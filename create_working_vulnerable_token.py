#!/usr/bin/env python3
"""
СОЗДАНИЕ РАБОЧЕГО УЯЗВИМОГО SPL ТОКЕНА
Упрощенная версия для практического тестирования эксплойтов
"""

import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from solders.system_program import create_account, CreateAccountParams
from solders.instruction import Instruction
import struct

# Константы SPL Token Program
TOKEN_PROGRAM_ID = PublicKey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
MINT_SIZE = 82
TOKEN_ACCOUNT_SIZE = 165

class SimpleVulnerableToken:
    """Создатель простого уязвимого токена"""
    
    def __init__(self):
        load_dotenv()
        self.rpc_url = os.getenv('SOLANA_RPC_URL')
        self.private_key_hex = os.getenv('SOLANA_PRIVKEY')
        
        # Создание keypair из приватного ключа
        private_key_bytes = bytes.fromhex(self.private_key_hex)
        self.payer = Keypair.from_bytes(private_key_bytes)
        
        self.client = AsyncClient(self.rpc_url)
        
    async def create_vulnerable_token(self):
        """Создает простой уязвимый токен"""
        
        print("\n=== СОЗДАНИЕ РАБОЧЕГО УЯЗВИМОГО ТОКЕНА ===")
        
        try:
            # Проверка баланса
            balance_resp = await self.client.get_balance(self.payer.pubkey())
            balance_sol = balance_resp.value / 1_000_000_000
            print(f"[BALANCE] Баланс: {balance_sol} SOL")
            
            if balance_sol < 0.01:
                raise Exception("Недостаточно SOL (нужно минимум 0.01)")
            
            # Создаем новый mint keypair
            mint = Keypair()
            print(f"[MINT] Создаем токен: {mint.pubkey()}")
            
            # Получаем минимальный rent-exempt баланс
            rent = await self.client.get_minimum_balance_for_rent_exemption(MINT_SIZE)
            
            # Создаем транзакцию
            tx = Transaction()
            
            # 1. Создаем mint account
            create_mint_account_ix = create_account(
                CreateAccountParams(
                    from_pubkey=self.payer.pubkey(),
                    to_pubkey=mint.pubkey(),
                    lamports=rent.value,
                    space=MINT_SIZE,
                    owner=TOKEN_PROGRAM_ID
                )
            )
            tx.add(create_mint_account_ix)
            
            # 2. Инициализируем mint с УЯЗВИМОСТЯМИ
            # УЯЗВИМОСТЬ 1: decimals = 0 (может вызвать проблемы с округлением)
            # УЯЗВИМОСТЬ 2: mint_authority = публичный известный ключ
            # УЯЗВИМОСТЬ 3: freeze_authority = None
            
            # Используем известный публичный ключ как mint authority
            # Это позволит любому, кто знает соответствующий приватный ключ, минтить токены
            weak_authority = PublicKey.from_string("11111111111111111111111111111111")
            
            # InitializeMint instruction data
            # [instruction_id(1), decimals(1), mint_authority(32), freeze_authority_option(1), freeze_authority(32)]
            init_mint_data = bytearray()
            init_mint_data.extend(struct.pack("<B", 0))  # InitializeMint instruction
            init_mint_data.extend(struct.pack("<B", 0))  # decimals = 0 (УЯЗВИМОСТЬ!)
            init_mint_data.extend(bytes(weak_authority))  # mint authority
            init_mint_data.extend(struct.pack("<B", 0))  # freeze authority = None (УЯЗВИМОСТЬ!)
            
            init_mint_ix = Instruction(
                program_id=TOKEN_PROGRAM_ID,
                accounts=[
                    {"pubkey": mint.pubkey(), "is_signer": False, "is_writable": True},
                    {"pubkey": PublicKey.from_string("SysvarRent111111111111111111111111111111111"), "is_signer": False, "is_writable": False}
                ],
                data=bytes(init_mint_data)
            )
            tx.add(init_mint_ix)
            
            # Получаем последний blockhash
            recent_blockhash = await self.client.get_latest_blockhash()
            tx.recent_blockhash = recent_blockhash.value.blockhash
            
            # Подписываем транзакцию
            tx.sign(self.payer, mint)
            
            # Отправляем транзакцию
            print("[TX] Отправляем транзакцию создания токена...")
            result = await self.client.send_transaction(tx, self.payer, mint)
            signature = result.value
            print(f"[TX] Подпись: {signature}")
            
            # Ждем подтверждения
            print("[WAIT] Ожидаем подтверждения...")
            await asyncio.sleep(5)
            
            # Проверяем создание
            mint_info = await self.client.get_account_info(mint.pubkey())
            if mint_info.value:
                print("[SUCCESS] Токен успешно создан!")
            else:
                print("[WARNING] Токен может быть не создан, проверьте вручную")
            
            # Сохраняем информацию
            token_info = {
                "mint_address": str(mint.pubkey()),
                "decimals": 0,
                "vulnerabilities": [
                    "zero_decimals - может вызвать проблемы с округлением",
                    "weak_mint_authority - используется известный публичный ключ",
                    "no_freeze_authority - невозможно заморозить токены"
                ],
                "mint_authority": str(weak_authority),
                "freeze_authority": None,
                "created_at": datetime.now().isoformat(),
                "signature": str(signature)
            }
            
            filename = f"vulnerable_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(token_info, f, indent=2)
            
            print(f"\n[SAVE] Сохранено в {filename}")
            print("\n=== УЯЗВИМОСТИ ТОКЕНА ===")
            for vuln in token_info["vulnerabilities"]:
                print(f"  [!] {vuln}")
            
            return token_info
            
        except Exception as e:
            print(f"[ERROR] Ошибка: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await self.client.close()

async def main():
    creator = SimpleVulnerableToken()
    await creator.create_vulnerable_token()

if __name__ == "__main__":
    asyncio.run(main())
