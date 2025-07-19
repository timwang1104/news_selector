"""
AI智能筛选器实现
"""
import time
import logging
from typing import List, Optional
from ..models.news import NewsArticle
from ..config.filter_config import AIFilterConfig
from ..ai.factory import create_ai_client
from ..ai.exceptions import AIClientError
from ..ai.cache import AIResultCache
from .base import BaseFilter, AIFilterResult, FilterMetrics

logger = logging.getLogger(__name__)


class AIFilter(BaseFilter):
    """AI智能筛选器"""
    
    def __init__(self, config: AIFilterConfig):
        self.config = config
        self.client = create_ai_client(config)
        self.cache = AIResultCache(ttl=config.cache_ttl, max_size=config.cache_size) if config.enable_cache else None
        self.metrics = FilterMetrics()
    
    def filter(self, articles: List[NewsArticle]) -> List[AIFilterResult]:
        """筛选文章列表"""
        if not articles:
            return []
        
        # 限制处理数量
        if len(articles) > self.config.max_requests:
            logger.warning(f"Too many articles ({len(articles)}), limiting to {self.config.max_requests}")
            articles = articles[:self.config.max_requests]
        
        results = []
        
        # 批量处理
        for batch in self._create_batches(articles, self.config.batch_size):
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
        
        # 过滤低分文章
        filtered_results = [
            result for result in results
            if result.evaluation.total_score >= self.config.threshold
        ]
        
        # 按总分排序
        filtered_results.sort(key=lambda x: x.evaluation.total_score, reverse=True)
        
        return filtered_results
    
    def filter_single(self, article: NewsArticle) -> Optional[AIFilterResult]:
        """筛选单篇文章"""
        start_time = time.time()
        
        try:
            # 检查缓存
            cached_evaluation = None
            if self.cache:
                cached_evaluation = self.cache.get(article)
                if cached_evaluation:
                    self.metrics.record_cache_hit()
                    processing_time = time.time() - start_time
                    
                    return AIFilterResult(
                        article=article,
                        evaluation=cached_evaluation,
                        processing_time=processing_time,
                        ai_model=self.config.model_name,
                        cached=True
                    )
                else:
                    self.metrics.record_cache_miss()
            
            # AI评估
            evaluation = self.client.evaluate_article(article)
            
            # 缓存结果
            if self.cache and evaluation.confidence >= self.config.min_confidence:
                self.cache.set(article, evaluation)
            
            processing_time = time.time() - start_time
            self.metrics.record_processing_time(processing_time * 1000)
            
            result = AIFilterResult(
                article=article,
                evaluation=evaluation,
                processing_time=processing_time,
                ai_model=self.config.model_name,
                cached=False
            )
            
            # 检查是否通过阈值
            if evaluation.total_score >= self.config.threshold:
                return result
            else:
                return None
                
        except AIClientError as e:
            self.metrics.record_error()
            logger.error(f"AI filtering failed for article {article.id}: {e}")
            
            # 降级策略
            if self.config.fallback_enabled:
                return self._fallback_filter(article, start_time)
            else:
                return None
        except Exception as e:
            self.metrics.record_error()
            logger.error(f"Unexpected error in AI filtering: {e}")
            return None
    
    def _process_batch(self, articles: List[NewsArticle]) -> List[AIFilterResult]:
        """处理文章批次"""
        # 检查缓存，分离已缓存和未缓存的文章
        cached_results = []
        uncached_articles = []
        
        if self.cache:
            for article in articles:
                cached_evaluation = self.cache.get(article)
                if cached_evaluation:
                    self.metrics.record_cache_hit()
                    cached_results.append(AIFilterResult(
                        article=article,
                        evaluation=cached_evaluation,
                        processing_time=0.0,
                        ai_model=self.config.model_name,
                        cached=True
                    ))
                else:
                    self.metrics.record_cache_miss()
                    uncached_articles.append(article)
        else:
            uncached_articles = articles
        
        # 批量评估未缓存的文章
        uncached_results = []
        if uncached_articles:
            try:
                start_time = time.time()
                evaluations = self.client.batch_evaluate(uncached_articles)
                processing_time = time.time() - start_time
                
                for article, evaluation in zip(uncached_articles, evaluations):
                    # 缓存结果
                    if self.cache and evaluation.confidence >= self.config.min_confidence:
                        self.cache.set(article, evaluation)
                    
                    uncached_results.append(AIFilterResult(
                        article=article,
                        evaluation=evaluation,
                        processing_time=processing_time / len(uncached_articles),
                        ai_model=self.config.model_name,
                        cached=False
                    ))
                
                self.metrics.record_processing_time(processing_time * 1000)
                
            except AIClientError as e:
                self.metrics.record_error()
                logger.error(f"Batch AI evaluation failed: {e}")
                
                # 降级策略
                if self.config.fallback_enabled:
                    for article in uncached_articles:
                        fallback_result = self._fallback_filter(article, time.time())
                        if fallback_result:
                            uncached_results.append(fallback_result)
        
        return cached_results + uncached_results
    
    def _fallback_filter(self, article: NewsArticle, start_time: float) -> Optional[AIFilterResult]:
        """降级筛选策略"""
        # 使用简单的启发式评估
        fallback_evaluation = self.client._fallback_evaluation(article)
        
        processing_time = time.time() - start_time
        
        return AIFilterResult(
            article=article,
            evaluation=fallback_evaluation,
            processing_time=processing_time,
            ai_model="fallback",
            cached=False
        )
    
    def _create_batches(self, articles: List[NewsArticle], batch_size: int) -> List[List[NewsArticle]]:
        """创建文章批次"""
        batches = []
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def get_metrics(self) -> dict:
        """获取筛选指标"""
        metrics = self.metrics.get_performance_summary()
        
        # 添加缓存统计
        if self.cache:
            cache_stats = self.cache.get_stats()
            metrics.update(cache_stats)
        
        return metrics
    
    def reset_metrics(self):
        """重置指标"""
        self.metrics.reset()
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()
    
    def cleanup_cache(self):
        """清理过期缓存"""
        if self.cache:
            self.cache.cleanup_expired()
