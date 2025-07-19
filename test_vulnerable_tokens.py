#!/usr/bin/env python3
"""
Тестирование эксплойтов на созданных уязвимых токенах:
- Запускает различные эксплойты на указанном токене
- Проверяет успешность выполнения эксплойтов
- Генерирует подробный отчет о результатах
"""
import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.pubkey import Pubkey as PublicKey

# Настраиваем пути для импорта модулей
sys.path.append(str(Path(__file__).parent))
from src.exploits.token_exploit import TokenExploit
from src.exploits.reentrancy_exploit import ReentrancyExploit
from src.exploits.account_exploit import AccountExploit
from src.exploits.base_exploit import ExploitResult, ExploitStatus

from dotenv import load_dotenv

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("vuln_token_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def load_vulnerable_token(token_address: str) -> Optional[Dict[str, Any]]:
    """Загружает информацию о уязвимом токене из файла"""
    try:
        with open("vulnerable_tokens.json", "r", encoding="utf-8") as f:
            tokens = json.load(f)
        
        for token in tokens:
            if token["mint_address"] == token_address:
                return token
        
        logger.error(f"Токен с адресом {token_address} не найден в vulnerable_tokens.json")
        return None
    except Exception as e:
        logger.error(f"Ошибка при загрузке информации о токене: {e}")
        return None


async def create_and_fund_test_account(client: AsyncClient, payer: Keypair, amount: float = 0.1) -> Optional[Keypair]:
    """Создает тестовый аккаунт и отправляет на него SOL"""
    try:
        test_account = Keypair()
        test_pubkey = test_account.pubkey()
        
        # Конвертируем SOL в лампорты
        lamports = int(amount * 1_000_000_000)
        
        from solana.transaction import Transaction
        from solders.system_program import TransferParams, transfer
        
        # Создаем и отправляем транзакцию
        tx = Transaction()
        tx.add(transfer(TransferParams(
            from_pubkey=payer.pubkey(),
            to_pubkey=test_pubkey,
            lamports=lamports
        )))
        
        signature = await client.send_transaction(tx, payer)
        logger.info(f"Создан тестовый аккаунт {test_pubkey} и отправлено {amount} SOL, подпись: {signature.value}")
        
        # Ждем подтверждения транзакции
        await client.confirm_transaction(signature.value)
        
        # Проверяем баланс
        balance = await client.get_balance(test_pubkey)
        logger.info(f"Баланс тестового аккаунта: {balance.value / 1_000_000_000} SOL")
        
        return test_account
    except Exception as e:
        logger.error(f"Ошибка при создании тестового аккаунта: {e}")
        return None


async def test_token_exploit(client: AsyncClient, token_info: Dict[str, Any], payer: Keypair) -> Dict[str, Any]:
    """Тестирует TokenExploit на указанном токене"""
    result = {
        "exploit_type": "TokenExploit",
        "token_name": token_info["name"],
        "token_address": token_info["mint_address"],
        "vulnerability": token_info["vulnerability_type"],
        "success": False,
        "details": {},
        "error": None
    }
    
    try:
        # Создаем экземпляр эксплойта
        exploit = TokenExploit(
            connection=client,
            attacker_keypair=payer,
            logger=logger
        )
        
        # Запускаем сканирование
        token_pubkey = PublicKey.from_string(token_info["mint_address"])
        scan_result = await exploit.scan_target(token_pubkey)
        
        result["details"]["scan"] = {
            "vulnerable": scan_result.get("vulnerable", False),
            "reason": scan_result.get("reason", ""),
            "findings": scan_result
        }
        
        # Если токен уязвим, пытаемся выполнить эксплойт
        if scan_result.get("vulnerable", False):
            # Подготовка эксплойта
            prepare_result = await exploit.prepare_exploit(token_pubkey)
            result["details"]["prepare"] = {"success": prepare_result}
            
            if prepare_result:
                # Выполнение эксплойта
                exploit_result = await exploit.execute_exploit(token_pubkey)
                result["success"] = exploit_result.status == ExploitStatus.SUCCESS
                
                result["details"]["execute"] = {
                    "status": exploit_result.status.name,
                    "extracted_value": exploit_result.extracted_value,
                    "execution_time": exploit_result.execution_time,
                    "transaction_signatures": exploit_result.transaction_signatures,
                    "error_message": exploit_result.error_message
                }
        else:
            result["details"]["reason"] = "Токен не уязвим к TokenExploit"
    except Exception as e:
        logger.error(f"Ошибка при тестировании TokenExploit: {e}")
        result["error"] = str(e)
    
    return result


async def test_reentrancy_exploit(client: AsyncClient, token_info: Dict[str, Any], payer: Keypair) -> Dict[str, Any]:
    """Тестирует ReentrancyExploit на указанном токене"""
    result = {
        "exploit_type": "ReentrancyExploit",
        "token_name": token_info["name"],
        "token_address": token_info["mint_address"],
        "vulnerability": token_info["vulnerability_type"],
        "success": False,
        "details": {},
        "error": None
    }
    
    try:
        # Создаем экземпляр эксплойта
        exploit = ReentrancyExploit(
            connection=client,
            attacker_keypair=payer,
            logger=logger
        )
        
        # Запускаем сканирование
        token_pubkey = PublicKey.from_string(token_info["mint_address"])
        scan_result = await exploit.scan_target(token_pubkey)
        
        result["details"]["scan"] = {
            "vulnerable": scan_result.get("vulnerable", False),
            "reason": scan_result.get("reason", ""),
            "vulnerabilities": len(scan_result) if isinstance(scan_result, list) else 0
        }
        
        # Если найдены уязвимости, пытаемся выполнить эксплойт
        if scan_result and (isinstance(scan_result, list) and len(scan_result) > 0 or 
                        isinstance(scan_result, dict) and scan_result.get("vulnerable", False)):
            # Подготовка эксплойта
            prepare_result = await exploit.prepare_exploit(token_pubkey)
            result["details"]["prepare"] = {"success": prepare_result}
            
            if prepare_result:
                # Выполнение эксплойта
                exploit_result = await exploit.execute_exploit(token_pubkey)
                result["success"] = exploit_result.status == ExploitStatus.SUCCESS
                
                result["details"]["execute"] = {
                    "status": exploit_result.status.name,
                    "extracted_value": exploit_result.extracted_value,
                    "execution_time": exploit_result.execution_time,
                    "transaction_signatures": exploit_result.transaction_signatures,
                    "error_message": exploit_result.error_message
                }
        else:
            result["details"]["reason"] = "Токен не уязвим к ReentrancyExploit"
    except Exception as e:
        logger.error(f"Ошибка при тестировании ReentrancyExploit: {e}")
        result["error"] = str(e)
    
    return result


async def test_account_exploit(client: AsyncClient, token_info: Dict[str, Any], payer: Keypair) -> Dict[str, Any]:
    """Тестирует AccountExploit на указанном токене"""
    result = {
        "exploit_type": "AccountExploit",
        "token_name": token_info["name"],
        "token_address": token_info["mint_address"],
        "vulnerability": token_info["vulnerability_type"],
        "success": False,
        "details": {},
        "error": None
    }
    
    try:
        # Создаем экземпляр эксплойта
        exploit = AccountExploit(
            connection=client,
            attacker_keypair=payer,
            logger=logger
        )
        
        # Запускаем сканирование
        token_pubkey = PublicKey.from_string(token_info["mint_address"])
        scan_result = await exploit.scan_target(token_pubkey)
        
        result["details"]["scan"] = {
            "vulnerable": scan_result.get("vulnerable", False),
            "reason": scan_result.get("reason", ""),
            "findings": scan_result
        }
        
        # Если аккаунт уязвим, пытаемся выполнить эксплойт
        if scan_result.get("vulnerable", False):
            # Подготовка эксплойта
            prepare_result = await exploit.prepare_exploit(token_pubkey)
            result["details"]["prepare"] = {"success": prepare_result}
            
            if prepare_result:
                # Выполнение эксплойта
                exploit_result = await exploit.execute_exploit(token_pubkey)
                result["success"] = exploit_result.status == ExploitStatus.SUCCESS
                
                result["details"]["execute"] = {
                    "status": exploit_result.status.name,
                    "extracted_value": exploit_result.extracted_value,
                    "execution_time": exploit_result.execution_time,
                    "transaction_signatures": exploit_result.transaction_signatures,
                    "error_message": exploit_result.error_message
                }
        else:
            result["details"]["reason"] = "Токен не уязвим к AccountExploit"
    except Exception as e:
        logger.error(f"Ошибка при тестировании AccountExploit: {e}")
        result["error"] = str(e)
    
    return result


async def test_all_exploits(client: AsyncClient, token_info: Dict[str, Any], payer: Keypair) -> Dict[str, Any]:
    """Запускает все эксплойты на указанном токене"""
    logger.info(f"Начинаем тестирование эксплойтов для токена {token_info['name']} ({token_info['mint_address']})")
    
    results = {
        "token_name": token_info["name"],
        "token_symbol": token_info["symbol"],
        "token_address": token_info["mint_address"],
        "vulnerability_type": token_info["vulnerability_type"],
        "test_timestamp": int(time.time()),
        "exploits": []
    }
    
    # Тестируем TokenExploit
    logger.info("Тестирование TokenExploit...")
    token_exploit_result = await test_token_exploit(client, token_info, payer)
    results["exploits"].append(token_exploit_result)
    
    # Тестируем ReentrancyExploit
    logger.info("Тестирование ReentrancyExploit...")
    reentrancy_exploit_result = await test_reentrancy_exploit(client, token_info, payer)
    results["exploits"].append(reentrancy_exploit_result)
    
    # Тестируем AccountExploit
    logger.info("Тестирование AccountExploit...")
    account_exploit_result = await test_account_exploit(client, token_info, payer)
    results["exploits"].append(account_exploit_result)
    
    # Подсчитываем общую статистику
    successful_exploits = sum(1 for exploit in results["exploits"] if exploit["success"])
    results["success_rate"] = successful_exploits / len(results["exploits"])
    results["successful_exploits"] = successful_exploits
    results["total_exploits"] = len(results["exploits"])
    
    return results


async def main():
    parser = argparse.ArgumentParser(description="Тестирование эксплойтов на уязвимых токенах")
    parser.add_argument("--token", type=str, help="Адрес минта токена для тестирования")
    parser.add_argument("--all", action="store_true", help="Тестировать все созданные токены")
    args = parser.parse_args()
    
    # Загружаем настройки из .env
    load_dotenv()
    rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com')
    privkey_hex = os.getenv('SOLANA_PRIVKEY')
    
    if not privkey_hex:
        logger.error("SOLANA_PRIVKEY не найден в .env файле")
        return
    
    # Создаем клиент и keypair плательщика
    client = AsyncClient(rpc_url)
    payer = Keypair.from_bytes(bytes.fromhex(privkey_hex))
    
    try:
        # Проверяем баланс
        balance = await client.get_balance(payer.pubkey())
        logger.info(f"Баланс кошелька: {balance.value / 1_000_000_000} SOL")
        
        if balance.value < 10_000_000:  # Минимум 0.01 SOL
            logger.error("Недостаточно SOL для выполнения тестов")
            return
        
        all_results = []
        
        if args.all:
            # Тестирование всех токенов
            try:
                with open("vulnerable_tokens.json", "r", encoding="utf-8") as f:
                    tokens = json.load(f)
                
                logger.info(f"Найдено {len(tokens)} токенов для тестирования")
                for token in tokens:
                    logger.info(f"Тестирование токена {token['name']} ({token['mint_address']})...")
                    result = await test_all_exploits(client, token, payer)
                    all_results.append(result)
            except Exception as e:
                logger.error(f"Ошибка при загрузке списка токенов: {e}")
                return
        elif args.token:
            # Тестирование указанного токена
            token_info = await load_vulnerable_token(args.token)
            if token_info:
                logger.info(f"Тестирование токена {token_info['name']} ({token_info['mint_address']})...")
                result = await test_all_exploits(client, token_info, payer)
                all_results.append(result)
        else:
            logger.error("Не указаны параметры для тестирования. Используйте --token или --all")
            return
        
        # Сохраняем результаты
        if all_results:
            timestamp = int(time.time())
            with open(f"exploit_test_results_{timestamp}.json", "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=4)
            
            # Создаем отчет Markdown
            with open(f"EXPLOIT_TEST_REPORT_{timestamp}.md", "w", encoding="utf-8") as f:
                f.write("# Отчет о тестировании эксплойтов на уязвимых токенах\n\n")
                f.write(f"Дата тестирования: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Общая статистика
                total_tokens = len(all_results)
                successful_tokens = sum(1 for result in all_results if any(exploit["success"] for exploit in result["exploits"]))
                success_rate = successful_tokens / total_tokens if total_tokens > 0 else 0
                
                f.write(f"## Общая статистика\n\n")
                f.write(f"- **Всего токенов протестировано:** {total_tokens}\n")
                f.write(f"- **Успешно проэксплуатировано токенов:** {successful_tokens}\n")
                f.write(f"- **Процент успеха:** {success_rate * 100:.1f}%\n\n")
                
                # Детали по каждому токену
                for result in all_results:
                    f.write(f"## {result['token_name']} ({result['token_symbol']})\n\n")
                    f.write(f"- **Адрес минта:** {result['token_address']}\n")
                    f.write(f"- **Тип уязвимости:** {result['vulnerability_type']}\n")
                    f.write(f"- **Успешных эксплойтов:** {result['successful_exploits']}/{result['total_exploits']}\n\n")
                    
                    f.write("### Результаты эксплойтов\n\n")
                    for exploit in result["exploits"]:
                        status = "✅ Успешно" if exploit["success"] else "❌ Неуспешно"
                        f.write(f"- **{exploit['exploit_type']}:** {status}\n")
                        if exploit["error"]:
                            f.write(f"  - Ошибка: {exploit['error']}\n")
                        if "execute" in exploit["details"] and exploit["details"]["execute"].get("error_message"):
                            f.write(f"  - Сообщение об ошибке: {exploit['details']['execute']['error_message']}\n")
                    f.write("\n")
            
            logger.info(f"Результаты сохранены в exploit_test_results_{timestamp}.json")
            logger.info(f"Отчет сохранен в EXPLOIT_TEST_REPORT_{timestamp}.md")
            
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
