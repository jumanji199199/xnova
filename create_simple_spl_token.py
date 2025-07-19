#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
УПРОЩЕННЫЙ создатель тестового SPL токена
Использует более простой подход для избежания ошибок подписания
"""

import sys
import os
import asyncio
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID

# Устанавливаем UTF-8 кодировку для Windows консоли
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

class SimpleSPLTokenCreator:
    """Упрощенный создатель тестового SPL токена"""
    
    def __init__(self):
        load_dotenv()
        self.setup_config()
        
    def setup_config(self):
        """Настройка конфигурации"""
        # RPC URL с API ключом
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet.solana.com")
        print(f"[RPC] Используем endpoint: {self.rpc_url}")
        
        # Приватный ключ кошелька
        privkey_hex = os.getenv("SOLANA_PRIVKEY")
        if not privkey_hex:
            raise ValueError("[ERROR] SOLANA_PRIVKEY не найден!")
            
        try:
            privkey_bytes = bytes.fromhex(privkey_hex)
            self.payer_keypair = Keypair.from_bytes(privkey_bytes)
        except Exception as e:
            raise ValueError(f"[ERROR] Ошибка загрузки приватного ключа: {e}")
        
        print(f"[WALLET] Кошелек: {self.payer_keypair.pubkey()}")
        
    async def create_simple_token(self) -> dict:
        """Создает тестовый SPL токен упрощенным способом"""
        print(f"\n🪙 [CREATE] Упрощенное создание тестового SPL токена...")
        
        try:
            # Подключаемся к RPC
            client = AsyncClient(self.rpc_url)
            
            # Проверяем баланс кошелька
            balance_resp = await client.get_balance(self.payer_keypair.pubkey())
            balance_sol = balance_resp.value / 1e9
            print(f"[BALANCE] Баланс кошелька: {balance_sol:.9f} SOL")
            
            if balance_sol < 0.01:
                print(f"❌ [ERROR] Недостаточно SOL для создания токена (нужно минимум 0.01 SOL)")
                return {"success": False, "error": "Insufficient balance"}
            
            # 🚀 УПРОЩЕННЫЙ ПОДХОД: Используем AsyncToken class
            print(f"[STEP 1] Создание SPL токена через AsyncToken...")
            
            # Создаем AsyncToken instance
            token_client = AsyncToken(
                conn=client,
                pubkey=None,  # Will be set after creation
                program_id=TOKEN_PROGRAM_ID,
                payer=self.payer_keypair
            )
            
            # 🎯 КЛЮЧЕВОЕ УПРОЩЕНИЕ: Создаем mint с помощью create_mint
            print(f"[STEP 2] Создание mint account...")
            mint_keypair = Keypair()
            
            # 🔧 ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ: Добавляем обязательный program_id параметр
            # AsyncToken.create_mint() автоматически создает mint_keypair
            create_mint_resp = await AsyncToken.create_mint(
                conn=client,
                payer=self.payer_keypair,
                mint_authority=self.payer_keypair.pubkey(),
                freeze_authority=self.payer_keypair.pubkey(),
                decimals=6,
                program_id=TOKEN_PROGRAM_ID  # 🚀 Обязательный параметр
            )
            
            # 🔧 ИСПРАВЛЕНО: create_mint_resp это AsyncToken объект, извлекаем pubkey
            token = create_mint_resp  # Это уже готовый AsyncToken объект
            mint_pubkey = token.pubkey  # Извлекаем pubkey из объекта
            print(f"[MINT] Mint создан: {mint_pubkey}")
            
            # 🎯 СОЗДАЕМ ASSOCIATED TOKEN ACCOUNT
            print(f"[STEP 3] Создание associated token account...")
            token_account_resp = await token.create_associated_token_account(
                owner=self.payer_keypair.pubkey()
            )
            
            token_account = token_account_resp
            print(f"[TOKEN_ACCOUNT] Token account создан: {token_account}")
            
            # 🎯 МИНТИМ ТЕСТОВЫЕ ТОКЕНЫ
            test_amount = 1000 * (10 ** 6)  # 1000 токенов с 6 decimals
            print(f"[STEP 4] Минтинг {test_amount / (10**6)} тестовых токенов...")
            
            mint_resp = await token.mint_to(
                dest=token_account,
                mint_authority=self.payer_keypair,
                amount=test_amount
            )
            
            print(f"[MINT_TO] Mint to signature: {mint_resp}")
            
            print(f"✅ [SUCCESS] SPL токен создан успешно упрощенным методом!")
            
            token_info = {
                "success": True,
                "mint_address": str(mint_pubkey),
                "token_account": str(token_account),
                "owner": str(self.payer_keypair.pubkey()),
                "amount": test_amount,
                "decimals": 6,
                "ui_amount": test_amount / (10 ** 6),
                "create_mint_signature": str(create_mint_resp),
                "mint_to_signature": str(mint_resp)
            }
            
            # Сохраняем информацию о токене
            import json
            with open("simple_spl_token_info.json", "w", encoding="utf-8") as f:
                json.dump(token_info, f, indent=2, ensure_ascii=False)
            
            print(f"[SAVE] Информация сохранена в simple_spl_token_info.json")
            
            await client.close()
            return token_info
            
        except Exception as e:
            print(f"❌ [ERROR] Ошибка создания SPL токена: {e}")
            return {"success": False, "error": str(e)}

async def main():
    """Главная функция"""
    print("🚀 === УПРОЩЕННОЕ СОЗДАНИЕ ТЕСТОВОГО SPL ТОКЕНА ===")
    
    creator = SimpleSPLTokenCreator()
    result = await creator.create_simple_token()
    
    if result["success"]:
        print(f"\n🎉 === ТОКЕН СОЗДАН УСПЕШНО ===")
        print(f"Mint Address: {result['mint_address']}")
        print(f"Token Account: {result['token_account']}")
        print(f"Amount: {result['ui_amount']} токенов")
        print(f"Create Mint Signature: {result['create_mint_signature']}")
        print(f"Mint To Signature: {result['mint_to_signature']}")
        print(f"\n💡 Теперь можно тестировать TokenExploit на этом SPL токене!")
    else:
        print(f"\n❌ === ОШИБКА СОЗДАНИЯ ТОКЕНА ===")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
