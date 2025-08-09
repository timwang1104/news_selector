"""
新闻去重服务
"""
import logging
import re
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from collections import defaultdict

from ..models.news import NewsArticle

logger = logging.getLogger(__name__)


class NewsDeduplicator:
    """新闻去重器"""
    
    def __init__(self,
                 title_threshold: float = 0.8,
                 content_threshold: float = 0.7,
                 time_window_hours: int = 72,
                 min_content_length: int = 20):
        """
        初始化去重器
        
        Args:
            title_threshold: 标题相似度阈值
            content_threshold: 内容相似度阈值
            time_window_hours: 时间窗口（小时）
            min_content_length: 最小内容长度
        """
        self.title_threshold = title_threshold
        self.content_threshold = content_threshold
        self.time_window_hours = time_window_hours
        self.min_content_length = min_content_length
        
        # 去重统计
        self.stats = {
            'original_count': 0,
            'deduplicated_count': 0,
            'removed_count': 0,
            'duplicate_groups': []
        }
    
    def deduplicate(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """
        执行去重
        
        Args:
            articles: 原始文章列表
            
        Returns:
            去重后的文章列表
        """
        if not articles:
            return articles
        
        logger.info(f"开始去重，原始文章数: {len(articles)}")
        
        # 重置统计
        self.stats = {
            'original_count': len(articles),
            'deduplicated_count': 0,
            'removed_count': 0,
            'duplicate_groups': []
        }
        
        # 预处理文章
        processed_articles = self._preprocess_articles(articles)
        
        # 按时间排序（最早的在前）
        processed_articles.sort(key=lambda x: x.published)
        
        # 执行去重
        deduplicated = self._perform_deduplication(processed_articles)
        
        # 更新统计
        self.stats['deduplicated_count'] = len(deduplicated)
        self.stats['removed_count'] = self.stats['original_count'] - self.stats['deduplicated_count']
        
        logger.info(f"去重完成，保留文章数: {len(deduplicated)}, 去除重复: {self.stats['removed_count']}")
        
        return deduplicated
    
    def _preprocess_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """预处理文章"""
        processed = []
        
        for article in articles:
            # 过滤掉内容过短的文章
            if len(article.content) < self.min_content_length:
                continue
            
            # 标准化文本
            article.title = self._normalize_text(article.title)
            article.summary = self._normalize_text(article.summary)
            article.content = self._normalize_text(article.content)
            
            processed.append(article)
        
        return processed
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本"""
        if not text:
            return ""
        
        # 去除多余空白
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 去除特殊字符（保留中英文、数字、基本标点）
        text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()（）【】""''—-]', '', text)
        
        return text
    
    def _perform_deduplication(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """执行去重逻辑"""
        if not articles:
            return articles
        
        # 用于存储去重后的文章
        deduplicated = []
        # 用于跟踪已处理的文章索引
        processed_indices = set()

        print(f"     🔍 开始去重算法，文章数: {len(articles)}, 时间窗口: {self.time_window_hours}小时, 相似度阈值: {self.title_threshold}")

        # 每处理10篇文章显示一次进度
        progress_interval = max(1, len(articles) // 10)

        for i, article in enumerate(articles):
            if i in processed_indices:
                continue

            # 显示进度
            if i % progress_interval == 0 or i == len(articles) - 1:
                print(f"     📖 处理进度: {i+1}/{len(articles)} ({(i+1)/len(articles)*100:.1f}%)")

            # 当前文章作为候选保留文章
            current_group = [article]
            duplicate_indices = {i}
            
            # 在时间窗口内查找相似文章
            time_window_start = article.published
            time_window_end = time_window_start + timedelta(hours=self.time_window_hours)
            
            for j, other_article in enumerate(articles[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                # 检查是否在时间窗口内
                if other_article.published > time_window_end:
                    break  # 由于已排序，后续文章都超出时间窗口
                
                # 计算相似度
                similarity = self._calculate_similarity(article, other_article)
                
                if similarity >= self.title_threshold:
                    current_group.append(other_article)
                    duplicate_indices.add(j)
            
            # 如果找到重复文章，记录重复组
            if len(current_group) > 1:
                self.stats['duplicate_groups'].append({
                    'kept_article': {
                        'title': article.title,
                        'published': article.published.isoformat(),
                        'url': article.url
                    },
                    'removed_articles': [
                        {
                            'title': dup.title,
                            'published': dup.published.isoformat(),
                            'url': dup.url
                        }
                        for dup in current_group[1:]
                    ],
                    'similarity_scores': [
                        self._calculate_similarity(article, dup)
                        for dup in current_group[1:]
                    ]
                })
            
            # 保留最早发布的文章（已按时间排序，第一个就是最早的）
            deduplicated.append(article)
            
            # 标记所有重复文章为已处理
            processed_indices.update(duplicate_indices)
        
        return deduplicated
    
    def _calculate_similarity(self, article1: NewsArticle, article2: NewsArticle) -> float:
        """
        计算两篇文章的相似度
        
        Args:
            article1: 文章1
            article2: 文章2
            
        Returns:
            相似度分数 (0-1)
        """
        # 标题相似度（权重0.7）
        title_sim = self._text_similarity(article1.title, article2.title)
        
        # 摘要相似度（权重0.2）
        summary_sim = self._text_similarity(article1.summary, article2.summary)
        
        # 内容相似度（权重0.1，只取前500字符避免计算量过大）
        content1 = article1.content[:500] if article1.content else ""
        content2 = article2.content[:500] if article2.content else ""
        content_sim = self._text_similarity(content1, content2)
        
        # 加权平均
        weighted_similarity = (
            title_sim * 0.7 + 
            summary_sim * 0.2 + 
            content_sim * 0.1
        )
        
        return weighted_similarity
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数 (0-1)
        """
        if not text1 or not text2:
            return 0.0
        
        # 使用SequenceMatcher计算相似度
        matcher = SequenceMatcher(None, text1, text2)
        return matcher.ratio()
    
    def get_deduplication_stats(self) -> Dict:
        """获取去重统计信息"""
        return {
            'original_count': self.stats['original_count'],
            'deduplicated_count': self.stats['deduplicated_count'],
            'removed_count': self.stats['removed_count'],
            'deduplication_rate': (
                self.stats['removed_count'] / self.stats['original_count'] 
                if self.stats['original_count'] > 0 else 0
            ),
            'duplicate_groups_count': len(self.stats['duplicate_groups']),
            'duplicate_groups': self.stats['duplicate_groups'][:10]  # 只返回前10个重复组
        }
    
    def get_detailed_stats(self) -> Dict:
        """获取详细统计信息"""
        stats = self.get_deduplication_stats()
        
        # 添加更多统计信息
        if self.stats['duplicate_groups']:
            similarities = []
            for group in self.stats['duplicate_groups']:
                similarities.extend(group['similarity_scores'])
            
            stats.update({
                'avg_similarity': sum(similarities) / len(similarities) if similarities else 0,
                'max_similarity': max(similarities) if similarities else 0,
                'min_similarity': min(similarities) if similarities else 0,
                'total_duplicates_found': sum(len(group['removed_articles']) for group in self.stats['duplicate_groups'])
            })
        
        return stats


# 全局去重器实例
_deduplicator_instance = None


def get_deduplicator(title_threshold: float = 0.8,
                    content_threshold: float = 0.7,
                    time_window_hours: int = 72) -> NewsDeduplicator:
    """
    获取去重器实例
    
    Args:
        title_threshold: 标题相似度阈值
        content_threshold: 内容相似度阈值
        time_window_hours: 时间窗口
        
    Returns:
        去重器实例
    """
    global _deduplicator_instance
    if _deduplicator_instance is None:
        _deduplicator_instance = NewsDeduplicator(
            title_threshold=title_threshold,
            content_threshold=content_threshold,
            time_window_hours=time_window_hours
        )
    return _deduplicator_instance


def deduplicate_articles(articles: List[NewsArticle], 
                        title_threshold: float = 0.8,
                        time_window_hours: int = 72) -> Tuple[List[NewsArticle], Dict]:
    """
    去重文章的便捷函数
    
    Args:
        articles: 文章列表
        title_threshold: 标题相似度阈值
        time_window_hours: 时间窗口
        
    Returns:
        (去重后的文章列表, 统计信息)
    """
    deduplicator = get_deduplicator(
        title_threshold=title_threshold,
        time_window_hours=time_window_hours
    )
    
    deduplicated_articles = deduplicator.deduplicate(articles)
    stats = deduplicator.get_deduplication_stats()
    
    return deduplicated_articles, stats


if __name__ == "__main__":
    # 测试代码
    print("新闻去重服务测试")
    
    deduplicator = get_deduplicator()
    print(f"去重器配置: 标题阈值={deduplicator.title_threshold}, 时间窗口={deduplicator.time_window_hours}小时")
