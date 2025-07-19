"""
Модуль для настройки логирования
"""

import os
import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import colorlog
from rich.logging import RichHandler
from rich.console import Console

from .config import get_logging_config

class SolanaLogger:
    """Класс для настройки и управления логированием"""
    
    def __init__(self, name: str = "solana_deployer"):
        self.name = name
        self.logger: Optional[logging.Logger] = None
        self.console = Console()
        
    def setup_logger(self) -> logging.Logger:
        """Настраивает и возвращает логгер"""
        if self.logger is not None:
            return self.logger
            
        config = get_logging_config()
        
        # Создаем логгер
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(getattr(logging, config.level.upper()))
        
        # Очищаем существующие обработчики
        self.logger.handlers.clear()
        
        # Настраиваем форматтер для файлов
        file_formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Настраиваем цветной форматтер для консоли
        console_formatter = colorlog.ColoredFormatter(
            fmt='%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S',
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        
        # Добавляем файловый обработчик
        self._add_file_handler(config, file_formatter)
        
        # Добавляем консольный обработчик
        self._add_console_handler(console_formatter)
        
        # Добавляем Rich обработчик для красивого вывода
        self._add_rich_handler()
        
        return self.logger
    
    def _add_file_handler(self, config, formatter):
        """Добавляет файловый обработчик с ротацией"""
        try:
            # Создаем директорию для логов
            log_dir = Path(config.file).parent
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Парсим размер файла
            max_bytes = self._parse_size(config.max_size)
            
            # Создаем RotatingFileHandler
            file_handler = logging.handlers.RotatingFileHandler(
                filename=config.file,
                maxBytes=max_bytes,
                backupCount=config.backup_count,
                encoding='utf-8'
            )
            
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Ошибка при настройке файлового логирования: {e}")
    
    def _add_console_handler(self, formatter):
        """Добавляет консольный обработчик"""
        try:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"Ошибка при настройке консольного логирования: {e}")
    
    def _add_rich_handler(self):
        """Добавляет Rich обработчик для красивого вывода"""
        try:
            rich_handler = RichHandler(
                console=self.console,
                show_time=False,
                show_path=False,
                rich_tracebacks=True,
                tracebacks_show_locals=True
            )
            
            rich_handler.setLevel(logging.WARNING)
            self.logger.addHandler(rich_handler)
            
        except Exception as e:
            print(f"Ошибка при настройке Rich логирования: {e}")
    
    def _parse_size(self, size_str: str) -> int:
        """Парсит строку размера в байты"""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self) -> logging.Logger:
        """Возвращает настроенный логгер"""
        if self.logger is None:
            return self.setup_logger()
        return self.logger

# Глобальный экземпляр логгера
_logger_instance = SolanaLogger()

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Получает логгер с указанным именем"""
    if name:
        return SolanaLogger(name).setup_logger()
    return _logger_instance.get_logger()

def setup_logging() -> logging.Logger:
    """Настраивает глобальное логирование"""
    return _logger_instance.setup_logger()

# Удобные функции для логирования
def log_info(message: str, **kwargs):
    """Логирует информационное сообщение"""
    get_logger().info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Логирует предупреждение"""
    get_logger().warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """Логирует ошибку"""
    get_logger().error(message, **kwargs)

def log_debug(message: str, **kwargs):
    """Логирует отладочное сообщение"""
    get_logger().debug(message, **kwargs)

def log_critical(message: str, **kwargs):
    """Логирует критическую ошибку"""
    get_logger().critical(message, **kwargs)

# Декоратор для логирования выполнения функций
def log_execution(func):
    """Декоратор для логирования выполнения функций"""
    def wrapper(*args, **kwargs):
        logger = get_logger()
        func_name = func.__name__
        
        logger.debug(f"Начало выполнения функции: {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Функция {func_name} выполнена успешно")
            return result
            
        except Exception as e:
            logger.error(f"Ошибка в функции {func_name}: {str(e)}")
            raise
            
    return wrapper

# Контекстный менеджер для логирования операций
class LogOperation:
    """Контекстный менеджер для логирования операций"""
    
    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None):
        self.operation_name = operation_name
        self.logger = logger or get_logger()
    
    def __enter__(self):
        self.logger.info(f"Начало операции: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.logger.info(f"Операция завершена успешно: {self.operation_name}")
        else:
            self.logger.error(f"Операция завершена с ошибкой: {self.operation_name} - {exc_val}")
        return False
