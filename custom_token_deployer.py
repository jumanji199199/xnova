#!/usr/bin/env python3
"""
CUSTOM TOKEN DEPLOYER & TESTER
Разработка и тестирование собственного токена на Solana mainnet

Возможности:
- Создание токена с кастомными параметрами
- Тестирование всех функций токена
- Анализ безопасности и уязвимостей
- Интеграция с exploit framework
"""

import asyncio
import logging
import time
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from decimal import Decimal

from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solders.instruction import Instruction, AccountMeta
from solders.system_program import create_account, CreateAccountParams

# SPL Token imports
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import (
    initialize_mint, InitializeMintParams,
    initialize_account, InitializeAccountParams,
    mint_to, MintToParams,
    transfer, TransferParams,
    burn, BurnParams,
    close_account, CloseAccountParams,
    freeze_account, FreezeAccountParams,
    thaw_account, ThawAccountParams,
    set_authority, SetAuthorityParams,
    AuthorityType
)
from spl.token.client import Token

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('custom_token_test.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class TokenConfig:
    """Конфигурация кастомного токена"""
    name: str
    symbol: str
    decimals: int
    initial_supply: int
    description: str
    image_url: str = ""
    website: str = ""
    
    # Настройки безопасности
    freeze_authority_enabled: bool = True
    mint_authority_enabled: bool = True
    close_authority_enabled: bool = False
    
    # Дополнительные параметры
    max_supply: Optional[int] = None
    burn_enabled: bool = True
    transfer_fee: Optional[float] = None

@dataclass
class TokenTestResult:
    """Результат тестирования токена"""
    test_name: str
    success: bool
    execution_time: float
    transaction_signature: Optional[str] = None
    error_message: Optional[str] = None
    gas_used: Optional[int] = None
    data: Optional[Dict[str, Any]] = None

class CustomTokenDeployer:
    """
    Деплойер и тестер кастомных токенов
    """
    
    def __init__(self, rpc_url: str, private_key: str):
        self.client = AsyncClient(rpc_url, commitment=Commitment("confirmed"))
        
        # Создаем keypair из приватного ключа
        private_key_bytes = bytes.fromhex(private_key)
        self.payer_keypair = Keypair.from_bytes(private_key_bytes)
        
        # Создаем отдельные keypair для токена
        self.mint_keypair = Keypair()
        self.mint_authority = self.payer_keypair  # Используем основной кошелек как mint authority
        self.freeze_authority = self.payer_keypair  # И как freeze authority
        
        # Результаты тестирования
        self.test_results: List[TokenTestResult] = []
        self.token_address: Optional[PublicKey] = None
        self.token_account: Optional[PublicKey] = None
        
        logger.info(f"[+] CustomTokenDeployer инициализирован")
        logger.info(f"    Payer: {self.payer_keypair.pubkey()}")
        logger.info(f"    Mint: {self.mint_keypair.pubkey()}")
        
    async def check_balance(self) -> float:
        """Проверка баланса SOL"""
        try:
            response = await self.client.get_balance(self.payer_keypair.pubkey())
            balance_lamports = response.value
            balance_sol = balance_lamports / 1_000_000_000
            
            logger.info(f"[+] Баланс: {balance_sol:.9f} SOL ({balance_lamports} lamports)")
            return balance_sol
            
        except Exception as e:
            logger.error(f"[-] Ошибка проверки баланса: {e}")
            return 0.0
    
    async def create_token_mint(self, config: TokenConfig) -> TokenTestResult:
        """Создание mint аккаунта для токена"""
        test_start = time.time()
        
        try:
            logger.info(f"[*] Создание токена: {config.name} ({config.symbol})")
            
            # Рассчитываем размер mint аккаунта (82 байта для SPL Token)
            mint_rent = await self.client.get_minimum_balance_for_rent_exemption(82)
            
            # Создаем инструкции
            instructions = []
            
            # 1. Создание аккаунта для mint
            create_mint_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=self.payer_keypair.pubkey(),
                    to_pubkey=self.mint_keypair.pubkey(),
                    lamports=mint_rent.value,
                    space=82,
                    owner=TOKEN_PROGRAM_ID
                )
            )
            instructions.append(create_mint_account_ix)
            
            # 2. Инициализация mint
            freeze_auth = self.freeze_authority.pubkey() if config.freeze_authority_enabled else None
            
            initialize_mint_ix = initialize_mint(
                InitializeMintParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=self.mint_keypair.pubkey(),
                    decimals=config.decimals,
                    mint_authority=self.mint_authority.pubkey(),
                    freeze_authority=freeze_auth
                )
            )
            instructions.append(initialize_mint_ix)
            
            # Создаем и отправляем транзакцию
            transaction = Transaction()
            for ix in instructions:
                transaction.add(ix)
            
            # Подписываем транзакцию
            transaction.sign(self.payer_keypair, self.mint_keypair)
            
            # Отправляем транзакцию
            response = await self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            # Ждем подтверждения
            await self.client.confirm_transaction(response.value)
            
            self.token_address = self.mint_keypair.pubkey()
            
            result = TokenTestResult(
                test_name="create_token_mint",
                success=True,
                execution_time=time.time() - test_start,
                transaction_signature=str(response.value),
                data={
                    "mint_address": str(self.mint_keypair.pubkey()),
                    "decimals": config.decimals,
                    "mint_authority": str(self.mint_authority.pubkey()),
                    "freeze_authority": str(freeze_auth) if freeze_auth else None
                }
            )
            
            logger.info(f"[+] Токен создан успешно!")
            logger.info(f"    Mint адрес: {self.mint_keypair.pubkey()}")
            logger.info(f"    Транзакция: {response.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"[-] Ошибка создания токена: {e}")
            return TokenTestResult(
                test_name="create_token_mint",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            )
    
    async def create_token_account(self) -> TokenTestResult:
        """Создание token аккаунта для хранения токенов"""
        test_start = time.time()
        
        try:
            logger.info("[*] Создание token аккаунта...")
            
            if not self.token_address:
                raise ValueError("Сначала нужно создать mint")
            
            # Создаем keypair для token аккаунта
            token_account_keypair = Keypair()
            
            # Рассчитываем размер token аккаунта (165 байт)
            account_rent = await self.client.get_minimum_balance_for_rent_exemption(165)
            
            instructions = []
            
            # 1. Создание аккаунта
            create_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=self.payer_keypair.pubkey(),
                    to_pubkey=token_account_keypair.pubkey(),
                    lamports=account_rent.value,
                    space=165,
                    owner=TOKEN_PROGRAM_ID
                )
            )
            instructions.append(create_account_ix)
            
            # 2. Инициализация token аккаунта
            initialize_account_ix = initialize_account(
                InitializeAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=token_account_keypair.pubkey(),
                    mint=self.token_address,
                    owner=self.payer_keypair.pubkey()
                )
            )
            instructions.append(initialize_account_ix)
            
            # Создаем и отправляем транзакцию
            transaction = Transaction()
            for ix in instructions:
                transaction.add(ix)
            
            transaction.sign(self.payer_keypair, token_account_keypair)
            
            response = await self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            await self.client.confirm_transaction(response.value)
            
            self.token_account = token_account_keypair.pubkey()
            
            result = TokenTestResult(
                test_name="create_token_account",
                success=True,
                execution_time=time.time() - test_start,
                transaction_signature=str(response.value),
                data={
                    "token_account": str(token_account_keypair.pubkey()),
                    "owner": str(self.payer_keypair.pubkey()),
                    "mint": str(self.token_address)
                }
            )
            
            logger.info(f"[+] Token аккаунт создан: {token_account_keypair.pubkey()}")
            return result
            
        except Exception as e:
            logger.error(f"[-] Ошибка создания token аккаунта: {e}")
            return TokenTestResult(
                test_name="create_token_account",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            )
    
    async def mint_tokens(self, amount: int) -> TokenTestResult:
        """Минт токенов"""
        test_start = time.time()
        
        try:
            logger.info(f"[*] Минт {amount} токенов...")
            
            if not self.token_address or not self.token_account:
                raise ValueError("Сначала нужно создать mint и token аккаунт")
            
            # Создаем инструкцию минта
            mint_to_ix = mint_to(
                MintToParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=self.token_address,
                    dest=self.token_account,
                    mint_authority=self.mint_authority.pubkey(),
                    amount=amount,
                    signers=[]
                )
            )
            
            # Создаем и отправляем транзакцию
            transaction = Transaction()
            transaction.add(mint_to_ix)
            transaction.sign(self.mint_authority)
            
            response = await self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            await self.client.confirm_transaction(response.value)
            
            result = TokenTestResult(
                test_name="mint_tokens",
                success=True,
                execution_time=time.time() - test_start,
                transaction_signature=str(response.value),
                data={
                    "amount_minted": amount,
                    "destination": str(self.token_account)
                }
            )
            
            logger.info(f"[+] Заминчено {amount} токенов")
            return result
            
        except Exception as e:
            logger.error(f"[-] Ошибка минта токенов: {e}")
            return TokenTestResult(
                test_name="mint_tokens",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            )
    
    async def test_token_transfer(self, amount: int) -> TokenTestResult:
        """Тест перевода токенов"""
        test_start = time.time()
        
        try:
            logger.info(f"[*] Тест перевода {amount} токенов...")
            
            # Создаем второй token аккаунт для теста
            recipient_keypair = Keypair()
            
            # Создаем аккаунт получателя
            account_rent = await self.client.get_minimum_balance_for_rent_exemption(165)
            
            create_recipient_ix = create_account(
                CreateAccountParams(
                    from_pubkey=self.payer_keypair.pubkey(),
                    to_pubkey=recipient_keypair.pubkey(),
                    lamports=account_rent.value,
                    space=165,
                    owner=TOKEN_PROGRAM_ID
                )
            )
            
            initialize_recipient_ix = initialize_account(
                InitializeAccountParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=recipient_keypair.pubkey(),
                    mint=self.token_address,
                    owner=self.payer_keypair.pubkey()
                )
            )
            
            # Инструкция перевода
            transfer_ix = transfer(
                TransferParams(
                    program_id=TOKEN_PROGRAM_ID,
                    source=self.token_account,
                    dest=recipient_keypair.pubkey(),
                    owner=self.payer_keypair.pubkey(),
                    amount=amount,
                    signers=[]
                )
            )
            
            # Создаем транзакцию
            transaction = Transaction()
            transaction.add(create_recipient_ix)
            transaction.add(initialize_recipient_ix)
            transaction.add(transfer_ix)
            
            transaction.sign(self.payer_keypair, recipient_keypair)
            
            response = await self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            await self.client.confirm_transaction(response.value)
            
            result = TokenTestResult(
                test_name="test_token_transfer",
                success=True,
                execution_time=time.time() - test_start,
                transaction_signature=str(response.value),
                data={
                    "amount_transferred": amount,
                    "recipient": str(recipient_keypair.pubkey())
                }
            )
            
            logger.info(f"[+] Перевод {amount} токенов успешен")
            return result
            
        except Exception as e:
            logger.error(f"[-] Ошибка перевода токенов: {e}")
            return TokenTestResult(
                test_name="test_token_transfer",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            )
    
    async def test_token_burn(self, amount: int) -> TokenTestResult:
        """Тест сжигания токенов"""
        test_start = time.time()
        
        try:
            logger.info(f"[*] Тест сжигания {amount} токенов...")
            
            burn_ix = burn(
                BurnParams(
                    program_id=TOKEN_PROGRAM_ID,
                    account=self.token_account,
                    mint=self.token_address,
                    owner=self.payer_keypair.pubkey(),
                    amount=amount,
                    signers=[]
                )
            )
            
            transaction = Transaction()
            transaction.add(burn_ix)
            transaction.sign(self.payer_keypair)
            
            response = await self.client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            await self.client.confirm_transaction(response.value)
            
            result = TokenTestResult(
                test_name="test_token_burn",
                success=True,
                execution_time=time.time() - test_start,
                transaction_signature=str(response.value),
                data={
                    "amount_burned": amount
                }
            )
            
            logger.info(f"[+] Сожжено {amount} токенов")
            return result
            
        except Exception as e:
            logger.error(f"[-] Ошибка сжигания токенов: {e}")
            return TokenTestResult(
                test_name="test_token_burn",
                success=False,
                execution_time=time.time() - test_start,
                error_message=str(e)
            )
    
    async def get_token_info(self) -> Dict[str, Any]:
        """Получение информации о токене"""
        try:
            if not self.token_address:
                return {"error": "Token not created"}
            
            # Получаем информацию о mint
            mint_info = await self.client.get_account_info(self.token_address)
            
            # Получаем информацию о token аккаунте
            token_account_info = None
            if self.token_account:
                token_account_info = await self.client.get_account_info(self.token_account)
            
            return {
                "mint_address": str(self.token_address),
                "token_account": str(self.token_account) if self.token_account else None,
                "mint_info": {
                    "lamports": mint_info.value.lamports if mint_info.value else 0,
                    "owner": str(mint_info.value.owner) if mint_info.value else None,
                    "data_size": len(mint_info.value.data) if mint_info.value and mint_info.value.data else 0
                },
                "token_account_info": {
                    "lamports": token_account_info.value.lamports if token_account_info and token_account_info.value else 0,
                    "owner": str(token_account_info.value.owner) if token_account_info and token_account_info.value else None
                } if token_account_info else None
            }
            
        except Exception as e:
            logger.error(f"[-] Ошибка получения информации о токене: {e}")
            return {"error": str(e)}
    
    async def run_comprehensive_token_tests(self, config: TokenConfig) -> Dict[str, Any]:
        """Запуск полного набора тестов токена"""
        logger.info("=" * 80)
        logger.info(f"[!] КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ТОКЕНА: {config.name}")
        logger.info("=" * 80)
        
        suite_start = time.time()
        
        # Проверка баланса
        balance = await self.check_balance()
        if balance < 0.01:  # Минимум 0.01 SOL для создания токена
            logger.error(f"[-] Недостаточно SOL для создания токена: {balance:.9f}")
            return {"error": "Insufficient SOL balance"}
        
        # 1. Создание токена
        logger.info("[1/6] Создание mint аккаунта...")
        create_result = await self.create_token_mint(config)
        self.test_results.append(create_result)
        
        if not create_result.success:
            logger.error("[-] Не удалось создать токен. Остановка тестов.")
            return {"error": "Failed to create token mint"}
        
        # 2. Создание token аккаунта
        logger.info("[2/6] Создание token аккаунта...")
        account_result = await self.create_token_account()
        self.test_results.append(account_result)
        
        if not account_result.success:
            logger.error("[-] Не удалось создать token аккаунт. Остановка тестов.")
            return {"error": "Failed to create token account"}
        
        # 3. Минт токенов
        logger.info("[3/6] Минт токенов...")
        mint_amount = config.initial_supply * (10 ** config.decimals)
        mint_result = await self.mint_tokens(mint_amount)
        self.test_results.append(mint_result)
        
        # 4. Тест перевода
        logger.info("[4/6] Тест перевода токенов...")
        transfer_amount = min(1000 * (10 ** config.decimals), mint_amount // 2)
        transfer_result = await self.test_token_transfer(transfer_amount)
        self.test_results.append(transfer_result)
        
        # 5. Тест сжигания (если включено)
        if config.burn_enabled:
            logger.info("[5/6] Тест сжигания токенов...")
            burn_amount = min(500 * (10 ** config.decimals), mint_amount // 4)
            burn_result = await self.test_token_burn(burn_amount)
            self.test_results.append(burn_result)
        
        # 6. Получение финальной информации
        logger.info("[6/6] Получение информации о токене...")
        token_info = await self.get_token_info()
        
        # Статистика
        total_time = time.time() - suite_start
        successful_tests = sum(1 for result in self.test_results if result.success)
        total_tests = len(self.test_results)
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        comprehensive_results = {
            "token_config": {
                "name": config.name,
                "symbol": config.symbol,
                "decimals": config.decimals,
                "initial_supply": config.initial_supply,
                "description": config.description
            },
            "test_results": [
                {
                    "test_name": result.test_name,
                    "success": result.success,
                    "execution_time": result.execution_time,
                    "transaction_signature": result.transaction_signature,
                    "error_message": result.error_message,
                    "data": result.data
                }
                for result in self.test_results
            ],
            "token_info": token_info,
            "final_stats": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "total_execution_time": total_time,
                "wallet_balance": balance
            }
        }
        
        logger.info("=" * 80)
        logger.info("[=] ФИНАЛЬНАЯ СТАТИСТИКА ТЕСТИРОВАНИЯ ТОКЕНА")
        logger.info(f"[+] Токен: {config.name} ({config.symbol})")
        logger.info(f"[+] Mint адрес: {self.token_address}")
        logger.info(f"[+] Всего тестов: {total_tests}")
        logger.info(f"[+] Успешных: {successful_tests}")
        logger.info(f"[%] Процент успеха: {success_rate:.1f}%")
        logger.info(f"[T] Время выполнения: {total_time:.2f}s")
        logger.info("=" * 80)
        
        return comprehensive_results
    
    async def save_token_report(self, results: Dict[str, Any]):
        """Сохранение отчета о токене"""
        report_path = Path(__file__).parent / "custom_token_report.json"
        
        report = {
            "metadata": {
                "timestamp": time.time(),
                "wallet_pubkey": str(self.payer_keypair.pubkey()),
                "mint_address": str(self.token_address) if self.token_address else None,
                "token_account": str(self.token_account) if self.token_account else None,
                "test_type": "custom_token_deployment"
            },
            "results": results
        }
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"[+] Отчет сохранен: {report_path}")
    
    async def close(self):
        """Закрытие соединений"""
        await self.client.close()

