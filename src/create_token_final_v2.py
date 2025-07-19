"""
Финальный скрипт создания SPL токена на Solana.
Использует правильную сигнатуру AsyncToken для создания токена.
Исправлены вызовы await для неасинхронных методов.
"""
import os
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solana.transaction import Transaction

# Импортируем доступные функции для токенов
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.async_client import AsyncToken

# Загружаем переменные окружения
load_dotenv()

# Константы из .env
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet.solana.com")
SOLANA_PRIVKEY = os.getenv("SOLANA_PRIVKEY")
SOLANA_TARGET_ADDRESS = os.getenv("SOLANA_TARGET_ADDRESS")

# Fallback RPC endpoints
FALLBACK_ENDPOINTS = [
    os.getenv("SOLANA_RPC_FALLBACK_1"),
    os.getenv("SOLANA_RPC_FALLBACK_2"),
    os.getenv("SOLANA_RPC_FALLBACK_3"),
    "https://api.mainnet-beta.solana.com",
    "https://solana-api.projectserum.com",
    "https://rpc.ankr.com/solana"
]

# Фильтруем None значения
FALLBACK_ENDPOINTS = [url for url in FALLBACK_ENDPOINTS if url]

def print_header(text):
    """Печатает заголовок с разделителями для лучшей читаемости."""
    print(f"\n{'='*50}")
    print(f" {text}")
    print(f"{'='*50}\n")

async def create_token(client, payer_keypair, token_name, token_symbol, decimals=9):
    """
    Создает SPL токен с заданными параметрами, используя AsyncToken.
    
    Args:
        client: RPC клиент Solana
        payer_keypair: Keypair плательщика
        token_name: Название токена
        token_symbol: Символ токена
        decimals: Количество десятичных знаков
        
    Returns:
        dict с информацией о созданном токене или None при ошибке
    """
    print_header(f"Создание токена {token_name} ({token_symbol})")
    
    try:
        # Создаем keypair для минта
        token_mint = Keypair()
        print(f"Mint address: {token_mint.pubkey()}")
        
        # Используем AsyncToken для создания минта
        token = AsyncToken(
            conn=client,
            pubkey=token_mint.pubkey(),
            program_id=TOKEN_PROGRAM_ID,
            payer=payer_keypair
        )
        
        # Создаем минт с правильной сигнатурой
        print("Создаем и инициализируем минт...")
        
        # ИСПРАВЛЕНО: get_balance не является асинхронным методом, не используем await
        balance_resp = client.get_balance(payer_keypair.pubkey())
        print(f"Текущий баланс кошелька: {balance_resp.value / 1_000_000_000} SOL")
        
        # Создаем минт с параметрами, которые поддерживаются в текущей версии библиотеки
        await token.create_mint(
            mint_authority=payer_keypair.pubkey(),  # Используем mint_authority вместо owner
            decimals=decimals,
            skip_confirmation=False
        )
        print("Минт создан успешно!")
        
        # Определяем получателя токенов
        owner_pubkey = Pubkey.from_string(SOLANA_TARGET_ADDRESS) if SOLANA_TARGET_ADDRESS else payer_keypair.pubkey()
        
        # Создаем токен-аккаунт
        print(f"Создаем токен-аккаунт для {owner_pubkey}...")
        associated_token = await token.create_associated_token_account(
            owner=owner_pubkey,
            skip_confirmation=False
        )
        print(f"Токен-аккаунт создан: {associated_token}")
        
        # Минтим начальное количество токенов
        initial_supply = 1_000_000 * (10 ** decimals)
        print(f"Минтим {initial_supply} токенов...")
        await token.mint_to(
            dest=associated_token,
            mint_authority=payer_keypair,
            amount=initial_supply,
            skip_confirmation=False
        )
        print(f"Токены созданы успешно!")
        
        # Создаем и возвращаем информацию о токене
        token_info = {
            "mint_address": str(token_mint.pubkey()),
            "token_account": str(associated_token),
            "owner_address": str(owner_pubkey),
            "name": token_name,
            "symbol": token_symbol,
            "decimals": decimals,
            "initial_supply": initial_supply,
            "mint_authority": str(payer_keypair.pubkey()),
            "freeze_authority": None,
            "creation_time": int(time.time()),
            "vulnerability_types": [
                "token_account_manipulation",
                "reentrancy",
                "unfrozen_tokens"
            ],
            "mint_private_key": token_mint.to_base58_string()
        }
        
        print(f"Токен {token_symbol} успешно создан!")
        return token_info
        
    except Exception as e:
        print(f"Ошибка при создании токена: {e}")
        import traceback
        traceback.print_exc()
        return None

