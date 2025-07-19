#!/usr/bin/env python3
"""
Создание уязвимого токен-аккаунта для теста drain-эксплойта:
- Генерирует новый Keypair
- Создаёт ATA для вашего тестового mint
- Переводит туда токены с вашего основного аккаунта
- Выводит адрес для атаки
"""
import asyncio
import json
import os
from solders.keypair import Keypair
from solders.pubkey import Pubkey as SoldersPublicKey
from solana.rpc.async_api import AsyncClient
from spl.token.async_client import AsyncToken
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, create_associated_token_account
from dotenv import load_dotenv

async def main():
    load_dotenv()
    rpc_url = os.getenv('SOLANA_RPC_URL')
    privkey_hex = os.getenv('SOLANA_PRIVKEY')
    mint_address = None
    with open("simple_spl_token_info.json", "r", encoding="utf-8") as f:
        token_info = json.load(f)
        mint_address = token_info["mint_address"]
    
    if not (rpc_url and privkey_hex and mint_address):
        print("[ERROR] Не найдены настройки или mint.")
        return
    
    payer = Keypair.from_bytes(bytes.fromhex(privkey_hex))
    mint_pubkey = SoldersPublicKey.from_string(mint_address)
    client = AsyncClient(rpc_url)

    # Генерируем уязвимый аккаунт
    vuln_keypair = Keypair()
    vuln_pubkey = vuln_keypair.pubkey()
    print(f"[VULN] Сгенерирован уязвимый pubkey: {vuln_pubkey}")

    # Преобразуем все адреса в solana PublicKey
    payer_pub = payer.pubkey()
    vuln_pub = vuln_pubkey
    mint_pub = mint_pubkey

    # Создаём ATA для mint на уязвимом pubkey
    vuln_ata = get_associated_token_address(vuln_pub, mint_pub)
    print(f"[VULN] ATA для атаки: {vuln_ata}")

    # Создаём ATA через транзакцию, если не существует
    try:
        ata_info = await client.get_account_info(vuln_ata)
        if not ata_info.value:
            from solana.transaction import Transaction
            ix = create_associated_token_account(
                payer_pub,
                vuln_pub,
                mint_pub
            )
            tx = Transaction()
            tx.add(ix)
            result = await client.send_transaction(tx, payer)
            print(f"[VULN] ATA создан: {result.value}")
        else:
            print(f"[VULN] ATA уже существует")
    except Exception as e:
        print(f"[ERROR] Ошибка создания ATA: {e}")
        await client.close()
        return

    # Переводим токены с вашего основного ATA на уязвимый
    try:
        token = AsyncToken(
            conn=client,
            pubkey=mint_pubkey,
            program_id=TOKEN_PROGRAM_ID,
            payer=payer
        )
        # Находим ваш основной ATA
        owner_ata = get_associated_token_address(owner=payer.pubkey(), mint=mint_pubkey)
        print(f"[OWNER] Ваш ATA: {owner_ata}")
        amount = 100_000  # 0.1 токена (6 decimals)
        tx_sig = await token.transfer(
            source=owner_ata,
            dest=vuln_ata,
            owner=payer,
            amount=amount
        )
        print(f"[TRANSFER] {amount/1e6} токена переведено на уязвимый ATA! Tx: {tx_sig}")
    except Exception as e:
        print(f"[ERROR] Ошибка перевода токенов: {e}")
    finally:
        await client.close()
    # Сохраняем приватник уязвимого аккаунта для теста
    with open("vuln_token_account.json", "w", encoding="utf-8") as f:
        json.dump({
            "pubkey": str(vuln_pubkey),
            "privkey": vuln_keypair.to_bytes().hex(),
            "ata": str(vuln_ata),
            "mint": str(mint_pubkey)
        }, f, indent=2)
    print("[DONE] Данные уязвимого аккаунта сохранены в vuln_token_account.json")

if __name__ == "__main__":
    asyncio.run(main())
