"""
筛选模块基础类和数据模型
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from ..models.news import NewsArticle


@dataclass
class KeywordMatch:
    """关键词匹配结果"""
    keyword: str
    category: str
    position: int
    context: str
    match_type: str = "exact"  # exact, fuzzy


@dataclass
class KeywordFilterResult:
    """关键词筛选结果"""
    article: NewsArticle
    matched_keywords: List[KeywordMatch]
    relevance_score: float
    category_scores: Dict[str, float]
    processing_time: float


@dataclass
class AIEvaluation:
    """AI评估结果"""
    relevance_score: int        # 政策相关性 (0-10)
    innovation_impact: int      # 创新影响 (0-10)
    practicality: int          # 实用性 (0-10)
    total_score: int           # 总分 (0-30)
    reasoning: str             # 评估理由
    confidence: float          # 置信度 (0-1)


@dataclass
class AIFilterResult:
    """AI筛选结果"""
    article: NewsArticle
    evaluation: AIEvaluation
    processing_time: float
    ai_model: str
    cached: bool = False


@dataclass
class CombinedFilterResult:
    """综合筛选结果"""
    article: NewsArticle
    keyword_result: Optional[KeywordFilterResult]
    ai_result: Optional[AIFilterResult]
    final_score: float
    selected: bool
    rejection_reason: Optional[str]


@dataclass
class FilterChainResult:
    """筛选链执行结果"""
    # 输入统计
    total_articles: int
    processing_start_time: datetime
    processing_end_time: Optional[datetime] = None

    # 筛选统计
    keyword_filtered_count: int = 0
    ai_filtered_count: int = 0
    final_selected_count: int = 0

    # 结果数据
    selected_articles: List[CombinedFilterResult] = None
    rejected_articles: List[CombinedFilterResult] = None

    # 性能统计
    keyword_filter_time: float = 0.0
    ai_filter_time: float = 0.0
    total_processing_time: float = 0.0

    # 错误信息
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.selected_articles is None:
            self.selected_articles = []
        if self.rejected_articles is None:
            self.rejected_articles = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class SubscriptionFilterResult:
    """单个订阅源的筛选结果"""
    subscription_id: str
    subscription_title: str
    filter_result: FilterChainResult
    articles_fetched: int
    fetch_time: float

    @property
    def selected_count(self) -> int:
        """获取选中文章数量"""
        return self.filter_result.final_selected_count

    @property
    def total_processing_time(self) -> float:
        """获取总处理时间（包括获取和筛选）"""
        return self.fetch_time + self.filter_result.total_processing_time


@dataclass
class BatchFilterResult:
    """批量筛选结果"""
    # 基本信息
    total_subscriptions: int
    processed_subscriptions: int
    processing_start_time: datetime
    processing_end_time: Optional[datetime] = None

    # 订阅源结果
    subscription_results: List[SubscriptionFilterResult] = None

    # 汇总统计
    total_articles_fetched: int = 0
    total_articles_selected: int = 0
    total_fetch_time: float = 0.0
    total_filter_time: float = 0.0

    # 错误信息
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.subscription_results is None:
            self.subscription_results = []
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []

    @property
    def all_selected_articles(self) -> List[CombinedFilterResult]:
        """获取所有选中的文章"""
        all_articles = []
        for sub_result in self.subscription_results:
            all_articles.extend(sub_result.filter_result.selected_articles)
        return all_articles

    @property
    def success_rate(self) -> float:
        """获取成功处理的订阅源比例"""
        if self.total_subscriptions == 0:
            return 0.0
        return self.processed_subscriptions / self.total_subscriptions

    @property
    def total_processing_time(self) -> float:
        """获取总处理时间"""
        if self.processing_end_time and self.processing_start_time:
            return (self.processing_end_time - self.processing_start_time).total_seconds()
        return 0.0


class BaseFilter(ABC):
    """筛选器基类"""
    
    @abstractmethod
    def filter(self, articles: List[NewsArticle]) -> List[Any]:
        """筛选文章的抽象方法"""
        pass
    
    @abstractmethod
    def filter_single(self, article: NewsArticle) -> Optional[Any]:
        """筛选单篇文章的抽象方法"""
        pass


class FilterMetrics:
    """筛选性能指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'processing_times': [],
            'memory_usage': [],
            'accuracy_scores': [],
            'throughput': [],
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def record_processing_time(self, time_ms: float):
        """记录处理时间"""
        self.metrics['processing_times'].append(time_ms)
    
    def record_memory_usage(self, memory_mb: float):
        """记录内存使用"""
        self.metrics['memory_usage'].append(memory_mb)
    
    def record_error(self):
        """记录错误"""
        self.metrics['error_count'] += 1
    
    def record_cache_hit(self):
        """记录缓存命中"""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        self.metrics['cache_misses'] += 1
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        processing_times = self.metrics['processing_times']
        if not processing_times:
            return {"status": "no_data"}
        
        import statistics
        
        return {
            'avg_processing_time': statistics.mean(processing_times),
            'median_processing_time': statistics.median(processing_times),
            'max_processing_time': max(processing_times),
            'min_processing_time': min(processing_times),
            'total_processed': len(processing_times),
            'error_rate': self.metrics['error_count'] / len(processing_times) if processing_times else 0,
            'cache_hit_rate': (
                self.metrics['cache_hits'] / 
                (self.metrics['cache_hits'] + self.metrics['cache_misses'])
                if (self.metrics['cache_hits'] + self.metrics['cache_misses']) > 0 else 0
            )
        }
    
    def reset(self):
        """重置指标"""
        self.metrics = {
            'processing_times': [],
            'memory_usage': [],
            'accuracy_scores': [],
            'throughput': [],
            'error_count': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
