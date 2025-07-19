"""
Главный файл Solana Token Deployer & Manager
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.token_creator import TokenCreator, TokenMetadata
from src.dex.raydium_integration import RaydiumIntegration
from src.marketing.social_media import SocialMediaManager, TokenPromotion
from src.utils.config import get_config
from src.utils.logger import setup_logging, get_logger

# Инициализация
app = typer.Typer(help="Solana Token Deployer & Manager")
console = Console()
logger = setup_logging()

class SolanaTokenManager:
    """Основной класс для управления токенами Solana"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_config()
        
        # Инициализация компонентов
        self.token_creator = None
        self.raydium = None
        self.social_media = None
        
    async def initialize(self):
        """Инициализирует все компоненты"""
        try:
            console.print("[yellow]Инициализация компонентов...[/yellow]")
            
            # Инициализация создателя токенов
            self.token_creator = TokenCreator()
            console.print("✅ TokenCreator инициализирован")
            
            # Инициализация Raydium
            self.raydium = RaydiumIntegration(self.token_creator.payer)
            console.print("✅ Raydium интеграция инициализирована")
            
            # Инициализация социальных сетей
            self.social_media = SocialMediaManager()
            console.print("✅ Менеджер социальных сетей инициализирован")
            
            console.print("[green]Все компоненты инициализированы успешно![/green]")
            
        except Exception as e:
            console.print(f"[red]Ошибка инициализации: {e}[/red]")
            raise
    
    async def create_and_promote_token(
        self,
        name: str,
        symbol: str,
        description: str,
        supply: int,
        website: Optional[str] = None,
        image_url: Optional[str] = None
    ):
        """Создает токен и автоматически его продвигает"""
        try:
            console.print(Panel(f"🚀 Создание и продвижение токена {symbol}", style="bold blue"))
            
            # 1. Создание токена
            console.print("[yellow]Шаг 1: Создание токена...[/yellow]")
            
            metadata = TokenMetadata(
                name=name,
                symbol=symbol,
                description=description,
                image_url=image_url or "https://via.placeholder.com/200x200",
                website=website
            )
            
            token_info = await self.token_creator.create_token(
                metadata=metadata,
                initial_supply=supply
            )
            
            if not token_info:
                raise Exception("Не удалось создать токен")
            
            console.print(f"✅ Токен создан: {token_info.mint_address}")
            
            # 2. Создание пула ликвидности
            console.print("[yellow]Шаг 2: Создание пула ликвидности...[/yellow]")
            
            # SOL как котируемый токен
            sol_mint = "So11111111111111111111111111111111111111112"
            
            # Рассчитываем количества для ликвидности
            sol_amount = int(self.config.liquidity.initial_sol_amount * 10**9)  # SOL в lamports
            token_amount = int(supply * 0.1 * 10**metadata.decimals)  # 10% от общего количества
            
            pool_id = await self.raydium.create_pool(
                base_mint=token_info.mint_address,
                quote_mint=sol_mint,
                base_amount=token_amount,
                quote_amount=sol_amount
            )
            
            if pool_id:
                console.print(f"✅ Пул ликвидности создан: {pool_id}")
            else:
                console.print("[yellow]⚠️ Не удалось создать пул ликвидности (будет создан позже)[/yellow]")
            
            # 3. Продвижение в социальных сетях
            console.print("[yellow]Шаг 3: Продвижение в социальных сетях...[/yellow]")
            
            promotion = TokenPromotion(
                token_name=name,
                token_symbol=symbol,
                token_address=token_info.mint_address,
                website=website,
                description=description,
                key_features=[
                    "Быстрые транзакции на Solana",
                    "Низкие комиссии",
                    "Децентрализованное управление",
                    "Инновационная токеномика"
                ]
            )
            
            promotion_results = await self.social_media.promote_token(promotion)
            
            # Отображаем результаты продвижения
            for platform, success in promotion_results.items():
                status = "✅" if success else "❌"
                console.print(f"{status} {platform.capitalize()}: {'Успешно' if success else 'Ошибка'}")
            
            # 4. Планирование регулярных постов
            console.print("[yellow]Шаг 4: Планирование регулярных постов...[/yellow]")
            
            await self.social_media.schedule_regular_posts(promotion, days=7)
            console.print("✅ Регулярные посты запланированы на 7 дней")
            
            # 5. Отображение итоговой информации
            self._display_token_summary(token_info, metadata, pool_id, promotion_results)
            
        except Exception as e:
            console.print(f"[red]Ошибка при создании и продвижении токена: {e}[/red]")
            self.logger.error(f"Ошибка при создании и продвижении токена: {e}")
    
    def _display_token_summary(self, token_info, metadata, pool_id, promotion_results):
        """Отображает итоговую информацию о токене"""
        table = Table(title="📊 Итоговая информация о токене", style="bold")
        
        table.add_column("Параметр", style="cyan")
        table.add_column("Значение", style="green")
        
        table.add_row("Название", metadata.name)
        table.add_row("Символ", metadata.symbol)
        table.add_row("Адрес контракта", token_info.mint_address)
        table.add_row("Общее количество", f"{token_info.total_supply:,}")
        table.add_row("Десятичные знаки", str(token_info.decimals))
        table.add_row("Пул ликвидности", pool_id or "Не создан")
        
        # Результаты продвижения
        promotion_status = []
        for platform, success in promotion_results.items():
            status = "✅" if success else "❌"
            promotion_status.append(f"{status} {platform.capitalize()}")
        
        table.add_row("Продвижение", "\n".join(promotion_status))
        
        console.print(table)
        
        # Дополнительная информация
        console.print(Panel(
            f"🎉 Токен {metadata.symbol} успешно создан и запущен!\n\n"
            f"📍 Адрес для добавления в кошелек: {token_info.mint_address}\n"
            f"🌐 Сайт: {metadata.website or 'Не указан'}\n"
            f"📱 Следите за обновлениями в социальных сетях!",
            title="Поздравляем!",
            style="bold green"
        ))
    
    async def close(self):
        """Закрывает все соединения"""
        if self.token_creator:
            await self.token_creator.close()
        if self.raydium:
            await self.raydium.close()
        if self.social_media:
            await self.social_media.close()

