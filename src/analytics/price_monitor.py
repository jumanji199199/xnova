"""
Модуль для мониторинга цен токенов
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from decimal import Decimal

import httpx
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey

from ..utils.config import get_solana_config, get_analytics_config
from ..utils.logger import get_logger, LogOperation

@dataclass
class PriceData:
    """Данные о цене токена"""
    token_address: str
    price_usd: Decimal
    price_sol: Decimal
    volume_24h: Decimal
    market_cap: Optional[Decimal]
    liquidity: Optional[Decimal]
    timestamp: datetime
    source: str

@dataclass
class PriceAlert:
    """Алерт о изменении цены"""
    token_address: str
    token_symbol: str
    old_price: Decimal
    new_price: Decimal
    change_percent: Decimal
    timestamp: datetime
    alert_type: str  # 'pump', 'dump', 'milestone'

class PriceMonitor:
    """Класс для мониторинга цен токенов"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.solana_config = get_solana_config()
        self.analytics_config = get_analytics_config()
        
        # Инициализация клиента Solana
        self.client = AsyncClient(endpoint=self.solana_config.rpc_url)
        
        # Хранилище данных о ценах
        self.price_history: Dict[str, List[PriceData]] = {}
        self.current_prices: Dict[str, PriceData] = {}
        self.monitored_tokens: List[str] = []
        
        # API endpoints
        self.jupiter_api = "https://quote-api.jup.ag/v6"
        self.coingecko_api = "https://api.coingecko.com/api/v3"
        
        # Настройки алертов
        self.price_change_threshold = 0.1  # 10% изменение цены
        self.volume_spike_threshold = 2.0  # 2x увеличение объема
        
    def add_token_to_monitor(self, token_address: str, token_symbol: str = ""):
        """Добавляет токен в список мониторинга"""
        if token_address not in self.monitored_tokens:
            self.monitored_tokens.append(token_address)
            self.price_history[token_address] = []
            self.logger.info(f"Токен добавлен в мониторинг: {token_address} ({token_symbol})")
    
    def remove_token_from_monitor(self, token_address: str):
        """Удаляет токен из списка мониторинга"""
        if token_address in self.monitored_tokens:
            self.monitored_tokens.remove(token_address)
            if token_address in self.price_history:
                del self.price_history[token_address]
            if token_address in self.current_prices:
                del self.current_prices[token_address]
            self.logger.info(f"Токен удален из мониторинга: {token_address}")
    
    async def get_token_price_jupiter(self, token_address: str) -> Optional[PriceData]:
        """Получает цену токена через Jupiter API"""
        try:
            # SOL mint address
            sol_mint = "So11111111111111111111111111111111111111112"
            
            async with httpx.AsyncClient() as client:
                # Получаем курс токена к SOL
                response = await client.get(
                    f"{self.jupiter_api}/quote",
                    params={
                        "inputMint": token_address,
                        "outputMint": sol_mint,
                        "amount": 1000000000,  # 1 токен с 9 decimals
                        "slippageBps": 50
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "outAmount" in data:
                        # Рассчитываем цену в SOL
                        price_sol = Decimal(data["outAmount"]) / Decimal(10**9)
                        
                        # Получаем цену SOL в USD
                        sol_price_usd = await self._get_sol_price_usd()
                        price_usd = price_sol * sol_price_usd if sol_price_usd else Decimal(0)
                        
                        return PriceData(
                            token_address=token_address,
                            price_usd=price_usd,
                            price_sol=price_sol,
                            volume_24h=Decimal(0),  # Jupiter не предоставляет объем
                            market_cap=None,
                            liquidity=None,
                            timestamp=datetime.now(),
                            source="Jupiter"
                        )
                
        except Exception as e:
            self.logger.error(f"Ошибка получения цены через Jupiter: {e}")
        
        return None
    
    async def _get_sol_price_usd(self) -> Optional[Decimal]:
        """Получает цену SOL в USD"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.coingecko_api}/simple/price",
                    params={
                        "ids": "solana",
                        "vs_currencies": "usd"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "solana" in data and "usd" in data["solana"]:
                        return Decimal(str(data["solana"]["usd"]))
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения цены SOL: {e}")
        
        return None
    
    async def get_token_price_dexscreener(self, token_address: str) -> Optional[PriceData]:
        """Получает цену токена через DexScreener API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "pairs" in data and data["pairs"]:
                        # Берем первую пару (обычно с наибольшей ликвидностью)
                        pair = data["pairs"][0]
                        
                        price_usd = Decimal(str(pair.get("priceUsd", "0")))
                        volume_24h = Decimal(str(pair.get("volume", {}).get("h24", "0")))
                        liquidity = Decimal(str(pair.get("liquidity", {}).get("usd", "0")))
                        
                        # Рассчитываем цену в SOL
                        sol_price_usd = await self._get_sol_price_usd()
                        price_sol = price_usd / sol_price_usd if sol_price_usd and sol_price_usd > 0 else Decimal(0)
                        
                        return PriceData(
                            token_address=token_address,
                            price_usd=price_usd,
                            price_sol=price_sol,
                            volume_24h=volume_24h,
                            market_cap=None,
                            liquidity=liquidity,
                            timestamp=datetime.now(),
                            source="DexScreener"
                        )
                        
        except Exception as e:
            self.logger.error(f"Ошибка получения цены через DexScreener: {e}")
        
        return None
    
    async def update_token_price(self, token_address: str) -> Optional[PriceData]:
        """Обновляет цену токена из всех доступных источников"""
        try:
            # Пробуем получить цену из разных источников
            price_data = None
            
            # Сначала пробуем DexScreener (более полная информация)
            price_data = await self.get_token_price_dexscreener(token_address)
            
            # Если не получилось, пробуем Jupiter
            if not price_data:
                price_data = await self.get_token_price_jupiter(token_address)
            
            if price_data:
                # Сохраняем в историю
                if token_address not in self.price_history:
                    self.price_history[token_address] = []
                
                self.price_history[token_address].append(price_data)
                
                # Ограничиваем размер истории (последние 1000 записей)
                if len(self.price_history[token_address]) > 1000:
                    self.price_history[token_address] = self.price_history[token_address][-1000:]
                
                # Обновляем текущую цену
                old_price = self.current_prices.get(token_address)
                self.current_prices[token_address] = price_data
                
                # Проверяем на алерты
                if old_price:
                    await self._check_price_alerts(token_address, old_price, price_data)
                
                return price_data
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления цены токена {token_address}: {e}")
        
        return None
    
    async def _check_price_alerts(self, token_address: str, old_price: PriceData, new_price: PriceData):
        """Проверяет условия для алертов о изменении цены"""
        try:
            if old_price.price_usd == 0:
                return
            
            # Рассчитываем изменение цены в процентах
            price_change = (new_price.price_usd - old_price.price_usd) / old_price.price_usd
            
            alert_type = None
            
            # Проверяем на значительное изменение цены
            if abs(price_change) >= self.price_change_threshold:
                if price_change > 0:
                    alert_type = "pump"
                else:
                    alert_type = "dump"
            
            # Проверяем на всплеск объема
            if (old_price.volume_24h > 0 and 
                new_price.volume_24h / old_price.volume_24h >= self.volume_spike_threshold):
                alert_type = "volume_spike"
            
            if alert_type:
                alert = PriceAlert(
                    token_address=token_address,
                    token_symbol="",  # Можно добавить получение символа
                    old_price=old_price.price_usd,
                    new_price=new_price.price_usd,
                    change_percent=price_change * 100,
                    timestamp=datetime.now(),
                    alert_type=alert_type
                )
                
                await self._send_price_alert(alert)
                
        except Exception as e:
            self.logger.error(f"Ошибка проверки алертов: {e}")
    
    async def _send_price_alert(self, alert: PriceAlert):
        """Отправляет алерт о изменении цены"""
        try:
            alert_message = self._format_price_alert(alert)
            self.logger.warning(f"PRICE ALERT: {alert_message}")
            
            # Здесь можно добавить отправку уведомлений:
            # - В Telegram
            # - В Discord
            # - По email
            # - В базу данных
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки алерта: {e}")
    
    def _format_price_alert(self, alert: PriceAlert) -> str:
        """Форматирует сообщение алерта"""
        if alert.alert_type == "pump":
            emoji = "🚀"
            action = "PUMP"
        elif alert.alert_type == "dump":
            emoji = "📉"
            action = "DUMP"
        else:
            emoji = "📊"
            action = "VOLUME SPIKE"
        
        return (
            f"{emoji} {action} ALERT!\n"
            f"Token: {alert.token_address[:8]}...{alert.token_address[-8:]}\n"
            f"Price: ${alert.old_price:.6f} → ${alert.new_price:.6f}\n"
            f"Change: {alert.change_percent:+.2f}%\n"
            f"Time: {alert.timestamp.strftime('%H:%M:%S')}"
        )
    
    async def get_price_history(self, token_address: str, hours: int = 24) -> List[PriceData]:
        """Получает историю цен токена за указанный период"""
        if token_address not in self.price_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            price for price in self.price_history[token_address]
            if price.timestamp >= cutoff_time
        ]
    
    async def calculate_price_statistics(self, token_address: str, hours: int = 24) -> Dict[str, Any]:
        """Рассчитывает статистику цен токена"""
        history = await self.get_price_history(token_address, hours)
        
        if not history:
            return {}
        
        prices = [float(price.price_usd) for price in history]
        volumes = [float(price.volume_24h) for price in history]
        
        current_price = prices[-1] if prices else 0
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        avg_price = sum(prices) / len(prices) if prices else 0
        
        # Изменение цены
        price_change = 0
        if len(prices) >= 2:
            price_change = ((current_price - prices[0]) / prices[0]) * 100
        
        # Волатильность (стандартное отклонение)
        volatility = 0
        if len(prices) > 1:
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            volatility = variance ** 0.5
        
        return {
            "token_address": token_address,
            "period_hours": hours,
            "current_price": current_price,
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": avg_price,
            "price_change_percent": price_change,
            "volatility": volatility,
            "total_volume": sum(volumes),
            "avg_volume": sum(volumes) / len(volumes) if volumes else 0,
            "data_points": len(history),
            "last_update": history[-1].timestamp.isoformat() if history else None
        }
    
    async def start_monitoring(self):
        """Запускает мониторинг цен"""
        with LogOperation("Запуск мониторинга цен"):
            self.logger.info(f"Начинаем мониторинг {len(self.monitored_tokens)} токенов")
            
            while True:
                try:
                    # Обновляем цены всех токенов
                    tasks = []
                    for token_address in self.monitored_tokens:
                        task = self.update_token_price(token_address)
                        tasks.append(task)
                    
                    if tasks:
                        results = await asyncio.gather(*tasks, return_exceptions=True)
                        
                        successful_updates = sum(1 for r in results if not isinstance(r, Exception))
                        self.logger.info(f"Обновлено цен: {successful_updates}/{len(tasks)}")
                    
                    # Ждем до следующего обновления
                    await asyncio.sleep(self.analytics_config.price_check_interval)
                    
                except Exception as e:
                    self.logger.error(f"Ошибка в цикле мониторинга: {e}")
                    await asyncio.sleep(60)  # Ждем минуту перед повтором
    
    async def export_price_data(self, token_address: str, filename: str):
        """Экспортирует данные о ценах в JSON файл"""
        try:
            if token_address not in self.price_history:
                self.logger.warning(f"Нет данных для токена: {token_address}")
                return
            
            # Подготавливаем данные для экспорта
            export_data = {
                "token_address": token_address,
                "export_timestamp": datetime.now().isoformat(),
                "total_records": len(self.price_history[token_address]),
                "price_history": [
                    asdict(price_data) for price_data in self.price_history[token_address]
                ]
            }
            
            # Конвертируем Decimal в строки для JSON
            def decimal_converter(obj):
                if isinstance(obj, Decimal):
                    return str(obj)
                elif isinstance(obj, datetime):
                    return obj.isoformat()
                return obj
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=decimal_converter, ensure_ascii=False)
            
            self.logger.info(f"Данные экспортированы в файл: {filename}")
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта данных: {e}")
    
    async def close(self):
        """Закрывает соединения"""
        await self.client.close()
