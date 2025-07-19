"""
筛选功能配置管理
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import os


@dataclass
class KeywordConfig:
    """关键词筛选配置"""
    keywords: Dict[str, List[str]]  # 分类关键词
    weights: Dict[str, float]       # 分类权重
    threshold: float = 0.6          # 筛选阈值
    max_results: int = 100          # 最大结果数
    case_sensitive: bool = False    # 大小写敏感
    fuzzy_match: bool = True        # 模糊匹配
    word_boundary: bool = True      # 单词边界检查
    phrase_matching: bool = True    # 短语匹配
    min_keyword_length: int = 2     # 最小关键词长度
    min_matches: int = 2            # 最少匹配关键词数


@dataclass
class AIFilterConfig:
    """AI筛选配置"""
    # AI服务配置
    model_name: str = "gpt-3.5-turbo"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 1000
    
    # 筛选配置
    threshold: int = 20             # 总分阈值 (满分30)
    max_requests: int = 50          # 最大请求数
    batch_size: int = 5             # 批处理大小
    
    # 性能配置
    timeout: int = 30               # 请求超时时间
    retry_times: int = 3            # 重试次数
    retry_delay: int = 1            # 重试延迟
    enable_cache: bool = True       # 启用缓存
    cache_ttl: int = 3600          # 缓存过期时间(秒)
    cache_size: int = 1000         # 缓存大小
    
    # 降级策略
    fallback_enabled: bool = True
    fallback_threshold: float = 0.7  # 关键词筛选分数作为降级
    min_confidence: float = 0.5     # 最小置信度


@dataclass
class FilterChainConfig:
    """筛选链配置"""
    # 筛选流程配置
    enable_keyword_filter: bool = True
    enable_ai_filter: bool = True
    keyword_threshold: float = 0.6
    ai_threshold: int = 20
    final_score_threshold: float = 0.7
    
    # 流程控制
    max_keyword_results: int = 100
    max_ai_requests: int = 50
    max_final_results: int = 30
    fail_fast: bool = False
    enable_parallel: bool = True
    batch_size: int = 10
    
    # 结果配置
    sort_by: str = "final_score"    # final_score, relevance, timestamp
    include_rejected: bool = False
    include_metrics: bool = True


# 注意：INTERNATIONAL_TECH_KEYWORDS 已移动到 default_keywords.py
# 这里保留注释以避免混淆



class FilterConfigManager:
    """筛选配置管理器"""
    
    def __init__(self):
        self.configs = {}
        self.load_default_configs()
    
    def load_default_configs(self):
        """加载默认配置"""
        # 关键词筛选配置
        from .default_keywords import INTERNATIONAL_TECH_KEYWORDS
        keyword_config = KeywordConfig(
            keywords={k: v["keywords"] for k, v in INTERNATIONAL_TECH_KEYWORDS.items()},
            weights={k: v["weight"] for k, v in INTERNATIONAL_TECH_KEYWORDS.items()},
            threshold=0.65,
            max_results=150,
            min_matches=2
        )
        
        # AI筛选配置
        ai_config = AIFilterConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", ""),
            threshold=20,
            max_requests=50
        )
        
        # 筛选链配置
        chain_config = FilterChainConfig(
            keyword_threshold=0.65,
            ai_threshold=20,
            final_score_threshold=0.7,
            max_keyword_results=100,
            max_ai_requests=50,
            max_final_results=30
        )
        
        self.configs = {
            "keyword": keyword_config,
            "ai": ai_config,
            "chain": chain_config
        }
    
    def get_keyword_config(self) -> KeywordConfig:
        """获取关键词筛选配置"""
        return self.configs["keyword"]
    
    def get_ai_config(self) -> AIFilterConfig:
        """获取AI筛选配置"""
        return self.configs["ai"]
    
    def get_chain_config(self) -> FilterChainConfig:
        """获取筛选链配置"""
        return self.configs["chain"]
    
    def update_config(self, config_type: str, **kwargs):
        """更新配置参数"""
        if config_type not in self.configs:
            raise ValueError(f"Unknown config type: {config_type}")
        
        config = self.configs[config_type]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                print(f"Warning: Unknown config key '{key}' for {config_type}")


# 全局配置管理器实例
filter_config_manager = FilterConfigManager()
