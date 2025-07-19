"""
Модуль для автоматизации маркетинга в социальных сетях
"""

import asyncio
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import tweepy
import discord
from telegram import Bot
from telegram.error import TelegramError

from ..utils.config import get_marketing_config
from ..utils.logger import get_logger, LogOperation

@dataclass
class SocialPost:
    """Структура поста для социальных сетей"""
    text: str
    image_url: Optional[str] = None
    hashtags: List[str] = None
    scheduled_time: Optional[datetime] = None

@dataclass
class TokenPromotion:
    """Структура для продвижения токена"""
    token_name: str
    token_symbol: str
    token_address: str
    website: Optional[str] = None
    description: str
    key_features: List[str] = None

class TwitterManager:
    """Менеджер для работы с Twitter"""
    
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_token_secret: str):
        self.logger = get_logger(__name__)
        
        try:
            # Инициализация Twitter API v2
            self.client = tweepy.Client(
                bearer_token=None,
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
                wait_on_rate_limit=True
            )
            
            # Проверяем подключение
            self.user = self.client.get_me()
            self.logger.info(f"Twitter подключен: @{self.user.data.username}")
            
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Twitter: {e}")
            self.client = None
    
    async def post_tweet(self, post: SocialPost) -> bool:
        """Публикует твит"""
        if not self.client:
            return False
            
        try:
            # Формируем текст с хештегами
            text = post.text
            if post.hashtags:
                hashtags_str = " ".join([f"#{tag}" for tag in post.hashtags])
                text = f"{text}\n\n{hashtags_str}"
            
            # Ограничиваем длину твита
            if len(text) > 280:
                text = text[:277] + "..."
            
            # Публикуем твит
            response = self.client.create_tweet(text=text)
            
            if response.data:
                self.logger.info(f"Твит опубликован: {response.data['id']}")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка при публикации твита: {e}")
            return False
    
    async def post_thread(self, posts: List[SocialPost]) -> bool:
        """Публикует цепочку твитов"""
        if not self.client or not posts:
            return False
            
        try:
            previous_tweet_id = None
            
            for i, post in enumerate(posts):
                # Формируем текст
                text = post.text
                if post.hashtags and i == len(posts) - 1:  # Хештеги только в последнем твите
                    hashtags_str = " ".join([f"#{tag}" for tag in post.hashtags])
                    text = f"{text}\n\n{hashtags_str}"
                
                # Добавляем номер твита в цепочке
                if len(posts) > 1:
                    text = f"{i+1}/{len(posts)} {text}"
                
                # Ограничиваем длину
                if len(text) > 280:
                    text = text[:277] + "..."
                
                # Публикуем твит
                response = self.client.create_tweet(
                    text=text,
                    in_reply_to_tweet_id=previous_tweet_id
                )
                
                if response.data:
                    previous_tweet_id = response.data['id']
                    self.logger.info(f"Твит {i+1} опубликован: {previous_tweet_id}")
                    
                    # Пауза между твитами
                    if i < len(posts) - 1:
                        await asyncio.sleep(2)
                else:
                    self.logger.error(f"Ошибка при публикации твита {i+1}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при публикации цепочки твитов: {e}")
            return False

class DiscordManager:
    """Менеджер для работы с Discord"""
    
    def __init__(self, bot_token: str):
        self.logger = get_logger(__name__)
        self.bot_token = bot_token
        self.bot = None
        
    async def initialize(self):
        """Инициализирует Discord бота"""
        try:
            intents = discord.Intents.default()
            intents.message_content = True
            
            self.bot = discord.Client(intents=intents)
            
            @self.bot.event
            async def on_ready():
                self.logger.info(f'Discord бот подключен: {self.bot.user}')
            
            # Запускаем бота в фоне
            asyncio.create_task(self.bot.start(self.bot_token))
            
            # Ждем подключения
            await asyncio.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Discord бота: {e}")
    
    async def send_message(self, channel_id: int, post: SocialPost) -> bool:
        """Отправляет сообщение в Discord канал"""
        if not self.bot:
            return False
            
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                self.logger.error(f"Канал не найден: {channel_id}")
                return False
            
            # Формируем сообщение
            message = post.text
            if post.hashtags:
                hashtags_str = " ".join([f"#{tag}" for tag in post.hashtags])
                message = f"{message}\n\n{hashtags_str}"
            
            # Отправляем сообщение
            await channel.send(message)
            self.logger.info(f"Сообщение отправлено в Discord канал {channel_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при отправке сообщения в Discord: {e}")
            return False
    
    async def close(self):
        """Закрывает соединение с Discord"""
        if self.bot:
            await self.bot.close()