# Глобальный экземпляр менеджера
manager = SolanaTokenManager()

@app.command()
def create_token(
    name: str = typer.Option(..., help="Название токена"),
    symbol: str = typer.Option(..., help="Символ токена (например, MYTOKEN)"),
    description: str = typer.Option(..., help="Описание токена"),
    supply: int = typer.Option(1000000000, help="Общее количество токенов"),
    website: Optional[str] = typer.Option(None, help="Веб-сайт проекта"),
    image_url: Optional[str] = typer.Option(None, help="URL изображения токена"),
    auto_promote: bool = typer.Option(True, help="Автоматически продвигать токен")
):
    """Создает новый SPL токен"""
    
    async def _create():
        try:
            await manager.initialize()
            
            if auto_promote:
                await manager.create_and_promote_token(
                    name=name,
                    symbol=symbol,
                    description=description,
                    supply=supply,
                    website=website,
                    image_url=image_url
                )
            else:
                # Только создание токена без продвижения
                metadata = TokenMetadata(
                    name=name,
                    symbol=symbol,
                    description=description,
                    image_url=image_url or "https://via.placeholder.com/200x200",
                    website=website
                )
                
                token_info = await manager.token_creator.create_token(
                    metadata=metadata,
                    initial_supply=supply
                )
                
                if token_info:
                    console.print(f"✅ Токен создан: {token_info.mint_address}")
                else:
                    console.print("❌ Ошибка при создании токена")
            
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
        finally:
            await manager.close()
    
    asyncio.run(_create())

@app.command()
def interactive():
    """Интерактивный режим создания токена"""
    
    console.print(Panel("🚀 Добро пожаловать в Solana Token Deployer!", style="bold blue"))
    
    # Сбор информации о токене
    name = Prompt.ask("📝 Введите название токена")
    symbol = Prompt.ask("🏷️ Введите символ токена (например, MYTOKEN)").upper()
    description = Prompt.ask("📄 Введите описание токена")
    
    supply_input = Prompt.ask("💰 Введите общее количество токенов", default="1000000000")
    try:
        supply = int(supply_input)
    except ValueError:
        supply = 1000000000
    
    website = Prompt.ask("🌐 Введите веб-сайт проекта (необязательно)", default="")
    website = website if website else None
    
    image_url = Prompt.ask("🖼️ Введите URL изображения токена (необязательно)", default="")
    image_url = image_url if image_url else None
    
    auto_promote = Confirm.ask("📢 Автоматически продвигать токен в социальных сетях?", default=True)
    
    # Подтверждение
    console.print("\n📋 Проверьте введенную информацию:")
    console.print(f"Название: {name}")
    console.print(f"Символ: {symbol}")
    console.print(f"Описание: {description}")
    console.print(f"Количество: {supply:,}")
    console.print(f"Сайт: {website or 'Не указан'}")
    console.print(f"Изображение: {image_url or 'По умолчанию'}")
    console.print(f"Автопродвижение: {'Да' if auto_promote else 'Нет'}")
    
    if not Confirm.ask("\n✅ Создать токен с указанными параметрами?"):
        console.print("❌ Создание токена отменено")
        return
    
    # Создание токена
    async def _create():
        try:
            await manager.initialize()
            
            if auto_promote:
                await manager.create_and_promote_token(
                    name=name,
                    symbol=symbol,
                    description=description,
                    supply=supply,
                    website=website,
                    image_url=image_url
                )
            else:
                metadata = TokenMetadata(
                    name=name,
                    symbol=symbol,
                    description=description,
                    image_url=image_url or "https://via.placeholder.com/200x200",
                    website=website
                )
                
                token_info = await manager.token_creator.create_token(
                    metadata=metadata,
                    initial_supply=supply
                )
                
                if token_info:
                    console.print(f"✅ Токен создан: {token_info.mint_address}")
                else:
                    console.print("❌ Ошибка при создании токена")
            
        except Exception as e:
            console.print(f"[red]Ошибка: {e}[/red]")
        finally:
            await manager.close()
    
    asyncio.run(_create())

@app.command()
def config():
    """Показывает текущую конфигурацию"""
    config_data = get_config()
    
    table = Table(title="⚙️ Текущая конфигурация", style="bold")
    table.add_column("Параметр", style="cyan")
    table.add_column("Значение", style="green")
    
    table.add_row("Сеть Solana", config_data.solana.network)
    table.add_row("RPC URL", config_data.solana.rpc_url)
    table.add_row("Десятичные знаки по умолчанию", str(config_data.token.default_decimals))
    table.add_row("Количество токенов по умолчанию", f"{config_data.token.default_supply:,}")
    table.add_row("Начальная ликвидность (SOL)", str(config_data.liquidity.initial_sol_amount))
    
    console.print(table)

if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Программа прервана пользователем[/yellow]")
    except Exception as e:
        console.print(f"[red]Критическая ошибка: {e}[/red]")
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Очистка ресурсов
        try:
            asyncio.run(manager.close())
        except:
            pass
