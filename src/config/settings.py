"""
应用程序配置管理
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


@dataclass
class InoreaderConfig:
    """Inoreader API配置"""
    app_id: str
    app_key: str
    base_url: str = "https://www.inoreader.com/reader/api/0/"
    oauth_url: str = "https://www.inoreader.com/oauth2/"

    # API区域配置
    regions: list = None
    current_region: int = 0

    def __post_init__(self):
        if self.regions is None:
            self.regions = [
                {
                    "name": "区域1",
                    "base_url": "https://www.inoreader.com/reader/api/0/",
                    "oauth_url": "https://www.inoreader.com/oauth2/",
                    "description": "主要API区域"
                },
                {
                    "name": "区域2",
                    "base_url": "https://jp.inoreader.com/reader/api/0/",
                    "oauth_url": "https://jp.inoreader.com/oauth2/",
                    "description": "日本API区域"
                }
            ]

    def get_current_region(self) -> dict:
        """获取当前使用的API区域"""
        return self.regions[self.current_region]

    def switch_to_next_region(self) -> bool:
        """切换到下一个API区域"""
        if self.current_region < len(self.regions) - 1:
            self.current_region += 1
            return True
        return False

    def reset_region(self):
        """重置到第一个区域"""
        self.current_region = 0


@dataclass
class AppConfig:
    """应用程序配置"""
    debug: bool = False
    log_level: str = "INFO"
    cache_dir: str = ".cache"
    max_articles_per_request: int = 100
    request_timeout: int = 30

    # 缓存配置
    cache_enabled: bool = True
    cache_expire_hours: int = 1  # 缓存过期时间（小时）
    max_cache_size_mb: int = 100  # 最大缓存大小（MB）

    # API请求频率控制
    rate_limit_enabled: bool = True
    min_request_interval: float = 1.0  # 最小请求间隔（秒）
    max_retries: int = 3  # 最大重试次数
    retry_backoff_factor: float = 2.0  # 重试退避因子

    # 降级模式配置
    degraded_mode_enabled: bool = True
    degraded_cache_hours: int = 24  # 降级模式下缓存延长时间


class Settings:
    """配置管理器"""
    
    def __init__(self):
        self.inoreader = InoreaderConfig(
            app_id=os.getenv("INOREADER_APP_ID", "1000001602"),
            app_key=os.getenv("INOREADER_APP_KEY", "sQfe0f9MWiw9O4Xxkq3YwXNhsy9NrAT_")
        )
        
        self.app = AppConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cache_dir=os.getenv("CACHE_DIR", ".cache"),
            max_articles_per_request=int(os.getenv("MAX_ARTICLES_PER_REQUEST", "100")),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
            cache_enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            cache_expire_hours=int(os.getenv("CACHE_EXPIRE_HOURS", "1")),
            max_cache_size_mb=int(os.getenv("MAX_CACHE_SIZE_MB", "100"))
        )
    
    @property
    def user_token_file(self) -> str:
        """用户token存储文件路径"""
        return os.path.join(self.app.cache_dir, "user_token.json")
    
    def ensure_cache_dir(self) -> None:
        """确保缓存目录存在"""
        os.makedirs(self.app.cache_dir, exist_ok=True)


# 全局配置实例
settings = Settings()
