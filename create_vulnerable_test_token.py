#!/usr/bin/env python3
"""
СОЗДАНИЕ УЯЗВИМОГО SPL ТОКЕНА ДЛЯ ТЕСТИРОВАНИЯ ЭКСПЛОЙТОВ
Создает токен с намеренными уязвимостями для валидации exploit-модулей
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey
from solders.system_program import CreateAccountParams, create_account
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction
from spl.token.constants import TOKEN_PROGRAM_ID, MINT_LEN
from spl.token.instructions import (
    InitializeMintParams, initialize_mint,
    MintToParams, mint_to,
    create_associated_token_account,
    get_associated_token_address
)

class VulnerableTokenCreator:
    """Создатель уязвимых токенов для тестирования"""
    
    def __init__(self):
        load_dotenv()
        self.rpc_url = os.getenv('SOLANA_RPC_URL')
        self.private_key_hex = os.getenv('SOLANA_PRIVKEY')
        
        # Создание keypair из приватного ключа
        private_key_bytes = bytes.fromhex(self.private_key_hex)
        self.payer_keypair = Keypair.from_bytes(private_key_bytes)
        
        self.client = AsyncClient(self.rpc_url)
        
    async def create_vulnerable_token(self, vulnerability_type: str = "all") -> Dict[str, Any]:
        """
        Создает токен с намеренными уязвимостями
        
        vulnerability_type:
        - "open_mint" - любой может минтить токены
        - "no_freeze" - отсутствует freeze authority
        - "weak_authority" - слабый контроль authority
        - "all" - все уязвимости сразу
        """
        
        print(f"\n=== СОЗДАНИЕ УЯЗВИМОГО ТОКЕНА ({vulnerability_type}) ===")
        
        # Проверка баланса
        balance = await self.client.get_balance(self.payer_keypair.pubkey())
        balance_sol = balance.value / 1_000_000_000
        print(f"[BALANCE] Баланс: {balance_sol} SOL")
        
        if balance_sol < 0.1:
            raise Exception("Недостаточно SOL для создания токена (нужно минимум 0.1 SOL)")
        
        # Создание mint keypair
        mint_keypair = Keypair()
        print(f"[MINT] Адрес токена: {mint_keypair.pubkey()}")
        
        # 1. Создание mint account с уязвимостями
        tx = Transaction()
        
        # Получение минимального баланса для rent exemption
        min_balance = await self.client.get_minimum_balance_for_rent_exemption(MINT_LEN)
        
        # Создание аккаунта для mint
        create_account_ix = create_account(
            CreateAccountParams(
                from_pubkey=self.payer_keypair.pubkey(),
                to_pubkey=mint_keypair.pubkey(),
                lamports=min_balance.value,
                space=MINT_LEN,
                owner=TOKEN_PROGRAM_ID
            )
        )
        tx.add(create_account_ix)
        
        # Инициализация mint с уязвимостями
        if vulnerability_type in ["open_mint", "all"]:
            # УЯЗВИМОСТЬ: mint_authority = None (любой может минтить)
            mint_authority = None
            print("[VULN] WARNING: Mint authority отсутствует - любой может минтить токены!")
        elif vulnerability_type == "weak_authority":
            # УЯЗВИМОСТЬ: mint_authority = известный публичный ключ
            weak_keypair = Keypair.from_seed(b"weak_authority_seed_12345")
            mint_authority = weak_keypair.pubkey()
            print(f"[VULN] WARNING: Слабый mint authority: {mint_authority}")
        else:
            mint_authority = self.payer_keypair.pubkey()
            
        if vulnerability_type in ["no_freeze", "all"]:
            # УЯЗВИМОСТЬ: freeze_authority = None 
            freeze_authority = None
            print("[VULN] WARNING: Freeze authority отсутствует!")
        else:
            freeze_authority = self.payer_keypair.pubkey()
            
        init_mint_ix = initialize_mint(
            InitializeMintParams(
                mint=mint_keypair.pubkey(),
                decimals=9,
                mint_authority=mint_authority or self.payer_keypair.pubkey(),
                freeze_authority=freeze_authority,
                program_id=TOKEN_PROGRAM_ID
            )
        )
        tx.add(init_mint_ix)
        
        # Отправка транзакции создания mint
        print("[TX] Отправка транзакции создания токена...")
        recent_blockhash = await self.client.get_latest_blockhash()
        tx.recent_blockhash = recent_blockhash.value.blockhash
        tx.sign(self.payer_keypair, mint_keypair)
        
        result = await self.client.send_transaction(tx, self.payer_keypair, mint_keypair)
        print(f"[TX] Подпись: {result.value}")
        
        # Ждем подтверждения
        await asyncio.sleep(2)
        
        # 2. Создание associated token account
        ata = get_associated_token_address(
            owner=self.payer_keypair.pubkey(),
            mint=mint_keypair.pubkey()
        )
        
        # Создание ATA
        create_ata_ix = create_associated_token_account(
            payer=self.payer_keypair.pubkey(),
            owner=self.payer_keypair.pubkey(),
            mint=mint_keypair.pubkey()
        )
        
        tx2 = Transaction()
        tx2.add(create_ata_ix)
        
        # Минтинг начального запаса
        if mint_authority is not None:
            mint_amount = 1_000_000 * 10**9  # 1M токенов
            mint_to_ix = mint_to(
                MintToParams(
                    mint=mint_keypair.pubkey(),
                    dest=ata,
                    mint_authority=self.payer_keypair.pubkey(),
                    amount=mint_amount,
                    program_id=TOKEN_PROGRAM_ID
                )
            )
            tx2.add(mint_to_ix)
            print(f"[MINT] Минтинг {mint_amount / 10**9} токенов...")
        
        # Отправка второй транзакции
        recent_blockhash2 = await self.client.get_latest_blockhash()
        tx2.recent_blockhash = recent_blockhash2.value.blockhash
        tx2.sign(self.payer_keypair)
        
        result2 = await self.client.send_transaction(tx2, self.payer_keypair)
        print(f"[TX] Подпись ATA/Mint: {result2.value}")
        
        # 3. Создание дополнительных уязвимых аккаунтов
        vulnerable_accounts = []
        
        if vulnerability_type in ["weak_authority", "all"]:
            # Создаем токен-аккаунт с известным приватным ключом
            weak_owner = Keypair.from_seed(b"vulnerable_account_seed_99999")
            weak_ata = get_associated_token_address(
                owner=weak_owner.pubkey(),
                mint=mint_keypair.pubkey()
            )
            
            print(f"[VULN] WARNING: Создание уязвимого аккаунта: {weak_ata}")
            print(f"[VULN] WARNING: Владелец с известным seed: {weak_owner.pubkey()}")
            
            vulnerable_accounts.append({
                "address": str(weak_ata),
                "owner": str(weak_owner.pubkey()),
                "vulnerability": "known_seed",
                "seed": "vulnerable_account_seed_99999"
            })
        
        # Сохранение информации о токене
        token_info = {
            "mint_address": str(mint_keypair.pubkey()),
            "token_account": str(ata),
            "owner": str(self.payer_keypair.pubkey()),
            "decimals": 9,
            "supply": 1_000_000 if mint_authority else 0,
            "vulnerabilities": {
                "open_mint": mint_authority is None,
                "no_freeze": freeze_authority is None,
                "weak_authority": vulnerability_type == "weak_authority",
                "vulnerable_accounts": vulnerable_accounts
            },
            "mint_authority": str(mint_authority) if mint_authority else None,
            "freeze_authority": str(freeze_authority) if freeze_authority else None,
            "created_at": datetime.now().isoformat(),
            "vulnerability_type": vulnerability_type
        }
        
        # Сохранение в файл
        filename = f"vulnerable_token_{vulnerability_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(token_info, f, indent=2)
        
        print(f"\n=== УЯЗВИМЫЙ ТОКЕН СОЗДАН ===")
        print(f"[SAVE] Информация сохранена в {filename}")
        print(f"\n[SUMMARY] Уязвимости:")
        for vuln, status in token_info["vulnerabilities"].items():
            if vuln != "vulnerable_accounts" and status:
                print(f"  [+] {vuln}")
        
        await self.client.close()
        return token_info

async def main():
    """Создание различных типов уязвимых токенов"""
    creator = VulnerableTokenCreator()
    
    # Создаем токен со всеми уязвимостями
    try:
        token_info = await creator.create_vulnerable_token("all")
        print(f"\n[SUCCESS] Токен создан успешно!")
        print(f"Mint: {token_info['mint_address']}")
        
    except Exception as e:
        print(f"\n[ERROR] Ошибка создания токена: {e}")

if __name__ == "__main__":
    asyncio.run(main())