async def main():
    """Главная функция"""
    print("[!] CUSTOM TOKEN DEPLOYER & TESTER")
    print("    Создание и тестирование собственного токена на Solana")
    print()
    
    # Загрузка настроек из env
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet.solana.com')
    private_key = os.getenv('SOLANA_PRIVKEY', '')
    
    if not private_key:
        print("[-] Ошибка: SOLANA_PRIVKEY не найден в переменных окружения!")
        return
    
    # Конфигурация токена
    token_config = TokenConfig(
        name="TestExploitToken",
        symbol="TET",
        decimals=9,
        initial_supply=1000000,  # 1M токенов
        description="Тестовый токен для exploit framework",
        freeze_authority_enabled=True,
        mint_authority_enabled=True,
        burn_enabled=True
    )
    
    # Инициализация деплойера
    deployer = CustomTokenDeployer(rpc_url, private_key)
    
    try:
        # Запуск тестов
        results = await deployer.run_comprehensive_token_tests(token_config)
        
        # Сохранение отчета
        await deployer.save_token_report(results)
        
        print("\n[+] Тестирование токена завершено!")
        print(f"[+] Отчет сохранен в custom_token_report.json")
        
        if deployer.token_address:
            print(f"[+] Адрес токена: {deployer.token_address}")
        
    except Exception as e:
        logger.error(f"[-] Критическая ошибка: {e}")
        raise
    
    finally:
        await deployer.close()

if __name__ == "__main__":
    asyncio.run(main())
