#!/usr/bin/env python3
"""
Создание набора уязвимых SPL токенов для тестирования эксплойтов:
- Создает 4 разных токена с разными уязвимостями
- Сохраняет информацию о токенах для последующего тестирования
- Генерирует отчет о созданных уязвимостях
"""
import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import MintTo, transfer, create_associated_token_account, get_associated_token_address

from dotenv import load_dotenv

# Список уязвимостей для создания тестовых токенов
VULNERABILITIES = {
    "reentrancy": "Уязвимость повторного входа (reentrancy)",
    "no_balance_check": "Отсутствие проверок баланса",
    "no_owner_verification": "Отсутствие проверки владельца",
    "double_spend": "Возможность двойной траты"
}

@dataclass
class VulnerableToken:
    """Информация о созданном уязвимом токене"""
    name: str
    symbol: str
    decimals: int
    mint_address: str
    mint_authority: str
    mint_authority_private_key: str
    supply: int
    vulnerability_type: str
    vulnerability_description: str
    creation_time: int


async def create_token(
    client: AsyncClient,
    payer: Keypair,
    name: str,
    symbol: str,
    decimals: int = 9,
    vulnerability_type: str = None
) -> Optional[VulnerableToken]:
    """Создает новый SPL токен с указанной уязвимостью"""
    try:
        # Создаем mint keypair
        mint_keypair = Keypair()
        mint_pubkey = mint_keypair.pubkey()
        
        # Создаем токен
        token = AsyncToken(
            conn=client,
            pubkey=mint_pubkey,
            program_id=TOKEN_PROGRAM_ID,
            payer=payer
        )
        
        # Инициализируем минт
        await token.create_mint(
            mint_authority=payer.pubkey(),
            decimals=decimals,
            freeze_authority=payer.pubkey(),
        )
        
        print(f"[+] Создан токен {name} ({symbol}): {mint_pubkey}")
        
        # Создаем ATA для владельца
        owner_ata = get_associated_token_address(payer.pubkey(), mint_pubkey)
        
        # Проверяем существование ATA
        ata_info = await client.get_account_info(owner_ata)
        if not ata_info.value:
            # Создаем ATA если не существует
            tx = Transaction()
            tx.add(create_associated_token_account(
                payer=payer.pubkey(),
                owner=payer.pubkey(),
                mint=mint_pubkey
            ))
            await client.send_transaction(tx, payer)
            print(f"[+] Создан ATA для владельца: {owner_ata}")
        
        # Минтим токены
        initial_supply = 1_000_000_000  # 1000 токенов с decimals=6
        await token.mint_to(
            dest=owner_ata,
            mint_authority=payer,
            amount=initial_supply
        )
        print(f"[+] Выпущено {initial_supply / (10**decimals)} токенов на аккаунт {owner_ata}")
        
        # Добавляем специфичные уязвимости в зависимости от типа
        vulnerability_description = VULNERABILITIES.get(vulnerability_type, "Базовый токен без уязвимостей")
        
        # Сохраняем информацию о созданном токене
        token_info = VulnerableToken(
            name=name,
            symbol=symbol,
            decimals=decimals,
            mint_address=str(mint_pubkey),
            mint_authority=str(payer.pubkey()),
            mint_authority_private_key=payer.to_bytes().hex(),
            supply=initial_supply,
            vulnerability_type=vulnerability_type or "none",
            vulnerability_description=vulnerability_description,
            creation_time=int(time.time())
        )
        
        return token_info
        
    except Exception as e:
        print(f"[!] Ошибка при создании токена {name}: {e}")
        return None


