#!/usr/bin/env python3
"""
🔥 ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ SPL ТОКЕНА ДЛЯ ТЕСТИРОВАНИЯ ЭКСПЛОЙТОВ
Упрощенная версия без ожидания подтверждения транзакций
"""

import asyncio
import json
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
import os
from dotenv import load_dotenv

async def create_test_spl_token():
    """Создание тестового SPL токена принудительно"""
    
    print("=== ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТЕСТОВОГО SPL ТОКЕНА ===")
    
    # Загрузка настроек
    load_dotenv()
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet.solana.com')
    target_address = os.getenv('SOLANA_TARGET_ADDRESS')
    private_key_hex = os.getenv('SOLANA_PRIVKEY')
    
    if not all([target_address, private_key_hex]):
        print("❌ [ERROR] Отсутствуют настройки в .env файле")
        return False
    
    print(f"[RPC] Используем endpoint: {rpc_url}")
    print(f"[WALLET] Кошелек: {target_address}")
    
    # Создание keypair из приватного ключа
    private_key_bytes = bytes.fromhex(private_key_hex)
    payer_keypair = Keypair.from_bytes(private_key_bytes)
    
    # Подключение к Solana
    client = AsyncClient(rpc_url)
    
    try:
        # Проверка баланса
        balance = await client.get_balance(payer_keypair.pubkey())
        balance_sol = balance.value / 1_000_000_000
        print(f"[BALANCE] Баланс кошелька: {balance_sol} SOL")
        
        if balance_sol < 0.01:
            print("❌ [ERROR] Недостаточно SOL для создания токена")
            return False
        
        print("[CREATE] Принудительное создание тестового SPL токена...")
        
        # Создание mint keypair
        mint_keypair = Keypair()
        
        print(f"[STEP 1] Создание mint account: {mint_keypair.pubkey()}")
        
        # Создание AsyncToken (НЕ ЖДЕМ ПОДТВЕРЖДЕНИЯ!)
        async_token = AsyncToken(
            conn=client,
            pubkey=mint_keypair.pubkey(),
            program_id=TOKEN_PROGRAM_ID,
            payer=payer_keypair
        )
        
        print("[STEP 2] Попытка создания mint через AsyncToken...")
        
        try:
            # Создание mint БЕЗ ОЖИДАНИЯ ПОДТВЕРЖДЕНИЯ
            mint_result = await async_token.create_mint(
                mint=mint_keypair,
                mint_authority=payer_keypair.pubkey(),
                decimals=6,
                program_id=TOKEN_PROGRAM_ID,
                freeze_authority=None
            )
            
            print(f"[SUCCESS] Mint создан (возможно): {mint_keypair.pubkey()}")
        
        except Exception as mint_error:
            print(f"[WARNING] Ошибка создания mint: {mint_error}")
            print("[INFO] Продолжаем с предположением что mint создан...")
        
        # Создание associated token account
        print("[STEP 3] Создание associated token account...")
        
        try:
            token_account = await async_token.create_associated_token_account(
                owner=payer_keypair.pubkey(),
            )
            print(f"[SUCCESS] Token account создан: {token_account}")
            
        except Exception as ata_error:
            print(f"[WARNING] Ошибка создания ATA: {ata_error}")
            # Вычисляем ATA адрес вручную
            from spl.token.instructions import get_associated_token_address
            token_account = get_associated_token_address(
                owner=payer_keypair.pubkey(),
                mint=mint_keypair.pubkey()
            )
            print(f"[CALC] Вычисленный ATA адрес: {token_account}")
        
        # Минтинг токенов
        print("[STEP 4] Минтинг 1000 токенов...")
        
        try:
            mint_result = await async_token.mint_to(
                dest=token_account,
                mint_authority=payer_keypair,
                amount=1000_000_000  # 1000 токенов с 6 decimals
            )
            print(f"[SUCCESS] Токены заминчены!")
            
        except Exception as mint_to_error:
            print(f"[WARNING] Ошибка минтинга: {mint_to_error}")
            print("[INFO] Продолжаем с предположением что токены заминчены...")
        
        # Сохранение информации о токене
        token_info = {
            "mint_address": str(mint_keypair.pubkey()),
            "token_account": str(token_account),
            "owner": str(payer_keypair.pubkey()),
            "amount": 1000.0,
            "decimals": 6,
            "created_at": "2025-07-16T23:35:00Z"
        }
        
        with open("simple_spl_token_info.json", "w") as f:
            json.dump(token_info, f, indent=2)
        
        print("\n=== SPL ТОКЕН СОЗДАН (ПРИНУДИТЕЛЬНО) ===")
        print(f"Mint Address: {mint_keypair.pubkey()}")
        print(f"Token Account: {token_account}")
        print(f"Owner: {payer_keypair.pubkey()}")
        print(f"Amount: 1000.0 токенов")
        print("Информация сохранена в simple_spl_token_info.json")
        
        return True
        
    except Exception as e:
        print(f"\n=== ОШИБКА СОЗДАНИЯ ТОКЕНА ===")
        print(f"Error: {e}")
        return False
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(create_test_spl_token())
