#!/usr/bin/env python3
"""
Проверяет существование созданных тестовых аккаунтов через RPC
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey

# Загружаем переменные окружения
load_dotenv()

# Тестовые аккаунты из отчета
TEST_ACCOUNTS = [
    "EUU3QLhwi5zqDGEWPiGjXtr63oD7BL8zHStTNJ2cstaL",
    "BzBgmykB3D35SttCsra93AnVPdCHFgtw2J5o7rKGL8UM"
]

# RPC URL
RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet.solana.com")

async def check_account_existence(address_str: str) -> dict:
    """Проверяет существование аккаунта через RPC"""
    
    print(f"\n[CHECK] Проверяем аккаунт: {address_str}")
    
    try:
        # Конвертируем адрес
        pubkey = Pubkey.from_string(address_str)
        print(f"[OK] Адрес корректно сконвертирован: {pubkey}")
        
        # Подключаемся к RPC
        async with AsyncClient(RPC_URL) as client:
            print(f"[RPC] Подключились к RPC: {RPC_URL}")
            
            # Получаем информацию об аккаунте
            response = await client.get_account_info(pubkey)
            
            if response.value is None:
                print(f"[NOT_FOUND] АККАУНТ НЕ НАЙДЕН: {address_str}")
                return {
                    "address": address_str,
                    "exists": False,
                    "error": "Account not found"
                }
            else:
                account_info = response.value
                print(f"[FOUND] АККАУНТ НАЙДЕН!")
                print(f"   [BALANCE] Баланс: {account_info.lamports} лампортов")
                print(f"   [OWNER] Владелец: {account_info.owner}")
                print(f"   [SIZE] Размер данных: {len(account_info.data)} байт")
                print(f"   [EXEC] Исполняемый: {account_info.executable}")
                
                return {
                    "address": address_str,
                    "exists": True,
                    "lamports": account_info.lamports,
                    "owner": str(account_info.owner),
                    "data_size": len(account_info.data),
                    "executable": account_info.executable
                }
                
    except Exception as e:
        print(f"[ERROR] ОШИБКА при проверке {address_str}: {e}")
        return {
            "address": address_str,
            "exists": False,
            "error": str(e)
        }

async def main():
    """Основная функция"""
    
    print("[START] ПРОВЕРКА СУЩЕСТВОВАНИЯ ТЕСТОВЫХ АККАУНТОВ")
    print("=" * 50)
    
    results = []
    
    for account_address in TEST_ACCOUNTS:
        result = await check_account_existence(account_address)
        results.append(result)
        
        # Небольшая пауза между запросами
        await asyncio.sleep(0.5)
    
    print("\n" + "=" * 50)
    print("[REPORT] ИТОГОВЫЙ ОТЧЕТ:")
    print("=" * 50)
    
    existing_accounts = 0
    for result in results:
        if result["exists"]:
            existing_accounts += 1
            print(f"[OK] {result['address'][:10]}... - НАЙДЕН ({result['lamports']} лампортов)")
        else:
            print(f"[FAIL] {result['address'][:10]}... - НЕ НАЙДЕН ({result.get('error', 'Unknown error')})")
    
    print(f"\n[STATS] СТАТИСТИКА:")
    print(f"   Найдено аккаунтов: {existing_accounts}/{len(TEST_ACCOUNTS)}")
    print(f"   Процент успеха: {(existing_accounts/len(TEST_ACCOUNTS)*100):.1f}%")
    
    if existing_accounts == 0:
        print(f"\n[WARNING] ПРОБЛЕМА: Все тестовые аккаунты отсутствуют!")
        print(f"   Возможные причины:")
        print(f"   1. Транзакции создания не подтвердились")
        print(f"   2. Недостаточно средств для создания аккаунтов")
        print(f"   3. Ошибка в логике создания аккаунтов")
        print(f"   4. RPC не синхронизирован")
    
    return results

if __name__ == "__main__":
    # UTF-8 для Windows
    if sys.platform == "win32":
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except:
            pass
    
    # Запускаем проверку
    asyncio.run(main())