class TelegramManager:
    """Менеджер для работы с Telegram"""
    
    def __init__(self, bot_token: str):
        self.logger = get_logger(__name__)
        self.bot = Bot(token=bot_token)
        
    async def send_message(self, chat_id: str, post: SocialPost) -> bool:
        """Отправляет сообщение в Telegram канал"""
        try:
            # Формируем сообщение
            message = post.text
            if post.hashtags:
                hashtags_str = " ".join([f"#{tag}" for tag in post.hashtags])
                message = f"{message}\n\n{hashtags_str}"
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            self.logger.info(f"Сообщение отправлено в Telegram канал {chat_id}")
            return True
            
        except TelegramError as e:
            self.logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
            return False

class SocialMediaManager:
    """Основной менеджер для работы с социальными сетями"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = get_marketing_config()
        
        # Инициализация менеджеров
        self.twitter = None
        self.discord = None
        self.telegram = None
        
        self._initialize_platforms()
    
    def _initialize_platforms(self):
        """Инициализирует платформы социальных сетей"""
        try:
            # Twitter
            twitter_config = self.config.social_media.get('twitter', {})
            if twitter_config.get('enabled') and all(twitter_config.get(key) for key in 
                ['api_key', 'api_secret', 'access_token', 'access_token_secret']):
                self.twitter = TwitterManager(
                    twitter_config['api_key'],
                    twitter_config['api_secret'],
                    twitter_config['access_token'],
                    twitter_config['access_token_secret']
                )
            
            # Discord
            discord_config = self.config.social_media.get('discord', {})
            if discord_config.get('enabled') and discord_config.get('bot_token'):
                self.discord = DiscordManager(discord_config['bot_token'])
            
            # Telegram
            telegram_config = self.config.social_media.get('telegram', {})
            if telegram_config.get('enabled') and telegram_config.get('bot_token'):
                self.telegram = TelegramManager(telegram_config['bot_token'])
                
        except Exception as e:
            self.logger.error(f"Ошибка инициализации социальных сетей: {e}")
    
    async def promote_token(self, promotion: TokenPromotion) -> Dict[str, bool]:
        """Продвигает токен во всех социальных сетях"""
        with LogOperation(f"Продвижение токена {promotion.token_symbol}"):
            results = {}
            
            # Генерируем контент для продвижения
            posts = self._generate_promotion_content(promotion)
            
            # Публикуем в Twitter
            if self.twitter:
                twitter_success = await self._promote_on_twitter(posts, promotion)
                results['twitter'] = twitter_success
            
            # Публикуем в Discord
            if self.discord:
                discord_success = await self._promote_on_discord(posts, promotion)
                results['discord'] = discord_success
            
            # Публикуем в Telegram
            if self.telegram:
                telegram_success = await self._promote_on_telegram(posts, promotion)
                results['telegram'] = telegram_success
            
            return results
    
    def _generate_promotion_content(self, promotion: TokenPromotion) -> List[SocialPost]:
        """Генерирует контент для продвижения токена"""
        posts = []
        
        # Основной пост о запуске
        main_post = SocialPost(
            text=f"🚀 Представляем {promotion.token_name} (${promotion.token_symbol})!\n\n"
                 f"{promotion.description}\n\n"
                 f"📍 Адрес контракта: {promotion.token_address[:8]}...{promotion.token_address[-8:]}\n"
                 f"🌐 Сайт: {promotion.website or 'Скоро'}\n\n"
                 f"#Solana #DeFi #NewToken",
            hashtags=['Solana', 'DeFi', 'NewToken', promotion.token_symbol, 'Crypto']
        )
        posts.append(main_post)
        
        # Пост о ключевых особенностях
        if promotion.key_features:
            features_text = "🔥 Ключевые особенности:\n\n"
            for i, feature in enumerate(promotion.key_features[:5], 1):
                features_text += f"{i}. {feature}\n"
            
            features_post = SocialPost(
                text=features_text,
                hashtags=['Innovation', 'Technology', promotion.token_symbol]
            )
            posts.append(features_post)
        
        # Пост о торговле
        trading_post = SocialPost(
            text=f"💰 ${promotion.token_symbol} уже доступен для торговли!\n\n"
                 f"🔄 Торгуйте на популярных DEX:\n"
                 f"• Raydium\n"
                 f"• Orca\n"
                 f"• Jupiter\n\n"
                 f"⚡ Низкие комиссии благодаря сети Solana!",
            hashtags=['Trading', 'DEX', 'Raydium', 'Orca', 'Jupiter']
        )
        posts.append(trading_post)
        
        return posts
    
    async def _promote_on_twitter(self, posts: List[SocialPost], promotion: TokenPromotion) -> bool:
        """Продвигает токен в Twitter"""
        try:
            # Публикуем основной пост
            success = await self.twitter.post_tweet(posts[0])
            
            if success and len(posts) > 1:
                # Ждем перед публикацией следующих постов
                await asyncio.sleep(300)  # 5 минут
                
                # Публикуем остальные посты с интервалами
                for post in posts[1:]:
                    await self.twitter.post_tweet(post)
                    await asyncio.sleep(600)  # 10 минут между постами
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка продвижения в Twitter: {e}")
            return False
    
    async def _promote_on_discord(self, posts: List[SocialPost], promotion: TokenPromotion) -> bool:
        """Продвигает токен в Discord"""
        try:
            if not self.discord.bot:
                await self.discord.initialize()
            
            # Получаем ID канала из конфигурации
            discord_config = self.config.social_media.get('discord', {})
            channel_id = discord_config.get('channel_id')
            
            if not channel_id:
                self.logger.warning("Discord channel_id не настроен")
                return False
            
            # Отправляем все посты
            for post in posts:
                success = await self.discord.send_message(channel_id, post)
                if not success:
                    return False
                await asyncio.sleep(60)  # 1 минута между сообщениями
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка продвижения в Discord: {e}")
            return False
    
    async def _promote_on_telegram(self, posts: List[SocialPost], promotion: TokenPromotion) -> bool:
        """Продвигает токен в Telegram"""
        try:
            # Получаем ID канала из конфигурации
            telegram_config = self.config.social_media.get('telegram', {})
            channel_id = telegram_config.get('channel_id')
            
            if not channel_id:
                self.logger.warning("Telegram channel_id не настроен")
                return False
            
            # Отправляем все посты
            for post in posts:
                success = await self.telegram.send_message(channel_id, post)
                if not success:
                    return False
                await asyncio.sleep(30)  # 30 секунд между сообщениями
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка продвижения в Telegram: {e}")
            return False
    
    async def schedule_regular_posts(self, promotion: TokenPromotion, days: int = 7):
        """Планирует регулярные посты о токене"""
        with LogOperation(f"Планирование постов для {promotion.token_symbol} на {days} дней"):
            try:
                # Генерируем контент для регулярных постов
                regular_posts = self._generate_regular_content(promotion)
                
                # Планируем посты на несколько дней
                for day in range(days):
                    post_time = datetime.now() + timedelta(days=day+1)
                    
                    # Выбираем случайный пост
                    post = random.choice(regular_posts)
                    post.scheduled_time = post_time
                    
                    # Здесь можно добавить логику планирования
                    # Например, сохранение в базу данных или использование планировщика
                    self.logger.info(f"Запланирован пост на {post_time}: {post.text[:50]}...")
                
                return True
                
            except Exception as e:
                self.logger.error(f"Ошибка планирования постов: {e}")
                return False
    
    def _generate_regular_content(self, promotion: TokenPromotion) -> List[SocialPost]:
        """Генерирует контент для регулярных постов"""
        posts = []
        
        # Различные типы постов
        post_templates = [
            f"📈 ${promotion.token_symbol} продолжает развиваться! Следите за обновлениями.",
            f"🔥 Не упустите возможность стать частью экосистемы {promotion.token_name}!",
            f"💎 ${promotion.token_symbol} - инновационное решение в мире DeFi!",
            f"🚀 Присоединяйтесь к сообществу {promotion.token_name} уже сегодня!",
            f"⚡ Быстрые и дешевые транзакции с ${promotion.token_symbol} на Solana!",
        ]
        
        for template in post_templates:
            post = SocialPost(
                text=template,
                hashtags=[promotion.token_symbol, 'Solana', 'DeFi', 'Crypto']
            )
            posts.append(post)
        
        return posts
    
    async def close(self):
        """Закрывает соединения с социальными сетями"""
        if self.discord:
            await self.discord.close()
