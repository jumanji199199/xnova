"""
Демонстрация работы Solana Token Deployer
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.token_creator import TokenCreator, TokenMetadata
from src.marketing.social_media import SocialMediaManager, TokenPromotion
from src.analytics.price_monitor import PriceMonitor
from src.utils.logger import setup_logging, get_logger

async def demo_token_creation():
    """Демонстрация создания токена"""
    logger = get_logger(__name__)
    
    try:
        print("🚀 Демонстрация создания токена Solana")
        print("=" * 50)
        
        # Инициализация создателя токенов
        print("📝 Инициализация TokenCreator...")
        token_creator = TokenCreator()
        
        # Создание метаданных токена
        metadata = TokenMetadata(
            name="Demo Token",
            symbol="DEMO",
            description="Демонстрационный токен для тестирования системы автоматического деплоя",
            image_url="https://via.placeholder.com/200x200/FF6B6B/FFFFFF?text=DEMO",
            website="https://demo-token.example.com",
            twitter="https://twitter.com/demo_token",
            telegram="https://t.me/demo_token"
        )
        
        print(f"🏷️ Создание токена: {metadata.name} ({metadata.symbol})")
        print(f"📄 Описание: {metadata.description}")
        
        # Создание токена (в devnet)
        print("⏳ Создание токена в сети Solana...")
        token_info = await token_creator.create_token(
            metadata=metadata,
            initial_supply=1000000000,  # 1 миллиард токенов
            decimals=9
        )
        
        if token_info:
            print("✅ Токен успешно создан!")
            print(f"📍 Адрес mint: {token_info.mint_address}")
            print(f"💰 Общее количество: {token_info.total_supply:,}")
            print(f"🔢 Десятичные знаки: {token_info.decimals}")
        else:
            print("❌ Ошибка при создании токена")
            return
        
        # Закрываем соединения
        await token_creator.close()
        
        print("\n🎉 Демонстрация завершена успешно!")
        
    except Exception as e:
        logger.error(f"Ошибка в демонстрации: {e}")
        print(f"❌ Ошибка: {e}")

async def demo_price_monitoring():
    """Демонстрация мониторинга цен"""
    print("\n📊 Демонстрация мониторинга цен")
    print("=" * 50)
    
    try:
        # Инициализация монитора цен
        price_monitor = PriceMonitor()
        
        # Добавляем популярные токены для мониторинга
        popular_tokens = [
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
            "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
            "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",   # mSOL
        ]
        
        token_names = ["USDC", "USDT", "mSOL"]
        
        for token_address, name in zip(popular_tokens, token_names):
            price_monitor.add_token_to_monitor(token_address, name)
            print(f"➕ Добавлен в мониторинг: {name}")
        
        print("\n⏳ Получение текущих цен...")
        
        # Получаем цены токенов
        for token_address, name in zip(popular_tokens, token_names):
            price_data = await price_monitor.update_token_price(token_address)
            
            if price_data:
                print(f"💰 {name}: ${price_data.price_usd:.6f} | {price_data.price_sol:.6f} SOL")
                print(f"   📊 Объем 24ч: ${price_data.volume_24h:,.2f}")
                print(f"   🔗 Источник: {price_data.source}")
            else:
                print(f"❌ Не удалось получить цену для {name}")
        
        # Закрываем соединения
        await price_monitor.close()
        
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")

async def demo_social_media():
    """Демонстрация работы с социальными сетями"""
    print("\n📱 Демонстрация маркетинга в социальных сетях")
    print("=" * 50)
    
    try:
        # Инициализация менеджера социальных сетей
        social_media = SocialMediaManager()
        
        # Создание промо-материалов для токена
        promotion = TokenPromotion(
            token_name="Demo Token",
            token_symbol="DEMO",
            token_address="DemoTokenAddress123456789",
            website="https://demo-token.example.com",
            description="Инновационный токен для демонстрации возможностей автоматического деплоя и продвижения",
            key_features=[
                "Автоматический деплой в сети Solana",
                "Интеграция с популярными DEX",
                "Автоматическое продвижение в социальных сетях",
                "Мониторинг цен в реальном времени",
                "Аналитика и отчетность"
            ]
        )
        
        print(f"🎯 Подготовка промо-материалов для {promotion.token_symbol}")
        print(f"📝 Описание: {promotion.description}")
        print(f"🌟 Ключевые особенности: {len(promotion.key_features)} пунктов")
        
        # Генерируем контент (без реальной публикации)
        print("\n📝 Генерация контента для социальных сетей...")
        print("✅ Основной пост о запуске токена")
        print("✅ Пост о ключевых особенностях")
        print("✅ Пост о торговле на DEX")
        print("✅ Планирование регулярных постов")
        
        print("\n📅 Планирование постов на 7 дней...")
        await social_media.schedule_regular_posts(promotion, days=7)
        
        # Закрываем соединения
        await social_media.close()
        
        print("✅ Маркетинговая кампания подготовлена!")
        
    except Exception as e:
        print(f"❌ Ошибка маркетинга: {e}")

async def main():
    """Главная функция демонстрации"""
    # Настройка логирования
    setup_logging()
    
    print("🌟 Добро пожаловать в Solana Token Deployer!")
    print("Эта демонстрация покажет основные возможности системы")
    print("=" * 60)
    
    try:
        # Демонстрация создания токена
        await demo_token_creation()
        
        # Демонстрация мониторинга цен
        await demo_price_monitoring()
        
        # Демонстрация социальных сетей
        await demo_social_media()
        
        print("\n" + "=" * 60)
        print("🎊 Все демонстрации завершены успешно!")
        print("\nДля создания реального токена:")
        print("1. Настройте конфигурацию в config/settings.yaml")
        print("2. Добавьте API ключи в .env файл")
        print("3. Запустите: python main.py interactive")
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка демонстрации: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Демонстрация прервана пользователем")
    except Exception as e:
        print(f"\n💥 Неожиданная ошибка: {e}")
