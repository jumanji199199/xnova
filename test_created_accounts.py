#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестер созданных тестовых аккаунтов
Запускает эксплойты на конкретно наших созданных тестовых аккаунтах
"""

import sys
import os
import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from solders.keypair import Keypair
from solders.pubkey import Pubkey

# Устанавливаем UTF-8 кодировку для Windows консоли
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Настройка путей для импорта
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем модули эксплойтов
try:
    from src.exploits.account_exploit import AccountExploit
    from src.exploits.token_exploit import TokenExploit  
    from src.exploits.program_exploit import ProgramExploit
    from src.exploits.reentrancy_exploit import ReentrancyExploit
except ImportError:
    # Fallback импорты если модульная структура не работает
    import importlib.util
    import inspect
    
    def load_exploit_module(module_name, file_path):
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    # Загружаем модули напрямую
    base_path = os.path.join(os.path.dirname(__file__), 'src', 'exploits')
    account_module = load_exploit_module('account_exploit', os.path.join(base_path, 'account_exploit.py'))
    token_module = load_exploit_module('token_exploit', os.path.join(base_path, 'token_exploit.py'))
    
    AccountExploit = account_module.AccountExploit
    TokenExploit = token_module.TokenExploit

class CreatedAccountTester:
    """Тестер для созданных тестовых аккаунтов"""
    
    def __init__(self):
        load_dotenv()
        
        # Загружаем конфигурацию
        self.setup_config()
        
        # Наши созданные тестовые аккаунты
        self.test_accounts = [
            "EUU3QLhwi5zqDGEWPiGjXtr63oD7BL8zHStTNJ2cstaL",  # excess_lamports
            "BzBgmykB3D35SttCsra93AnVPdCHFgtw2J5o7rKGL8UM"   # normal_account
        ]
        
        print(f"[INIT] Тестер инициализирован")
        print(f"[WALLET] Кошелек: {self.attacker_keypair.pubkey()}")
        print(f"[TARGETS] Тестовых аккаунтов: {len(self.test_accounts)}")
        
    def setup_config(self):
        """Настройка конфигурации"""
        # Обязательные переменные
        self.target_address = os.getenv("SOLANA_TARGET_ADDRESS")
        if not self.target_address:
            raise ValueError("[ERROR] SOLANA_TARGET_ADDRESS не найден!")
        
        # 🔗 КРИТИЧНО: Загружаем новый надежный RPC URL с API ключом!
        self.rpc_url = os.getenv("SOLANA_RPC_URL", "https://api.mainnet.solana.com")
        print(f"[RPC] Используем RPC endpoint: {self.rpc_url}")
            
        # Приватный ключ
        privkey_hex = os.getenv("SOLANA_PRIVKEY")
        if not privkey_hex:
            raise ValueError("[ERROR] SOLANA_PRIVKEY не найден!")
            
        # Преобразование приватного ключа
        try:
            privkey_bytes = bytes.fromhex(privkey_hex)
            self.attacker_keypair = Keypair.from_bytes(privkey_bytes)
        except Exception as e:
            raise ValueError(f"[ERROR] Ошибка загрузки приватного ключа: {e}")
    
    async def test_account_exploit(self, target_address: str) -> Dict[str, Any]:
        """Тестирует Account exploit на целевом аккаунте"""
        print(f"\n[TEST] Testing AccountExploit на {target_address}")
        
        try:
            # 🔗 Передаем надежный RPC URL с API ключом!
            exploit = AccountExploit(self.attacker_keypair, rpc_url=self.rpc_url)
            
            # Конвертируем Base58 адрес в Pubkey объект
            try:
                target_pubkey = Pubkey.from_string(target_address)
                print(f"[PARSE] Адрес сконвертирован: {target_pubkey}")
            except Exception as e:
                print(f"[ERROR] Ошибка парсинга адреса {target_address}: {e}")
                return {
                    "exploit": "AccountExploit",
                    "target": target_address,
                    "success": False,
                    "error": f"Invalid address format: {e}"
                }
            
            # Сканируем цель
            scan_result = await exploit.scan_target(target_pubkey)
            print(f"[SCAN] Результат сканирования: {scan_result}")
            
            if scan_result:
                # Подготавливаем эксплойт
                prep_result = await exploit.prepare_exploit(target_address)
                print(f"[PREP] Подготовка: {prep_result}")
                
                if prep_result:
                    # Выполняем эксплойт
                    exec_result = await exploit.execute_exploit(target_address)
                    print(f"[EXEC] Выполнение: {exec_result}")
                    return {
                        "exploit": "AccountExploit",
                        "target": target_address,
                        "success": exec_result.status.value if exec_result else False,
                        "result": exec_result
                    }
            
            return {
                "exploit": "AccountExploit",
                "target": target_address,
                "success": False,
                "result": "Цель не уязвима или недоступна"
            }
            
        except Exception as e:
            print(f"[ERROR] AccountExploit ошибка: {e}")
            return {
                "exploit": "AccountExploit",
                "target": target_address,
                "success": False,
                "error": str(e)
            }
    
    async def test_token_exploit(self, target_address: str) -> Dict[str, Any]:
        """Тестирует Token exploit на целевом аккаунте"""
        print(f"\n[TEST] Testing TokenExploit на {target_address}")
        
        try:
            # 🔗 Передаем надежный RPC URL с API ключом!
            exploit = TokenExploit(self.attacker_keypair, rpc_url=self.rpc_url)
            
            # Конвертируем Base58 адрес в Pubkey объект
            try:
                target_pubkey = Pubkey.from_string(target_address)
                print(f"[PARSE] Адрес сконвертирован: {target_pubkey}")
            except Exception as e:
                print(f"[ERROR] Ошибка парсинга адреса {target_address}: {e}")
                return {
                    "exploit": "TokenExploit",
                    "target": target_address,
                    "success": False,
                    "error": f"Invalid address format: {e}"
                }
            
            # Сканируем цель
            scan_result = await exploit.scan_target(target_pubkey)
            print(f"[SCAN] Результат сканирования: {scan_result}")
            
            if scan_result:
                # Подготавливаем эксплойт
                prep_result = await exploit.prepare_exploit(target_address)
                print(f"[PREP] Подготовка: {prep_result}")
                
                if prep_result:
                    # Выполняем эксплойт
                    exec_result = await exploit.execute_exploit(target_address)
                    print(f"[EXEC] Выполнение: {exec_result}")
                    return {
                        "exploit": "TokenExploit",
                        "target": target_address,
                        "success": exec_result.status.value if exec_result else False,
                        "result": exec_result
                    }
            
            return {
                "exploit": "TokenExploit",
                "target": target_address,
                "success": False,
                "result": "Цель не уязвима или недоступна"
            }
            
        except Exception as e:
            print(f"[ERROR] TokenExploit ошибка: {e}")
            return {
                "exploit": "TokenExploit",
                "target": target_address,
                "success": False,
                "error": str(e)
            }
    
    async def test_all_exploits(self) -> List[Dict[str, Any]]:
        """Тестирует все эксплойты на всех созданных аккаунтах"""
        print(f"\n[START] === ТЕСТИРОВАНИЕ СОЗДАННЫХ АККАУНТОВ ===")
        print(f"[INFO] Аккаунтов для тестирования: {len(self.test_accounts)}")
        
        results = []
        
        for i, account in enumerate(self.test_accounts, 1):
            print(f"\n[ACCOUNT] {i}/{len(self.test_accounts)}: {account}")
            
            # Тестируем Account exploit
            account_result = await self.test_account_exploit(account)
            results.append(account_result)
            
            # Тестируем Token exploit
            token_result = await self.test_token_exploit(account)
            results.append(token_result)
            
            print(f"[PROGRESS] Аккаунт {i} завершен")
        
        return results
    
    def generate_report(self, results: List[Dict[str, Any]]) -> str:
        """Генерирует отчет о тестировании"""
        timestamp = int(datetime.now().timestamp())
        report_file = f"created_accounts_test_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "test_type": "created_accounts_testing",
            "wallet_address": str(self.attacker_keypair.pubkey()),
            "target_accounts": self.test_accounts,
            "total_tests": len(results),
            "successful_tests": len([r for r in results if r.get("success")]),
            "failed_tests": len([r for r in results if not r.get("success")]),
            "results": results
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        return report_file

async def main():
    """Главная функция"""
    try:
        tester = CreatedAccountTester()
        
        # Запускаем тесты
        results = await tester.test_all_exploits()
        
        # Генерируем отчет
        report_file = tester.generate_report(results)
        
        # Показываем итоги
        successful = len([r for r in results if r.get("success")])
        total = len(results)
        
        print(f"\n[COMPLETE] === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
        print(f"[RESULTS] Успешных тестов: {successful}/{total}")
        print(f"[REPORT] Отчет сохранен: {report_file}")
        
        # Показываем детали
        for result in results:
            status = "УСПЕХ" if result.get("success") else "ПРОВАЛ"
            print(f"[{status}] {result['exploit']} на {result['target'][:20]}...")
        
    except Exception as e:
        print(f"[FATAL] Критическая ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
