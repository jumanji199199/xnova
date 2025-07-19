#!/usr/bin/env python3
"""
Создание уязвимого токен-аккаунта и перевод токенов на него (solana-py + solders):
- Генерирует новый Keypair (solders)
- Создаёт ATA для вашего тестового mint (через solana-py, адреса преобразуются)
- Переводит туда токены с вашего основного аккаунта
- Сохраняет приватник и адреса для drain-теста
"""
import asyncio
import json
import os
from solders.keypair import Keypair as SoldersKeypair
from solders.pubkey import Pubkey as SoldersPubkey
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from solana.transaction import Transaction
from spl.token.instructions import create_associated_token_account, get_associated_token_address, transfer_checked
from spl.token.constants import TOKEN_PROGRAM_ID
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
    
    payer = SoldersKeypair.from_bytes(bytes.fromhex(privkey_hex))
    mint_pubkey = SoldersPubkey.from_string(mint_address)
    client = AsyncClient(rpc_url)

    # Генерируем уязвимый аккаунт
    vuln_keypair = SoldersKeypair()
    vuln_pubkey = vuln_keypair.pubkey()
    print(f"[VULN] Сгенерирован уязвимый pubkey: {vuln_pubkey}")

    # Преобразуем solders.pubkey в solana.publickey.PublicKey
    mint_pub = PublicKey(bytes(mint_pubkey))
    payer_pub = PublicKey(bytes(payer.pubkey()))
    vuln_pub = PublicKey(bytes(vuln_pubkey))

    # Создаём ATA для mint на уязвимом pubkey
    vuln_ata = get_associated_token_address(vuln_pub, mint_pub)
    print(f"[VULN] ATA для атаки: {vuln_ata}")

    # Создаём ATA через транзакцию, если не существует
    try:
        ata_info = await client.get_account_info(str(vuln_ata))
        if not ata_info.value:
            tx = Transaction()
            tx.add(create_associated_token_account(payer_pub, vuln_pub, mint_pub))
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
        owner_ata = get_associated_token_address(payer_pub, mint_pub)
        amount = 100_000  # 0.1 токена (6 decimals)
        tx = Transaction()
        tx.add(transfer_checked(
            source=owner_ata,
            dest=vuln_ata,
            owner=payer_pub,
            mint=mint_pub,
            amount=amount,
            decimals=6,
            program_id=TOKEN_PROGRAM_ID,
        ))
        tx_sig = await client.send_transaction(tx, payer)
        print(f"[TRANSFER] {amount/1e6} токена переведено на уязвимый ATA! Tx: {tx_sig.value}")
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
