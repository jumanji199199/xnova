#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Создание тестового SPL токена для безопасного тестирования эксплойтов
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
from spl.token.instructions import (
    initialize_mint, InitializeMintParams,
    create_associated_token_account,
    mint_to, MintToParams,
    get_associated_token_address
)
from solana.transaction import Transaction

# Устанавливаем UTF-8 кодировку для Windows консоли
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

class TestSPLTokenCreator:
    """Создатель тестового SPL токена"""
    
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
        
    async def create_test_token(self) -> dict:
        """Создает тестовый SPL токен"""
        print(f"\n🪙 [CREATE] Создание тестового SPL токена...")
        
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
            
            # Генерируем новый keypair для mint (адрес токена)
            mint_keypair = Keypair()
            print(f"[MINT] Mint address: {mint_keypair.pubkey()}")
            
            # Создаем mint account
            print(f"[STEP 1] Создание mint account...")
            
            # Сначала создаем account для mint
            from solders.system_program import create_account, CreateAccountParams
            
            # Получаем минимальный баланс для rent-exempt mint account
            mint_size = 82  # размер mint account в байтах
            rent_response = await client.get_minimum_balance_for_rent_exemption(mint_size)
            rent_lamports = rent_response.value
            
            create_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=self.payer_keypair.pubkey(),
                    to_pubkey=mint_keypair.pubkey(),  # 🔧 Исправлено: to_pubkey вместо new_account_pubkey
                    lamports=rent_lamports,
                    space=mint_size,
                    owner=TOKEN_PROGRAM_ID  # 🔧 Исправлено: owner вместо program_id
                )
            )
            
            # Инициализируем mint
            initialize_mint_ix = initialize_mint(
                InitializeMintParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint_keypair.pubkey(),
                    decimals=6,  # 6 знаков после запятой (как у USDC)
                    mint_authority=self.payer_keypair.pubkey(),
                    freeze_authority=self.payer_keypair.pubkey()
                )
            )
            
            # Получаем associated token account address
            token_account = get_associated_token_address(
                self.payer_keypair.pubkey(),
                mint_keypair.pubkey()
            )
            print(f"[TOKEN_ACCOUNT] Token account: {token_account}")
            
            # Создаем associated token account
            print(f"[STEP 2] Создание token account...")
            create_token_account_ix = create_associated_token_account(
                payer=self.payer_keypair.pubkey(),
                owner=self.payer_keypair.pubkey(),
                mint=mint_keypair.pubkey()
            )
            
            # Минтим тестовые токены (1000 токенов = 1000 * 10^6 = 1,000,000,000 raw units)
            test_amount = 1000 * (10 ** 6)  # 1000 токенов с 6 decimals
            print(f"[STEP 3] Минтинг {test_amount / (10**6)} тестовых токенов...")
            mint_to_ix = mint_to(
                MintToParams(
                    program_id=TOKEN_PROGRAM_ID,
                    mint=mint_keypair.pubkey(),
                    dest=token_account,
                    mint_authority=self.payer_keypair.pubkey(),
                    amount=test_amount
                )
            )
            
            # Собираем транзакцию
            recent_blockhash = await client.get_latest_blockhash()
            transaction = Transaction(recent_blockhash=recent_blockhash.value.blockhash)
            transaction.add(create_account_ix)  # Создаем account для mint
            transaction.add(initialize_mint_ix)  # Инициализируем mint
            transaction.add(create_token_account_ix)  # Создаем token account
            transaction.add(mint_to_ix)  # Минтим токены
            
            # 🔧 ИСПРАВЛЯЕМ ПОДПИСАНИЕ: Подписываем транзакцию всеми необходимыми keypairs
            # payer_keypair - fee payer, mint_keypair - для создания mint account
            transaction.sign(self.payer_keypair, mint_keypair)
            
            # Отправляем транзакцию
            print(f"[SEND] Отправка транзакции...")
            result = await client.send_transaction(
                transaction,
                opts=TxOpts(skip_preflight=False, preflight_commitment="confirmed")
            )
            
            signature = result.value
            print(f"[SIGNATURE] Транзакция: {signature}")
            
            # Ждем подтверждения
            print(f"[WAIT] Ожидание подтверждения...")
            await client.confirm_transaction(signature)
            
            print(f"✅ [SUCCESS] SPL токен создан успешно!")
            
            token_info = {
                "success": True,
                "mint_address": str(mint_keypair.pubkey()),
                "token_account": str(token_account),
                "owner": str(self.payer_keypair.pubkey()),
                "amount": test_amount,
                "decimals": 6,
                "ui_amount": test_amount / (10 ** 6),
                "signature": str(signature)
            }
            
            # Сохраняем информацию о токене
            import json
            with open("test_spl_token_info.json", "w", encoding="utf-8") as f:
                json.dump(token_info, f, indent=2, ensure_ascii=False)
            
            print(f"[SAVE] Информация сохранена в test_spl_token_info.json")
            
            await client.close()
            return token_info
            
        except Exception as e:
            print(f"❌ [ERROR] Ошибка создания SPL токена: {e}")
            return {"success": False, "error": str(e)}

async def main():
    """Главная функция"""
    print("🚀 === СОЗДАНИЕ ТЕСТОВОГО SPL ТОКЕНА ===")
    
    creator = TestSPLTokenCreator()
    result = await creator.create_test_token()
    
    if result["success"]:
        print(f"\n🎉 === ТОКЕН СОЗДАН УСПЕШНО ===")
        print(f"Mint Address: {result['mint_address']}")
        print(f"Token Account: {result['token_account']}")
        print(f"Amount: {result['ui_amount']} токенов")
        print(f"Signature: {result['signature']}")
        print(f"\n💡 Теперь можно тестировать TokenExploit на этом SPL токене!")
    else:
        print(f"\n❌ === ОШИБКА СОЗДАНИЯ ТОКЕНА ===")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
