"""
Комплексный тестовый сценарий для фреймворка эксплойтов Solana.

Этот скрипт выполняет следующие шаги:
1. Инициализирует окружение: загружает переменные, настраивает RPC-клиент.
2. Создает уязвимые активы с помощью VulnerableAssetFactory.
3. Инициализирует ExploitManager со всеми доступными модулями эксплойтов.
4. Запускает сканирование и эксплойты против созданных уязвимых активов.
5. Собирает, анализирует и выводит результаты в консоль и в отчет.
"""

import asyncio
import logging
from datetime import datetime
import json


from solders.keypair import Keypair
from solders.pubkey import Pubkey

from dotenv import load_dotenv
import os

def load_env_variables():
    """Загружает переменные окружения из файла .env в корне проекта."""
    # Путь к файлу .env находится на один уровень выше директории src
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError(f"Файл .env не найден по пути: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
    # Возвращаем переменные как словарь для совместимости
    return {
        'solana_privkey': os.getenv('SOLANA_PRIVKEY'),
        'solana_rpc_url': os.getenv('SOLANA_RPC_URL'),
        'solana_target_address': os.getenv('SOLANA_TARGET_ADDRESS')
    }

def get_rpc_endpoints():
    """Возвращает список RPC эндпоинтов."""
    # В этой реализации мы просто берем основной RPC из .env
    # В будущем можно добавить логику для резервных эндпоинтов
    rpc_url = os.getenv('SOLANA_RPC_URL')
    if not rpc_url:
        raise ValueError("Переменная SOLANA_RPC_URL не найдена в .env")
    return [rpc_url]

from .vulnerability_creation.asset_factory import VulnerableAssetFactory
from src.exploits.exploit_manager import ExploitManager
from src.exploits.base_exploit import ExploitStatus

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """Основная функция для запуска тестового сценария."""
    logging.info("🚀 Запуск комплексного тестового сценария для Solana эксплойтов...")

    try:
        # 1. Инициализация окружения
        logging.info("🔧 1. Инициализация окружения...")
        env_vars = load_env_variables()
        rpc_endpoints = get_rpc_endpoints()
        attacker_keypair = Keypair.from_bytes(bytes.fromhex(env_vars['solana_privkey']))
        
        logging.info(f"Атакующий кошелек: {attacker_keypair.pubkey()}")

        # 2. Создание уязвимых активов
        logging.info("🏭 2. Создание уязвимых активов с помощью AssetFactory...")
        asset_factory = VulnerableAssetFactory(rpc_endpoints, attacker_keypair)
        
        vulnerable_assets = await asset_factory.create_all_vulnerable_assets()
        
        if not vulnerable_assets:
            logging.error("❌ Не удалось создать уязвимые активы. Тестирование прервано.")
            return

        asset_count = sum(len(v) for v in vulnerable_assets.values())
        logging.info(f"✅ Создано {asset_count} уязвимых активов.")
        for asset_type, assets_list in vulnerable_assets.items():
            logging.info(f"\nКатегория: {asset_type} ({len(assets_list)} шт.)")
            for asset in assets_list:
                logging.info(f"  - Тип: {asset.vulnerability_type}, Адрес: {asset.address}")

        # 3. Инициализация ExploitManager
        logging.info("🤖 3. Инициализация ExploitManager...")
        exploit_manager = ExploitManager(rpc_endpoints, attacker_keypair)

        # 4. Запуск сканирования и эксплойтов
        logging.info("🎯 4. Запуск сканирования и атак на созданные активы...")
        target_pubkeys = [asset.address for asset_list in vulnerable_assets.values() for asset in asset_list]
        
        # Запуск кампании по эксплойтам
        campaign_results = await exploit_manager.run_exploit_campaign(target_pubkeys)

        # 5. Анализ и отчет
        logging.info("📊 5. Анализ результатов и формирование отчета...")
        total_exploits = len(campaign_results)
        successful_exploits = [
        res for results_list in campaign_results.values() 
        for res in results_list if res.status == ExploitStatus.SUCCESS
    ]
        
        logging.info("--- ОТЧЕТ ПО ТЕСТИРОВАНИЮ ---")
        logging.info(f"Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logging.info(f"Всего выполнено эксплойтов: {total_exploits}")
        logging.info(f"Успешных эксплойтов: {len(successful_exploits)}")
        logging.info(f"Неуспешных эксплойтов: {total_exploits - len(successful_exploits)}")
        
        total_extracted_value = sum(res.extracted_value for res in successful_exploits if res.extracted_value)
        logging.info(f"Суммарно извлечено: {total_extracted_value:.8f} SOL")
        
        # Сохранение отчета в файл
        report_filename = f"exploit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = [
            {
                "exploit": res.exploit_type.value,
                "target": str(res.target_account),
                "status": res.status.value,
                "error": res.error_message,
            }
            for results_list in campaign_results.values()
            for res in results_list
            if hasattr(res, "exploit_type") and hasattr(res, "target_account") and hasattr(res, "status")
        ]
        
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=4)
            
        logging.info(f"✅ Отчет сохранен в файл: {report_filename}")

    except Exception as e:
        logging.critical(f"❌ Критическая ошибка в тестовом сценарии: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
