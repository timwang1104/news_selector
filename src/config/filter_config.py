"""
筛选功能配置管理
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import os
import json
from pathlib import Path


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
    max_requests: int = 50          # 最大请求数
    max_selected: int = 3           # 最大筛选数量（按评分排序取前N条）
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
class TagBalanceConfig:
    """标签平衡配置"""
    # 标签生成配置
    enable_tag_generation: bool = True
    min_tag_score: float = 0.2
    max_tags_per_article: int = 5
    primary_tag_threshold: float = 0.5

    # 标签数量限制
    enable_tag_limits: bool = True
    tag_limits: Dict[str, int] = None  # {tag_name: max_count}
    default_tag_limit: int = 5  # 默认标签限制

    # 平衡策略配置
    enable_balanced_selection: bool = True
    balance_threshold: float = 0.5  # 填充比例阈值
    underrepresented_boost: float = 1.5  # 代表性不足标签的权重提升

    def __post_init__(self):
        if self.tag_limits is None:
            self.tag_limits = {}


@dataclass
class FilterChainConfig:
    """筛选链配置"""
    # 筛选流程配置
    enable_keyword_filter: bool = True
    enable_ai_filter: bool = True
    keyword_threshold: float = 0.6
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

    # 标签平衡配置
    tag_balance: TagBalanceConfig = None

    def __post_init__(self):
        if self.tag_balance is None:
            self.tag_balance = TagBalanceConfig()


# 注意：INTERNATIONAL_TECH_KEYWORDS 已移动到 default_keywords.py
# 这里保留注释以避免混淆



class FilterConfigManager:
    """筛选配置管理器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "filter_config.json"
        self.configs = {}
        self.load_configs()
    
    def load_configs(self):
        """加载配置"""
        # 先加载默认配置
        self.load_default_configs()

        # 然后尝试从文件加载保存的配置
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_configs = json.load(f)

                # 更新AI配置
                if "ai" in saved_configs:
                    ai_data = saved_configs["ai"]
                    self.configs["ai"] = AIFilterConfig(**ai_data)

                # 更新筛选链配置
                if "chain" in saved_configs:
                    chain_data = saved_configs["chain"]

                    # 处理嵌套的tag_balance配置
                    if "tag_balance" in chain_data and isinstance(chain_data["tag_balance"], dict):
                        chain_data["tag_balance"] = TagBalanceConfig(**chain_data["tag_balance"])

                    self.configs["chain"] = FilterChainConfig(**chain_data)

                # 更新关键词配置
                if "keyword" in saved_configs:
                    keyword_data = saved_configs["keyword"]

                    # 如果保存的关键词配置为空，使用默认配置
                    if not keyword_data.get("keywords") or not keyword_data.get("weights"):
                        print("⚠️  检测到空的关键词配置，使用默认关键词配置")
                        from .default_keywords import INTERNATIONAL_TECH_KEYWORDS
                        keyword_data["keywords"] = {k: v["keywords"] for k, v in INTERNATIONAL_TECH_KEYWORDS.items()}
                        keyword_data["weights"] = {k: v["weight"] for k, v in INTERNATIONAL_TECH_KEYWORDS.items()}

                    self.configs["keyword"] = KeywordConfig(**keyword_data)

                print(f"✅ 已加载筛选配置: {self.config_file}")
            except Exception as e:
                print(f"⚠️  加载筛选配置失败: {e}")

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
            max_requests=50
        )

        # 创建默认标签限制配置
        default_tag_limits = {
            "artificial_intelligence": 8,
            "quantum_technology": 5,
            "biotechnology": 5,
            "semiconductor": 4,
            "5g_6g_networks": 3,
            "cybersecurity": 3,
            "tech_policy": 6,
            "industry_development": 4,
            "international_cooperation": 3,
            "key_institutions": 2
        }

        tag_balance_config = TagBalanceConfig(
            enable_tag_generation=True,
            enable_tag_limits=True,
            tag_limits=default_tag_limits,
            enable_balanced_selection=True
        )

        # 筛选链配置
        chain_config = FilterChainConfig(
            keyword_threshold=0.65,
            final_score_threshold=0.7,
            max_keyword_results=100,
            max_ai_requests=50,
            max_final_results=30,
            tag_balance=tag_balance_config
        )

        self.configs = {
            "keyword": keyword_config,
            "ai": ai_config,
            "chain": chain_config
        }

    def save_configs(self):
        """保存配置到文件"""
        try:
            # 转换配置为字典
            config_data = {}
            for key, config in self.configs.items():
                config_data[key] = asdict(config)

            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            print(f"✅ 筛选配置已保存: {self.config_file}")
        except Exception as e:
            print(f"⚠️  保存筛选配置失败: {e}")
    
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

        # 自动保存配置
        self.save_configs()

    def reload_configs(self):
        """重新加载配置"""
        self.load_configs()


# 全局配置管理器实例
filter_config_manager = FilterConfigManager()
