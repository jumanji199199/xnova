"""
Модуль для управления конфигурацией проекта
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class SolanaConfig(BaseModel):
    network: str = "devnet"
    rpc_url: str = "https://api.devnet.solana.com"
    commitment: str = "confirmed"

class WalletConfig(BaseModel):
    keypair_path: str = "~/.config/solana/id.json"
    backup_path: str = "./wallets/backup/"

class TokenConfig(BaseModel):
    default_decimals: int = 9
    default_supply: int = 1000000000
    metadata_uri_base: str = "https://your-domain.com/metadata/"

class DEXConfig(BaseModel):
    raydium: Dict[str, Any] = Field(default_factory=dict)
    orca: Dict[str, Any] = Field(default_factory=dict)
    jupiter: Dict[str, Any] = Field(default_factory=dict)

class LiquidityConfig(BaseModel):
    initial_sol_amount: float = 10.0
    initial_token_ratio: int = 1000000
    slippage_tolerance: float = 0.01

class MarketingConfig(BaseModel):
    website: Dict[str, Any] = Field(default_factory=dict)
    social_media: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsConfig(BaseModel):
    price_check_interval: int = 60
    holder_analysis_interval: int = 3600
    report_generation_interval: int = 86400

class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/solana_deployer.log"
    max_size: str = "10MB"
    backup_count: int = 5

class SecurityConfig(BaseModel):
    max_tokens_per_day: int = 10
    min_sol_balance: float = 1.0
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60

class Config(BaseModel):
    solana: SolanaConfig = Field(default_factory=SolanaConfig)
    wallet: WalletConfig = Field(default_factory=WalletConfig)
    token: TokenConfig = Field(default_factory=TokenConfig)
    dex: DEXConfig = Field(default_factory=DEXConfig)
    liquidity: LiquidityConfig = Field(default_factory=LiquidityConfig)
    marketing: MarketingConfig = Field(default_factory=MarketingConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

class ConfigManager:
    """Менеджер конфигурации для загрузки и управления настройками"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[Config] = None
        
    def _get_default_config_path(self) -> str:
        """Получает путь к файлу конфигурации по умолчанию"""
        current_dir = Path(__file__).parent.parent.parent
        return str(current_dir / "config" / "settings.yaml")
    
    def load_config(self) -> Config:
        """Загружает конфигурацию из файла"""
        if self._config is None:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as file:
                    config_data = yaml.safe_load(file)
                
                # Заменяем переменные окружения
                config_data = self._replace_env_vars(config_data)
                
                self._config = Config(**config_data)
                
            except FileNotFoundError:
                print(f"Файл конфигурации не найден: {self.config_path}")
                print("Используется конфигурация по умолчанию")
                self._config = Config()
                
            except Exception as e:
                print(f"Ошибка при загрузке конфигурации: {e}")
                print("Используется конфигурация по умолчанию")
                self._config = Config()
        
        return self._config
    
    def _replace_env_vars(self, data: Any) -> Any:
        """Рекурсивно заменяет переменные окружения в конфигурации"""
        if isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Заменяем переменные вида ${VAR_NAME} или $VAR_NAME
            if data.startswith('${') and data.endswith('}'):
                var_name = data[2:-1]
                return os.getenv(var_name, data)
            elif data.startswith('$'):
                var_name = data[1:]
                return os.getenv(var_name, data)
            else:
                return data
        else:
            return data
    
    def get_config(self) -> Config:
        """Получает текущую конфигурацию"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def reload_config(self) -> Config:
        """Перезагружает конфигурацию"""
        self._config = None
        return self.load_config()
    
    def save_config(self, config: Config) -> None:
        """Сохраняет конфигурацию в файл"""
        try:
            config_dict = config.model_dump()
            
            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_dict, file, default_flow_style=False, 
                         allow_unicode=True, indent=2)
                
            self._config = config
            
        except Exception as e:
            raise Exception(f"Ошибка при сохранении конфигурации: {e}")

# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager()

def get_config() -> Config:
    """Получает глобальную конфигурацию"""
    return config_manager.get_config()

def reload_config() -> Config:
    """Перезагружает глобальную конфигурацию"""
    return config_manager.reload_config()

# Удобные функции для получения отдельных секций конфигурации
def get_solana_config() -> SolanaConfig:
    return get_config().solana

def get_wallet_config() -> WalletConfig:
    return get_config().wallet

def get_token_config() -> TokenConfig:
    return get_config().token

def get_dex_config() -> DEXConfig:
    return get_config().dex

def get_liquidity_config() -> LiquidityConfig:
    return get_config().liquidity

def get_marketing_config() -> MarketingConfig:
    return get_config().marketing

def get_analytics_config() -> AnalyticsConfig:
    return get_config().analytics

def get_logging_config() -> LoggingConfig:
    return get_config().logging

def get_security_config() -> SecurityConfig:
    return get_config().security
