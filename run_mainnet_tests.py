#!/usr/bin/env python3
"""
ЗАПУСК ТЕСТОВ НА MAINNET
Загрузка настроек из .env и запуск всех тестов эксплойтов и токенов
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[+] Загружены настройки из {env_path}")
else:
    print(f"[-] Файл .env не найден: {env_path}")

# Импорт наших модулей
from mainnet_exploit_tester import MainnetExploitTester, MainnetConfig
from custom_token_deployer import CustomTokenDeployer, TokenConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_exploit_tests():
    """Запуск тестов эксплойтов"""
    print("\n" + "="*80)
    print("[!] ЗАПУСК ТЕСТОВ ЭКСПЛОЙТОВ НА MAINNET")
    print("="*80)
    
    try:
        # Загрузка конфигурации
        config = MainnetConfig.from_env()
        
        # Проверка настроек
        if not config.private_key:
            print("[-] SOLANA_PRIVKEY не найден в переменных окружения!")
            return False
        
        if not config.target_address:
            print("[!] SOLANA_TARGET_ADDRESS не указан, будут использованы системные аккаунты")
        
        print(f"[+] Network: {config.network}")
        print(f"[+] RPC URL: {config.rpc_url}")
        print(f"[+] Target: {config.target_address}")
        
        # Инициализация тестера
        tester = MainnetExploitTester(config)
        
        # Запуск тестов
        results = await tester.run_comprehensive_test_suite()
        
        # Сохранение отчета
        await tester.save_test_report(results)
        
        print("\n[+] Тесты эксплойтов завершены успешно!")
        print(f"[+] Отчет сохранен в mainnet_test_report.json")
        
        # Показываем краткую статистику
        stats = results.get("final_stats", {})
        print(f"[=] Статистика: {stats.get('passed_tests', 0)}/{stats.get('total_tests', 0)} тестов успешно")
        print(f"[=] Процент успеха: {stats.get('success_rate', 0):.1f}%")
        
        await tester.close()
        return True
        
    except Exception as e:
        logger.error(f"[-] Ошибка в тестах эксплойтов: {e}")
        return False

async def run_token_tests():
    """Запуск тестов токена"""
    print("\n" + "="*80)
    print("[!] ЗАПУСК ТЕСТОВ КАСТОМНОГО ТОКЕНА")
    print("="*80)
    
    try:
        # Загрузка настроек
        rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.mainnet.solana.com')
        private_key = os.getenv('SOLANA_PRIVKEY', '')
        
        if not private_key:
            print("[-] SOLANA_PRIVKEY не найден в переменных окружения!")
            return False
        
        print(f"[+] RPC URL: {rpc_url}")
        
        # Конфигурация токена
        token_config = TokenConfig(
            name="ExploitFrameworkToken",
            symbol="EFT",
            decimals=9,
            initial_supply=10000000,  # 10M токенов
            description="Токен для тестирования Solana Exploit Framework",
            freeze_authority_enabled=True,
            mint_authority_enabled=True,
            burn_enabled=True
        )
        
        print(f"[+] Создаем токен: {token_config.name} ({token_config.symbol})")
        print(f"[+] Начальный supply: {token_config.initial_supply:,} токенов")
        
        # Инициализация деплойера
        deployer = CustomTokenDeployer(rpc_url, private_key)
        
        # Запуск тестов
        results = await deployer.run_comprehensive_token_tests(token_config)
        
        # Сохранение отчета
        await deployer.save_token_report(results)
        
        print("\n[+] Тесты токена завершены успешно!")
        print(f"[+] Отчет сохранен в custom_token_report.json")
        
        # Показываем информацию о токене
        if deployer.token_address:
            print(f"[+] Адрес токена: {deployer.token_address}")
        if deployer.token_account:
            print(f"[+] Token аккаунт: {deployer.token_account}")
        
        # Статистика
        stats = results.get("final_stats", {})
        print(f"[=] Статистика: {stats.get('successful_tests', 0)}/{stats.get('total_tests', 0)} тестов успешно")
        print(f"[=] Процент успеха: {stats.get('success_rate', 0):.1f}%")
        
        await deployer.close()
        return True
        
    except Exception as e:
        logger.error(f"[-] Ошибка в тестах токена: {e}")
        return False

async def main():
    """Главная функция"""
    print("[!] SOLANA MAINNET TESTING SUITE")
    print("Комплексное тестирование эксплойтов и токенов")
    print("Основано на анализе 155 изображений PDF 'Pwning Blockchain for Fun and Profit'")
    print()
    
    # Проверка переменных окружения
    required_vars = ['SOLANA_NETWORK', 'SOLANA_RPC_URL', 'SOLANA_PRIVKEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"[-] Отсутствуют переменные окружения: {', '.join(missing_vars)}")
        print("[-] Проверьте файл .env")
        return
    
    print("[+] Все необходимые переменные окружения найдены")
    print(f"[+] Network: {os.getenv('SOLANA_NETWORK')}")
    print(f"[+] RPC URL: {os.getenv('SOLANA_RPC_URL')}")
    print(f"[+] Target: {os.getenv('SOLANA_TARGET_ADDRESS', 'Не указан')}")
    
    # Предупреждение о mainnet
    if os.getenv('SOLANA_NETWORK') == 'mainnet':
        print("\n[!] ВНИМАНИЕ: Работа с MAINNET!")
        print("   Все операции выполняются с реальными средствами.")
        print("   Убедитесь, что понимаете риски.")
        
        response = input("\nПродолжить? (y/N): ").strip().lower()
        if response != 'y':
            print("Отменено пользователем.")
            return
    
    success_count = 0
    total_suites = 2
    
    # 1. Запуск тестов эксплойтов
    if await run_exploit_tests():
        success_count += 1
    
    # 2. Запуск тестов токена
    if await run_token_tests():
        success_count += 1
    
    # Финальная статистика
    print("\n" + "="*80)
    print("[=] ФИНАЛЬНАЯ СТАТИСТИКА ВСЕХ ТЕСТОВ")
    print(f"[+] Успешных наборов тестов: {success_count}/{total_suites}")
    print(f"[%] Общий процент успеха: {(success_count/total_suites*100):.1f}%")
    
    if success_count == total_suites:
        print("[+] Все тесты завершены успешно!")
    else:
        print("[!] Некоторые тесты завершились с ошибками. Проверьте логи.")
    
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
