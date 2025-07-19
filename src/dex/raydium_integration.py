"""
Модуль для интеграции с Raydium DEX
"""

import asyncio
import json
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from dataclasses import dataclass

import httpx
from solana.rpc.async_api import AsyncClient
from solana.keypair import Keypair
from solana.publickey import PublicKey
from solana.transaction import Transaction
from solders.instruction import Instruction

from ..utils.config import get_solana_config, get_dex_config, get_liquidity_config
from ..utils.logger import get_logger, LogOperation

@dataclass
class PoolInfo:
    """Информация о пуле ликвидности"""
    pool_id: str
    base_mint: str
    quote_mint: str
    base_vault: str
    quote_vault: str
    lp_mint: str
    open_orders: str
    target_orders: str
    base_decimals: int
    quote_decimals: int
    market_id: str
    market_base_vault: str
    market_quote_vault: str
    market_authority: str
    market_event_queue: str
    market_bids: str
    market_asks: str

@dataclass
class LiquidityPosition:
    """Позиция ликвидности"""
    pool_id: str
    lp_amount: int
    base_amount: int
    quote_amount: int
    share_percentage: float

class RaydiumIntegration:
    """Класс для интеграции с Raydium DEX"""
    
    def __init__(self, payer: Keypair):
        self.logger = get_logger(__name__)
        self.payer = payer
        self.solana_config = get_solana_config()
        self.dex_config = get_dex_config()
        self.liquidity_config = get_liquidity_config()
        
        # Инициализация клиента Solana
        self.client = AsyncClient(endpoint=self.solana_config.rpc_url)
        
        # Константы Raydium
        self.RAYDIUM_PROGRAM_ID = PublicKey("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8")
        self.SERUM_PROGRAM_ID = PublicKey("9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin")
        
        # API endpoints
        self.api_base = "https://api.raydium.io/v2"
        
    async def get_pool_info(self, pool_id: str) -> Optional[PoolInfo]:
        """Получает информацию о пуле ликвидности"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/ammV3/pools/{pool_id}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return PoolInfo(
                        pool_id=data["id"],
                        base_mint=data["baseMint"],
                        quote_mint=data["quoteMint"],
                        base_vault=data["baseVault"],
                        quote_vault=data["quoteVault"],
                        lp_mint=data["lpMint"],
                        open_orders=data["openOrders"],
                        target_orders=data["targetOrders"],
                        base_decimals=data["baseDecimals"],
                        quote_decimals=data["quoteDecimals"],
                        market_id=data["marketId"],
                        market_base_vault=data["marketBaseVault"],
                        market_quote_vault=data["marketQuoteVault"],
                        market_authority=data["marketAuthority"],
                        market_event_queue=data["marketEventQueue"],
                        market_bids=data["marketBids"],
                        market_asks=data["marketAsks"]
                    )
                else:
                    self.logger.error(f"Ошибка получения информации о пуле: {response.status_code}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о пуле: {e}")
            return None
    
    async def get_all_pools(self) -> List[PoolInfo]:
        """Получает список всех пулов Raydium"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.api_base}/ammV3/pools")
                
                if response.status_code == 200:
                    data = response.json()
                    pools = []
                    
                    for pool_data in data:
                        pool = PoolInfo(
                            pool_id=pool_data["id"],
                            base_mint=pool_data["baseMint"],
                            quote_mint=pool_data["quoteMint"],
                            base_vault=pool_data["baseVault"],
                            quote_vault=pool_data["quoteVault"],
                            lp_mint=pool_data["lpMint"],
                            open_orders=pool_data["openOrders"],
                            target_orders=pool_data["targetOrders"],
                            base_decimals=pool_data["baseDecimals"],
                            quote_decimals=pool_data["quoteDecimals"],
                            market_id=pool_data["marketId"],
                            market_base_vault=pool_data["marketBaseVault"],
                            market_quote_vault=pool_data["marketQuoteVault"],
                            market_authority=pool_data["marketAuthority"],
                            market_event_queue=pool_data["marketEventQueue"],
                            market_bids=pool_data["marketBids"],
                            market_asks=pool_data["marketAsks"]
                        )
                        pools.append(pool)
                    
                    return pools
                else:
                    self.logger.error(f"Ошибка получения списка пулов: {response.status_code}")
                    return []
                    
        except Exception as e:
            self.logger.error(f"Ошибка при получении списка пулов: {e}")
            return []
    
    async def find_pool_by_tokens(self, base_mint: str, quote_mint: str) -> Optional[PoolInfo]:
        """Находит пул по адресам токенов"""
        try:
            pools = await self.get_all_pools()
            
            for pool in pools:
                if ((pool.base_mint == base_mint and pool.quote_mint == quote_mint) or
                    (pool.base_mint == quote_mint and pool.quote_mint == base_mint)):
                    return pool
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при поиске пула: {e}")
            return None
    
    async def create_pool(
        self,
        base_mint: str,
        quote_mint: str,
        base_amount: int,
        quote_amount: int,
        market_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Создает новый пул ликвидности
        
        Args:
            base_mint: Адрес базового токена
            quote_mint: Адрес котируемого токена (обычно SOL или USDC)
            base_amount: Количество базового токена
            quote_amount: Количество котируемого токена
            market_id: ID рынка Serum (если есть)
            
        Returns:
            ID созданного пула или None в случае ошибки
        """
        with LogOperation(f"Создание пула {base_mint}/{quote_mint}"):
            try:
                # Проверяем, существует ли уже пул
                existing_pool = await self.find_pool_by_tokens(base_mint, quote_mint)
                if existing_pool:
                    self.logger.warning(f"Пул уже существует: {existing_pool.pool_id}")
                    return existing_pool.pool_id
                
                # Если нет market_id, создаем рынок Serum
                if not market_id:
                    market_id = await self._create_serum_market(base_mint, quote_mint)
                    if not market_id:
                        raise Exception("Не удалось создать рынок Serum")
                
                # Создаем пул ликвидности
                pool_id = await self._create_liquidity_pool(
                    base_mint, quote_mint, base_amount, quote_amount, market_id
                )
                
                if pool_id:
                    self.logger.info(f"Пул создан успешно: {pool_id}")
                    return pool_id
                else:
                    raise Exception("Не удалось создать пул ликвидности")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при создании пула: {e}")
                return None
    
    async def _create_serum_market(self, base_mint: str, quote_mint: str) -> Optional[str]:
        """Создает рынок Serum для токенов"""
        try:
            # Это упрощенная версия - в реальности создание рынка Serum
            # требует более сложной логики и дополнительных параметров
            self.logger.info(f"Создание рынка Serum для {base_mint}/{quote_mint}")
            
            # TODO: Реализовать создание рынка Serum
            # Это требует:
            # 1. Создание market account
            # 2. Создание request queue, event queue, bids, asks
            # 3. Инициализация рынка
            
            # Пока возвращаем None - в реальном проекте нужна полная реализация
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании рынка Serum: {e}")
            return None
    
    async def _create_liquidity_pool(
        self,
        base_mint: str,
        quote_mint: str,
        base_amount: int,
        quote_amount: int,
        market_id: str
    ) -> Optional[str]:
        """Создает пул ликвидности Raydium"""
        try:
            # Это упрощенная версия - в реальности создание пула
            # требует множества инструкций и аккаунтов
            self.logger.info(f"Создание пула ликвидности для {base_mint}/{quote_mint}")
            
            # TODO: Реализовать создание пула ликвидности
            # Это требует:
            # 1. Создание AMM аккаунтов
            # 2. Инициализация пула
            # 3. Добавление начальной ликвидности
            
            # Пока возвращаем None - в реальном проекте нужна полная реализация
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании пула ликвидности: {e}")
            return None
    
    async def add_liquidity(
        self,
        pool_id: str,
        base_amount: int,
        quote_amount: int,
        slippage: float = 0.01
    ) -> Optional[LiquidityPosition]:
        """Добавляет ликвидность в существующий пул"""
        with LogOperation(f"Добавление ликвидности в пул {pool_id}"):
            try:
                pool_info = await self.get_pool_info(pool_id)
                if not pool_info:
                    raise Exception(f"Пул не найден: {pool_id}")
                
                # Получаем текущие цены и рассчитываем оптимальные количества
                optimal_amounts = await self._calculate_optimal_amounts(
                    pool_info, base_amount, quote_amount, slippage
                )
                
                if not optimal_amounts:
                    raise Exception("Не удалось рассчитать оптимальные количества")
                
                # Создаем транзакцию для добавления ликвидности
                transaction = await self._build_add_liquidity_transaction(
                    pool_info, optimal_amounts[0], optimal_amounts[1]
                )
                
                if not transaction:
                    raise Exception("Не удалось создать транзакцию")
                
                # Отправляем транзакцию
                result = await self.client.send_transaction(transaction)
                
                if result.value:
                    self.logger.info(f"Ликвидность добавлена. Транзакция: {result.value}")
                    
                    # Возвращаем информацию о позиции
                    return LiquidityPosition(
                        pool_id=pool_id,
                        lp_amount=0,  # Нужно получить из результата транзакции
                        base_amount=optimal_amounts[0],
                        quote_amount=optimal_amounts[1],
                        share_percentage=0.0  # Нужно рассчитать
                    )
                else:
                    raise Exception("Транзакция не была выполнена")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при добавлении ликвидности: {e}")
                return None
    
    async def _calculate_optimal_amounts(
        self,
        pool_info: PoolInfo,
        desired_base: int,
        desired_quote: int,
        slippage: float
    ) -> Optional[Tuple[int, int]]:
        """Рассчитывает оптимальные количества токенов для добавления ликвидности"""
        try:
            # Получаем текущие резервы пула
            base_reserve = await self._get_token_balance(pool_info.base_vault)
            quote_reserve = await self._get_token_balance(pool_info.quote_vault)
            
            if base_reserve == 0 or quote_reserve == 0:
                # Пул пустой, используем желаемые количества
                return (desired_base, desired_quote)
            
            # Рассчитываем текущий курс
            current_rate = quote_reserve / base_reserve
            
            # Рассчитываем оптимальные количества
            if desired_quote > desired_base * current_rate:
                # Ограничиваем по базовому токену
                optimal_base = desired_base
                optimal_quote = int(desired_base * current_rate)
            else:
                # Ограничиваем по котируемому токену
                optimal_quote = desired_quote
                optimal_base = int(desired_quote / current_rate)
            
            # Применяем slippage
            optimal_base = int(optimal_base * (1 - slippage))
            optimal_quote = int(optimal_quote * (1 - slippage))
            
            return (optimal_base, optimal_quote)
            
        except Exception as e:
            self.logger.error(f"Ошибка при расчете оптимальных количеств: {e}")
            return None
    
    async def _get_token_balance(self, token_account: str) -> int:
        """Получает баланс токенов в аккаунте"""
        try:
            response = await self.client.get_token_account_balance(
                PublicKey(token_account)
            )
            
            if response.value:
                return int(response.value.amount)
            else:
                return 0
                
        except Exception as e:
            self.logger.error(f"Ошибка при получении баланса: {e}")
            return 0
    
    async def _build_add_liquidity_transaction(
        self,
        pool_info: PoolInfo,
        base_amount: int,
        quote_amount: int
    ) -> Optional[Transaction]:
        """Создает транзакцию для добавления ликвидности"""
        try:
            # Это упрощенная версия - в реальности нужно создать
            # множество инструкций для добавления ликвидности
            
            transaction = Transaction()
            
            # TODO: Добавить инструкции для:
            # 1. Создание associated token accounts если нужно
            # 2. Approve токенов для программы
            # 3. Вызов инструкции добавления ликвидности
            # 4. Создание LP токенов
            
            # Получаем последний blockhash
            recent_blockhash = await self.client.get_latest_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            # Подписываем транзакцию
            transaction.sign(self.payer)
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании транзакции: {e}")
            return None
    
    async def remove_liquidity(
        self,
        pool_id: str,
        lp_amount: int,
        min_base_amount: int = 0,
        min_quote_amount: int = 0
    ) -> bool:
        """Удаляет ликвидность из пула"""
        with LogOperation(f"Удаление ликвидности из пула {pool_id}"):
            try:
                pool_info = await self.get_pool_info(pool_id)
                if not pool_info:
                    raise Exception(f"Пул не найден: {pool_id}")
                
                # Создаем транзакцию для удаления ликвидности
                transaction = await self._build_remove_liquidity_transaction(
                    pool_info, lp_amount, min_base_amount, min_quote_amount
                )
                
                if not transaction:
                    raise Exception("Не удалось создать транзакцию")
                
                # Отправляем транзакцию
                result = await self.client.send_transaction(transaction)
                
                if result.value:
                    self.logger.info(f"Ликвидность удалена. Транзакция: {result.value}")
                    return True
                else:
                    return False
                    
            except Exception as e:
                self.logger.error(f"Ошибка при удалении ликвидности: {e}")
                return False
    
    async def _build_remove_liquidity_transaction(
        self,
        pool_info: PoolInfo,
        lp_amount: int,
        min_base_amount: int,
        min_quote_amount: int
    ) -> Optional[Transaction]:
        """Создает транзакцию для удаления ликвидности"""
        try:
            transaction = Transaction()
            
            # TODO: Добавить инструкции для удаления ликвидности
            
            # Получаем последний blockhash
            recent_blockhash = await self.client.get_latest_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            # Подписываем транзакцию
            transaction.sign(self.payer)
            
            return transaction
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании транзакции удаления ликвидности: {e}")
            return None
    
    async def get_pool_price(self, pool_id: str) -> Optional[Decimal]:
        """Получает текущую цену в пуле"""
        try:
            pool_info = await self.get_pool_info(pool_id)
            if not pool_info:
                return None
            
            base_reserve = await self._get_token_balance(pool_info.base_vault)
            quote_reserve = await self._get_token_balance(pool_info.quote_vault)
            
            if base_reserve == 0:
                return None
            
            # Учитываем decimals
            base_adjusted = Decimal(base_reserve) / Decimal(10 ** pool_info.base_decimals)
            quote_adjusted = Decimal(quote_reserve) / Decimal(10 ** pool_info.quote_decimals)
            
            price = quote_adjusted / base_adjusted
            return price
            
        except Exception as e:
            self.logger.error(f"Ошибка при получении цены пула: {e}")
            return None
    
    async def close(self):
        """Закрывает соединения"""
        await self.client.close()
