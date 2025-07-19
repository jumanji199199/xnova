#!/usr/bin/env python3
"""
Проверка реального баланса аккаунта
"""

import asyncio
import os
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey
from solders.keypair import Keypair

async def check_balance():
    """Проверка реального баланса аккаунта"""
    
    # Загрузка переменных окружения
    load_dotenv()
    
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet.solana.com')
    privkey_hex = os.getenv('SOLANA_PRIVKEY')
    target_address = os.getenv('SOLANA_TARGET_ADDRESS')
    
    if not privkey_hex:
        print("[ERROR] SOLANA_PRIVKEY не найден в .env")
        return
    
    # Создание клиента
    client = AsyncClient(rpc_url)
    
    try:
        # Создание keypair из приватного ключа
        privkey_bytes = bytes.fromhex(privkey_hex)
        keypair = Keypair.from_bytes(privkey_bytes)
        pubkey = keypair.pubkey()
        
        print(f"[KEY] Адрес из приватного ключа: {pubkey}")
        print(f"[TARGET] Целевой адрес из .env: {target_address}")
        
        # Проверка баланса по адресу из ключа
        balance_response = await client.get_balance(pubkey)
        if balance_response.value is not None:
            balance_sol = balance_response.value / 1_000_000_000  # lamports to SOL
            print(f"[BALANCE] Баланс (из ключа): {balance_sol:.9f} SOL")
        else:
            print("[ERROR] Не удалось получить баланс из ключа")
        
        # Проверка баланса по целевому адресу
        if target_address:
            target_pubkey = Pubkey.from_string(target_address)
            target_balance_response = await client.get_balance(target_pubkey)
            if target_balance_response.value is not None:
                target_balance_sol = target_balance_response.value / 1_000_000_000
                print(f"[BALANCE] Баланс (целевой): {target_balance_sol:.9f} SOL")
            else:
                print("[ERROR] Не удалось получить баланс целевого адреса")
        
        # Получение информации об аккаунте
        account_info = await client.get_account_info(pubkey)
        if account_info.value:
            print(f"[INFO] Владелец аккаунта: {account_info.value.owner}")
            print(f"[INFO] Размер данных: {account_info.value.data_size} байт")
            print(f"[INFO] Исполняемый: {account_info.value.executable}")
        
    except Exception as e:
        print(f"[ERROR] Ошибка: {e}")
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(check_balance())
