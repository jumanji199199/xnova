"""
Модуль проверок безопасности для эксплойтов
"""

import os
from typing import Optional, Dict, Any, List
from solders.pubkey import Pubkey as PublicKey
from solders.keypair import Keypair
from solana.rpc.async_api import AsyncClient

from ..utils.logger import get_logger


class SafetyChecker:
    """
    Проверяет безопасность операций эксплойтов
    """
    
    def __init__(self, target_address: Optional[str] = None):
        """
        Args:
            target_address: Наш целевой адрес для получения средств
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Получаем целевой адрес из окружения если не передан
        self.target_address = target_address or os.getenv("SOLANA_TARGET_ADDRESS")
        if not self.target_address:
            raise ValueError("SOLANA_TARGET_ADDRESS not set")
            
        self.target_pubkey = PublicKey.from_string(self.target_address)
        self.logger.info(f"Safety checker initialized with target: {self.target_address}")
    
    def is_safe_transfer(self, from_pubkey: PublicKey, to_pubkey: PublicKey, amount: int) -> bool:
        """
        Проверяет безопасность перевода
        
        Args:
            from_pubkey: Откуда переводим
            to_pubkey: Куда переводим
            amount: Сумма перевода
            
        Returns:
            True если перевод безопасен
        """
        # Запрещаем переводы ИЗ нашего целевого аккаунта
        if from_pubkey == self.target_pubkey:
            self.logger.error(f"❌ BLOCKED: Attempt to transfer FROM our target account!")
            return False
            
        # Разрешаем переводы НА наш целевой аккаунт
        if to_pubkey == self.target_pubkey:
            self.logger.info(f"✅ Safe transfer TO our target account: {amount} lamports")
            return True
            
        # Проверяем сумму
        if amount <= 0:
            self.logger.error(f"❌ Invalid transfer amount: {amount}")
            return False
            
        # Проверяем что не переводим на самого себя
        if from_pubkey == to_pubkey:
            self.logger.error(f"❌ Self-transfer detected")
            return False
            
        return True
    
    def validate_exploit_params(self, params: Dict[str, Any]) -> bool:
        """
        Валидирует параметры эксплойта
        
        Args:
            params: Параметры для проверки
            
        Returns:
            True если параметры валидны
        """
        # Проверяем обязательные параметры
        required = ["target", "amount"]
        for param in required:
            if param not in params:
                self.logger.error(f"❌ Missing required parameter: {param}")
                return False
                
        # Проверяем типы
        if not isinstance(params.get("target"), (str, PublicKey)):
            self.logger.error("❌ Invalid target type")
            return False
            
        if not isinstance(params.get("amount"), (int, float)):
            self.logger.error("❌ Invalid amount type")
            return False
            
        # Проверяем значения
        if params.get("amount", 0) <= 0:
            self.logger.error("❌ Amount must be positive")
            return False
            
        return True
    
    async def check_account_balance(self, client: AsyncClient, pubkey: PublicKey, min_balance: int = 0) -> bool:
        """
        Проверяет баланс аккаунта
        
        Args:
            client: RPC клиент
            pubkey: Публичный ключ для проверки
            min_balance: Минимальный требуемый баланс
            
        Returns:
            True если баланс достаточен
        """
        try:
            response = await client.get_balance(pubkey)
            balance = response.value
            
            if balance < min_balance:
                self.logger.warning(f"⚠️ Insufficient balance: {balance} < {min_balance}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to check balance: {e}")
            return False
    
    def validate_transaction_safety(self, instructions: List[Any]) -> bool:
        """
        Проверяет безопасность транзакции
        
        Args:
            instructions: Инструкции транзакции
            
        Returns:
            True если транзакция безопасна
        """
        if not instructions:
            self.logger.error("❌ No instructions in transaction")
            return False
            
        # TODO: Добавить более детальную проверку инструкций
        
        return True