def try_with_fallback_endpoints_sync(operation_func):
    """
    Пытается выполнить синхронную операцию с использованием запасных RPC endpoints.
    
    Args:
        operation_func: Синхронная функция, принимающая client и возвращающая результат
    
    Returns:
        Результат функции или None при ошибке
    """
    # Проверяем основной RPC endpoint
    try:
        client = Client(SOLANA_RPC_URL)
        print(f"Используем основной RPC endpoint: {SOLANA_RPC_URL}")
        return operation_func(client)
    except Exception as e:
        print(f"Ошибка с основным RPC endpoint: {e}")
    
    # Перебираем запасные endpoints
    for endpoint in FALLBACK_ENDPOINTS:
        try:
            client = Client(endpoint)
            print(f"Пробуем запасной endpoint: {endpoint}")
            return operation_func(client)
        except Exception as e:
            print(f"Ошибка с endpoint {endpoint}: {e}")
    
    print("Все RPC endpoints недоступны")
    return None

async def try_with_fallback_endpoints(operation_func):
    """
    Пытается выполнить асинхронную операцию с использованием запасных RPC endpoints.
    
    Args:
        operation_func: Асинхронная функция, принимающая client и возвращающая результат
    
    Returns:
        Результат функции или None при ошибке
    """
    # Проверяем основной RPC endpoint
    try:
        client = Client(SOLANA_RPC_URL)
        print(f"Используем основной RPC endpoint: {SOLANA_RPC_URL}")
        return await operation_func(client)
    except Exception as e:
        print(f"Ошибка с основным RPC endpoint: {e}")
    
    # Перебираем запасные endpoints
    for endpoint in FALLBACK_ENDPOINTS:
        try:
            client = Client(endpoint)
            print(f"Пробуем запасной endpoint: {endpoint}")
            return await operation_func(client)
        except Exception as e:
            print(f"Ошибка с endpoint {endpoint}: {e}")
    
    print("Все RPC endpoints недоступны")
    return None

async def main():
    """Основная асинхронная функция скрипта."""
    print_header("Создание уязвимых SPL токенов")
    
    # Проверяем наличие приватного ключа
    if not SOLANA_PRIVKEY:
        print("Ошибка: SOLANA_PRIVKEY не указан в .env")
        return
    
    try:
        # Создаем keypair из приватного ключа
        seed_bytes = bytes.fromhex(SOLANA_PRIVKEY)
        payer = Keypair.from_seed(seed_bytes[:32])
        print(f"Адрес кошелька: {payer.pubkey()}")
        
        # Проверяем баланс - используем синхронную функцию
        def check_balance(client):
            balance = client.get_balance(payer.pubkey())
            sol_balance = balance.value / 1_000_000_000
            print(f"Баланс: {sol_balance} SOL")
            return sol_balance
        
        sol_balance = try_with_fallback_endpoints_sync(check_balance)
        
        if sol_balance is None:
            print("Не удалось получить баланс. Продолжаем с осторожностью.")
        elif sol_balance < 0.1:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Баланс ({sol_balance} SOL) меньше рекомендуемого (0.1 SOL)")
            proceed = input("Продолжить? (y/n): ").strip().lower() == 'y'
            if not proceed:
                print("Отмена операции")
                return
        
        # Создаем токены для каждого типа эксплойта
        tokens_config = [
            {"name": "Account Exploit Token", "symbol": "AEXT", "decimals": 9},
            {"name": "Memory Exploit Token", "symbol": "MEXT", "decimals": 9},
            {"name": "Reentrancy Exploit Token", "symbol": "REXT", "decimals": 9},
        ]
        
        created_tokens = []
        
        for config in tokens_config:
            async def create_token_operation(client):
                return await create_token(
                    client=client,
                    payer_keypair=payer,
                    token_name=config["name"],
                    token_symbol=config["symbol"],
                    decimals=config["decimals"]
                )
            
            token_info = await try_with_fallback_endpoints(create_token_operation)
            
            if token_info:
                created_tokens.append(token_info)
            else:
                print(f"Не удалось создать токен {config['symbol']}")
            
            # Пауза между созданием токенов
            await asyncio.sleep(2)
        
        # Сохраняем информацию о токенах
        if created_tokens:
            # Обеспечиваем наличие директории data
            os.makedirs("data", exist_ok=True)
            
            # Основной файл с токенами
            with open("data/vulnerable_tokens.json", "w", encoding="utf-8") as f:
                json.dump(created_tokens, f, indent=2)
            
            # Также сохраняем копию с временной меткой
            timestamp_file = f"data/tokens_{int(time.time())}.json"
            with open(timestamp_file, "w", encoding="utf-8") as f:
                json.dump(created_tokens, f, indent=2)
            
            # Обновляем test_tokens.json для тестового фреймворка
            test_tokens = {}
            for token in created_tokens:
                test_tokens[token["symbol"]] = {
                    "address": token["mint_address"],
                    "account": token["token_account"],
                    "vulnerability_types": token["vulnerability_types"]
                }
                
            with open("data/test_tokens.json", "w", encoding="utf-8") as f:
                json.dump(test_tokens, f, indent=2)
            
            print(f"Создано {len(created_tokens)} токенов. Информация сохранена в:")
            print(f"- data/vulnerable_tokens.json")
            print(f"- {timestamp_file}")
            print(f"- data/test_tokens.json (для тестового фреймворка)")
        else:
            print("Не удалось создать ни одного токена")
            
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