async def create_all_vulnerable_tokens(client: AsyncClient, payer: Keypair) -> List[VulnerableToken]:
    """Создает набор токенов с различными уязвимостями"""
    tokens = []
    
    # 1. Базовый токен без уязвимостей (для контроля)
    base_token = await create_token(
        client=client,
        payer=payer,
        name="Secure Token",
        symbol="SECURE",
        decimals=9,
        vulnerability_type=None
    )
    if base_token:
        tokens.append(base_token)
    
    # 2. Токен с уязвимостью повторного входа
    reentrancy_token = await create_token(
        client=client,
        payer=payer,
        name="Reentrancy Vulnerable Token",
        symbol="REENT",
        decimals=9,
        vulnerability_type="reentrancy"
    )
    if reentrancy_token:
        tokens.append(reentrancy_token)
    
    # 3. Токен без проверок баланса
    no_balance_token = await create_token(
        client=client,
        payer=payer,
        name="No Balance Check Token",
        symbol="NOBAL",
        decimals=9,
        vulnerability_type="no_balance_check"
    )
    if no_balance_token:
        tokens.append(no_balance_token)
    
    # 4. Токен без проверки владельца
    no_owner_token = await create_token(
        client=client,
        payer=payer,
        name="No Owner Verification Token",
        symbol="NOOWN",
        decimals=9,
        vulnerability_type="no_owner_verification"
    )
    if no_owner_token:
        tokens.append(no_owner_token)
    
    # 5. Токен с уязвимостью двойной траты
    double_spend_token = await create_token(
        client=client,
        payer=payer,
        name="Double Spend Token",
        symbol="DBLSP",
        decimals=9,
        vulnerability_type="double_spend"
    )
    if double_spend_token:
        tokens.append(double_spend_token)
    
    return tokens


async def main():
    # Загружаем настройки из .env
    load_dotenv()
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    privkey_hex = os.getenv('SOLANA_PRIVKEY')
    
    if not privkey_hex:
        print("[!] SOLANA_PRIVKEY не найден в .env файле")
        return
    
    # Создаем клиент и keypair плательщика
    client = AsyncClient(rpc_url)
    payer = Keypair.from_bytes(bytes.fromhex(privkey_hex))
    
    try:
        # Проверяем баланс
        balance = await client.get_balance(payer.pubkey())
        print(f"[+] Баланс кошелька: {balance.value / 1_000_000_000} SOL")
        
        if balance.value < 10_000_000:  # Минимум 0.01 SOL
            print("[!] Недостаточно SOL для создания токенов")
            return
        
        # Создаем все токены
        print("\n[+] Начинаем создание токенов с уязвимостями...")
        tokens = await create_all_vulnerable_tokens(client, payer)
        
        # Сохраняем информацию о токенах
        if tokens:
            # Преобразуем dataclass в словари для JSON
            tokens_data = [
                {
                    "name": token.name,
                    "symbol": token.symbol,
                    "decimals": token.decimals,
                    "mint_address": token.mint_address,
                    "mint_authority": token.mint_authority,
                    "supply": token.supply,
                    "vulnerability_type": token.vulnerability_type,
                    "vulnerability_description": token.vulnerability_description,
                    "creation_time": token.creation_time
                }
                for token in tokens
            ]
            
            # Сохраняем в JSON
            with open("vulnerable_tokens.json", "w", encoding="utf-8") as f:
                json.dump(tokens_data, f, indent=4)
            
            # Создаем отчет Markdown
            with open("VULNERABLE_TOKENS_REPORT.md", "w", encoding="utf-8") as f:
                f.write("# Отчет о созданных уязвимых токенах\n\n")
                f.write(f"Дата создания: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## Список созданных токенов\n\n")
                for token in tokens:
                    f.write(f"### {token.name} ({token.symbol})\n\n")
                    f.write(f"- **Адрес минта:** {token.mint_address}\n")
                    f.write(f"- **Decimals:** {token.decimals}\n")
                    f.write(f"- **Тип уязвимости:** {token.vulnerability_type}\n")
                    f.write(f"- **Описание уязвимости:** {token.vulnerability_description}\n\n")
                
                f.write("## Как тестировать\n\n")
                f.write("Для тестирования эксплойтов используйте скрипт `test_vulnerable_tokens.py` с указанием адреса минта токена:\n\n")
                f.write("```bash\npython test_vulnerable_tokens.py --token <mint_address>\n```\n\n")
            
            print(f"\n[+] Создано токенов: {len(tokens)}")
            print(f"[+] Информация сохранена в vulnerable_tokens.json")
            print(f"[+] Отчет сохранен в VULNERABLE_TOKENS_REPORT.md")
            
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
