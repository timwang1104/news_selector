"""
测试配置模块
"""
import os
import tempfile
import pytest
from src.config.settings import Settings, InoreaderConfig, AppConfig


class TestSettings:
    """测试配置管理器"""
    
    def test_default_settings(self):
        """测试默认配置"""
        settings = Settings()
        
        assert settings.inoreader.app_id == "1000001602"
        assert settings.inoreader.app_key == "sQfe0f9MWiw9O4Xxkq3YwXNhsy9NrAT_"
        assert settings.inoreader.base_url == "https://www.inoreader.com/reader/api/0/"
        assert settings.app.debug == False
        assert settings.app.log_level == "INFO"
        assert settings.app.max_articles_per_request == 100
    
    def test_user_token_file_path(self):
        """测试用户token文件路径"""
        settings = Settings()
        expected_path = os.path.join(settings.app.cache_dir, "user_token.json")
        assert settings.user_token_file == expected_path
    
    def test_ensure_cache_dir(self):
        """测试确保缓存目录存在"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 临时修改缓存目录
            settings = Settings()
            settings.app.cache_dir = os.path.join(temp_dir, "test_cache")
            
            # 目录不存在
            assert not os.path.exists(settings.app.cache_dir)
            
            # 调用方法创建目录
            settings.ensure_cache_dir()
            
            # 目录应该存在
            assert os.path.exists(settings.app.cache_dir)
            assert os.path.isdir(settings.app.cache_dir)


class TestInoreaderConfig:
    """测试Inoreader配置"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = InoreaderConfig(
            app_id="test_app_id",
            app_key="test_app_key"
        )
        
        assert config.app_id == "test_app_id"
        assert config.app_key == "test_app_key"
        assert config.base_url == "https://www.inoreader.com/reader/api/0/"
        assert config.oauth_url == "https://www.inoreader.com/oauth2/"


class TestAppConfig:
    """测试应用配置"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = AppConfig(
            debug=True,
            log_level="DEBUG",
            cache_dir="/tmp/test",
            max_articles_per_request=50,
            request_timeout=60
        )
        
        assert config.debug == True
        assert config.log_level == "DEBUG"
        assert config.cache_dir == "/tmp/test"
        assert config.max_articles_per_request == 50
        assert config.request_timeout == 60
