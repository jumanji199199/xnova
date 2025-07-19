"""
Модуль для создания и управления SPL токенами в сети Solana
"""

import json
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass
from decimal import Decimal

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.system_program import SYS_PROGRAM_ID
from solana.transaction import Transaction
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import (
    create_mint, create_associated_token_account, mint_to,
    set_authority, AuthorityType
)

from ..utils.config import get_solana_config, get_token_config, get_wallet_config
from ..utils.logger import get_logger, LogOperation

@dataclass
class TokenMetadata:
    """Метаданные токена"""
    name: str
    symbol: str
    description: str
    image_url: str
    website: Optional[str] = None
    twitter: Optional[str] = None
    telegram: Optional[str] = None
    discord: Optional[str] = None

@dataclass
class TokenInfo:
    """Информация о созданном токене"""
    mint_address: str
    token_account: str
    metadata_account: Optional[str] = None
    total_supply: int = 0
    decimals: int = 9
    freeze_authority: Optional[str] = None
    mint_authority: Optional[str] = None

class TokenCreator:
    """Класс для создания SPL токенов"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.solana_config = get_solana_config()
        self.token_config = get_token_config()
        self.wallet_config = get_wallet_config()
        
        # Инициализация клиента Solana
        self.client = AsyncClient(
            endpoint=self.solana_config.rpc_url,
            commitment=Commitment(self.solana_config.commitment)
        )
        
        # Загрузка кошелька
        self.payer = self._load_wallet()
        
    def _load_wallet(self) -> Keypair:
        """Загружает кошелек из файла"""
        try:
            wallet_path = Path(self.wallet_config.keypair_path).expanduser()
            
            if not wallet_path.exists():
                self.logger.error(f"Файл кошелька не найден: {wallet_path}")
                raise FileNotFoundError(f"Wallet file not found: {wallet_path}")
            
            with open(wallet_path, 'r') as f:
                keypair_data = json.load(f)
            
            if isinstance(keypair_data, list):
                # Формат массива байтов
                keypair = Keypair.from_secret_key(bytes(keypair_data))
            else:
                # Другие форматы
                raise ValueError("Неподдерживаемый формат файла кошелька")
            
            self.logger.info(f"Кошелек загружен: {keypair.public_key}")
            return keypair
            
        except Exception as e:
            self.logger.error(f"Ошибка при загрузке кошелька: {e}")
            raise
    
    async def create_token(
        self,
        metadata: TokenMetadata,
        initial_supply: Optional[int] = None,
        decimals: Optional[int] = None,
        freeze_authority: Optional[PublicKey] = None,
        mint_authority: Optional[PublicKey] = None
    ) -> TokenInfo:
        """
        Создает новый SPL токен
        
        Args:
            metadata: Метаданные токена
            initial_supply: Начальное количество токенов
            decimals: Количество десятичных знаков
            freeze_authority: Адрес для заморозки токенов
            mint_authority: Адрес для создания новых токенов
            
        Returns:
            TokenInfo: Информация о созданном токене
        """
        with LogOperation(f"Создание токена {metadata.symbol}"):
            try:
                # Параметры по умолчанию
                decimals = decimals or self.token_config.default_decimals
                initial_supply = initial_supply or self.token_config.default_supply
                
                # Создаем новый mint
                mint_keypair = Keypair()
                mint_pubkey = mint_keypair.public_key
                
                self.logger.info(f"Создание mint для токена {metadata.symbol}: {mint_pubkey}")
                
                # Создаем инструкцию для создания mint
                create_mint_ix = create_mint(
                    params={
                        "program_id": TOKEN_PROGRAM_ID,
                        "mint": mint_pubkey,
                        "mint_authority": mint_authority or self.payer.public_key,
                        "freeze_authority": freeze_authority,
                        "decimals": decimals,
                    }
                )
                
                # Создаем associated token account для владельца
                token_account = self._get_associated_token_address(
                    mint_pubkey, self.payer.public_key
                )
                
                create_ata_ix = create_associated_token_account(
                    payer=self.payer.public_key,
                    owner=self.payer.public_key,
                    mint=mint_pubkey
                )
                
                # Создаем транзакцию
                transaction = Transaction()
                transaction.add(create_mint_ix)
                transaction.add(create_ata_ix)
                
                # Если нужно создать начальное количество токенов
                if initial_supply > 0:
                    mint_to_ix = mint_to(
                        params={
                            "program_id": TOKEN_PROGRAM_ID,
                            "mint": mint_pubkey,
                            "dest": token_account,
                            "mint_authority": self.payer.public_key,
                            "amount": initial_supply * (10 ** decimals),
                        }
                    )
                    transaction.add(mint_to_ix)
                
                # Подписываем и отправляем транзакцию
                transaction.recent_blockhash = (
                    await self.client.get_latest_blockhash()
                ).value.blockhash
                
                transaction.sign(self.payer, mint_keypair)
                
                result = await self.client.send_transaction(transaction)
                
                if result.value:
                    self.logger.info(f"Токен создан успешно. Транзакция: {result.value}")
                    
                    # Создаем метаданные токена
                    metadata_account = await self._create_token_metadata(
                        mint_pubkey, metadata
                    )
                    
                    token_info = TokenInfo(
                        mint_address=str(mint_pubkey),
                        token_account=str(token_account),
                        metadata_account=metadata_account,
                        total_supply=initial_supply,
                        decimals=decimals,
                        freeze_authority=str(freeze_authority) if freeze_authority else None,
                        mint_authority=str(mint_authority) if mint_authority else str(self.payer.public_key)
                    )
                    
                    # Сохраняем информацию о токене
                    await self._save_token_info(token_info, metadata)
                    
                    return token_info
                else:
                    raise Exception("Не удалось создать токен")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при создании токена: {e}")
                raise
    
    async def _create_token_metadata(
        self, 
        mint_pubkey: PublicKey, 
        metadata: TokenMetadata
    ) -> Optional[str]:
        """Создает метаданные для токена"""
        try:
            # Здесь должна быть интеграция с Metaplex для создания метаданных
            # Пока что возвращаем None, так как это требует дополнительных зависимостей
            self.logger.info(f"Создание метаданных для токена {mint_pubkey}")
            
            # TODO: Реализовать создание метаданных через Metaplex
            # metadata_account = await create_metadata_account(...)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании метаданных: {e}")
            return None
    
    def _get_associated_token_address(self, mint: PublicKey, owner: PublicKey) -> PublicKey:
        """Получает адрес associated token account"""
        try:
            # Находим PDA для associated token account
            seeds = [
                bytes(owner),
                bytes(TOKEN_PROGRAM_ID),
                bytes(mint)
            ]
            
            pda, _ = PublicKey.find_program_address(
                seeds, ASSOCIATED_TOKEN_PROGRAM_ID
            )
            
            return pda
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении ATA адреса: {e}")
            raise
    
    async def _save_token_info(self, token_info: TokenInfo, metadata: TokenMetadata):
        """Сохраняет информацию о токене в файл"""
        try:
            # Создаем директорию для сохранения
            tokens_dir = Path("./tokens")
            tokens_dir.mkdir(exist_ok=True)
            
            # Подготавливаем данные для сохранения
            token_data = {
                "token_info": {
                    "mint_address": token_info.mint_address,
                    "token_account": token_info.token_account,
                    "metadata_account": token_info.metadata_account,
                    "total_supply": token_info.total_supply,
                    "decimals": token_info.decimals,
                    "freeze_authority": token_info.freeze_authority,
                    "mint_authority": token_info.mint_authority
                },
                "metadata": {
                    "name": metadata.name,
                    "symbol": metadata.symbol,
                    "description": metadata.description,
                    "image_url": metadata.image_url,
                    "website": metadata.website,
                    "twitter": metadata.twitter,
                    "telegram": metadata.telegram,
                    "discord": metadata.discord
                },
                "created_at": asyncio.get_event_loop().time()
            }
            
            # Сохраняем в файл
            filename = f"{metadata.symbol}_{token_info.mint_address[:8]}.json"
            filepath = tokens_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(token_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Информация о токене сохранена: {filepath}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении информации о токене: {e}")
    
    async def get_token_balance(self, mint_address: str, owner_address: str) -> Decimal:
        """Получает баланс токенов для указанного адреса"""
        try:
            mint_pubkey = PublicKey(mint_address)
            owner_pubkey = PublicKey(owner_address)
            
            # Получаем associated token account
            token_account = self._get_associated_token_address(mint_pubkey, owner_pubkey)
            
            # Получаем информацию об аккаунте
            response = await self.client.get_token_account_balance(token_account)
            
            if response.value:
                return Decimal(response.value.amount) / Decimal(10 ** response.value.decimals)
            else:
                return Decimal(0)
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении баланса токенов: {e}")
            return Decimal(0)
    
    async def mint_additional_tokens(
        self, 
        mint_address: str, 
        amount: int, 
        destination: Optional[str] = None
    ) -> bool:
        """Создает дополнительные токены"""
        try:
            mint_pubkey = PublicKey(mint_address)
            dest_pubkey = PublicKey(destination) if destination else self.payer.public_key
            
            # Получаем associated token account получателя
            token_account = self._get_associated_token_address(mint_pubkey, dest_pubkey)
            
            # Создаем инструкцию mint_to
            mint_to_ix = mint_to(
                params={
                    "program_id": TOKEN_PROGRAM_ID,
                    "mint": mint_pubkey,
                    "dest": token_account,
                    "mint_authority": self.payer.public_key,
                    "amount": amount,
                }
            )
            
            # Создаем и отправляем транзакцию
            transaction = Transaction()
            transaction.add(mint_to_ix)
            
            transaction.recent_blockhash = (
                await self.client.get_latest_blockhash()
            ).value.blockhash
            
            transaction.sign(self.payer)
            
            result = await self.client.send_transaction(transaction)
            
            if result.value:
                self.logger.info(f"Дополнительные токены созданы. Транзакция: {result.value}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при создании дополнительных токенов: {e}")
            return False
    
    async def revoke_mint_authority(self, mint_address: str) -> bool:
        """Отзывает права на создание новых токенов"""
        try:
            mint_pubkey = PublicKey(mint_address)
            
            # Создаем инструкцию для отзыва прав
            revoke_ix = set_authority(
                params={
                    "program_id": TOKEN_PROGRAM_ID,
                    "account": mint_pubkey,
                    "authority": AuthorityType.MINT_TOKENS,
                    "current_authority": self.payer.public_key,
                    "new_authority": None,
                }
            )
            
            # Создаем и отправляем транзакцию
            transaction = Transaction()
            transaction.add(revoke_ix)
            
            transaction.recent_blockhash = (
                await self.client.get_latest_blockhash()
            ).value.blockhash
            
            transaction.sign(self.payer)
            
            result = await self.client.send_transaction(transaction)
            
            if result.value:
                self.logger.info(f"Права на создание токенов отозваны. Транзакция: {result.value}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при отзыве прав на создание токенов: {e}")
            return False
    
    async def close(self):
        """Закрывает соединение с клиентом"""
        await self.client.close()
