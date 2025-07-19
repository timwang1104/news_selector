"""
AI结果缓存机制
"""
import time
import hashlib
import json
import logging
from typing import Optional, Dict, Any
from ..models.news import NewsArticle
from ..filters.base import AIEvaluation

logger = logging.getLogger(__name__)


class AIResultCache:
    """AI评估结果缓存"""
    
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        self.cache: Dict[str, tuple] = {}
        self.ttl = ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, article: NewsArticle) -> Optional[AIEvaluation]:
        """获取缓存的评估结果"""
        article_hash = self._hash_article(article)
        
        if article_hash in self.cache:
            result, timestamp = self.cache[article_hash]
            
            # 检查是否过期
            if time.time() - timestamp < self.ttl:
                self.hits += 1
                logger.debug(f"Cache hit for article: {article.title[:50]}...")
                return self._deserialize_evaluation(result)
            else:
                # 删除过期缓存
                del self.cache[article_hash]
                logger.debug(f"Cache expired for article: {article.title[:50]}...")
        
        self.misses += 1
        return None
    
    def set(self, article: NewsArticle, evaluation: AIEvaluation):
        """设置缓存结果"""
        article_hash = self._hash_article(article)
        
        # 检查缓存大小限制
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        serialized_eval = self._serialize_evaluation(evaluation)
        self.cache[article_hash] = (serialized_eval, time.time())
        
        logger.debug(f"Cached evaluation for article: {article.title[:50]}...")
    
    def _hash_article(self, article: NewsArticle) -> str:
        """生成文章哈希值"""
        # 使用标题和摘要生成哈希，确保内容一致性
        content = f"{article.title or ''}{article.summary or ''}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _serialize_evaluation(self, evaluation: AIEvaluation) -> Dict[str, Any]:
        """序列化评估结果"""
        return {
            'relevance_score': evaluation.relevance_score,
            'innovation_impact': evaluation.innovation_impact,
            'practicality': evaluation.practicality,
            'total_score': evaluation.total_score,
            'reasoning': evaluation.reasoning,
            'confidence': evaluation.confidence
        }
    
    def _deserialize_evaluation(self, data: Dict[str, Any]) -> AIEvaluation:
        """反序列化评估结果"""
        return AIEvaluation(
            relevance_score=data['relevance_score'],
            innovation_impact=data['innovation_impact'],
            practicality=data['practicality'],
            total_score=data['total_score'],
            reasoning=data['reasoning'],
            confidence=data['confidence']
        )
    
    def _evict_oldest(self):
        """删除最旧的缓存项"""
        if not self.cache:
            return
        
        # 找到最旧的项
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]
        logger.debug("Evicted oldest cache entry")
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'ttl': self.ttl
        }
    
    def cleanup_expired(self):
        """清理过期的缓存项"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
