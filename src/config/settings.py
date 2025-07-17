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


@dataclass
class AppConfig:
    """应用程序配置"""
    debug: bool = False
    log_level: str = "INFO"
    cache_dir: str = ".cache"
    max_articles_per_request: int = 100
    request_timeout: int = 30


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
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30"))
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
