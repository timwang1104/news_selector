"""话题分布分析服务

提供话题分布分析的服务接口，包括：
- 数据加载和预处理
- 话题分布分析
- 结果缓存和存储
- 可视化数据生成
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any

from ..filters.topic_distribution_analyzer import TopicDistributionAnalyzer, TopicDistributionResult
from ..filters.base import CombinedFilterResult, ArticleTag
from ..models.news import NewsArticle
from ..utils.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class TopicDistributionService:
    """话题分布分析服务"""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """
        初始化话题分布分析服务
        
        Args:
            cache_manager: 缓存管理器
        """
        self.analyzer = TopicDistributionAnalyzer()
        self.cache_manager = cache_manager or CacheManager()
        self.cache_ttl = 3600  # 缓存1小时
    
    def analyze_current_data(self, 
                           results: List[CombinedFilterResult],
                           use_cache: bool = True) -> TopicDistributionResult:
        """
        分析当前数据的话题分布
        
        Args:
            results: 筛选结果列表
            use_cache: 是否使用缓存
            
        Returns:
            话题分布分析结果
        """
        cache_key = self._generate_cache_key(results)
        
        # 尝试从缓存获取结果
        if use_cache:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.info("从缓存获取话题分布分析结果")
                return cached_result
        
        # 执行分析
        logger.info(f"开始分析{len(results)}篇文章的话题分布")
        analysis_result = self.analyzer.analyze_topic_distribution(results)
        
        # 缓存结果
        if use_cache:
            self.cache_manager.set(cache_key, analysis_result)
        
        logger.info(f"话题分布分析完成，发现{analysis_result.total_topics}个话题")
        return analysis_result
    
    def analyze_with_historical_comparison(self, 
                                         current_results: List[CombinedFilterResult],
                                         historical_results: List[CombinedFilterResult],
                                         use_cache: bool = True) -> TopicDistributionResult:
        """
        分析话题分布并与历史数据比较
        
        Args:
            current_results: 当前筛选结果
            historical_results: 历史筛选结果
            use_cache: 是否使用缓存
            
        Returns:
            包含趋势分析的话题分布结果
        """
        cache_key = self._generate_cache_key(current_results, "with_history")
        
        # 尝试从缓存获取结果
        if use_cache:
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                logger.info("从缓存获取历史对比分析结果")
                return cached_result
        
        # 执行分析
        logger.info(f"开始分析话题分布趋势，当前{len(current_results)}篇，历史{len(historical_results)}篇")
        analysis_result = self.analyzer.analyze_topic_distribution(
            current_results, historical_results
        )
        
        # 缓存结果
        if use_cache:
            self.cache_manager.set(cache_key, analysis_result)
        
        logger.info(f"趋势分析完成，新兴话题{len(analysis_result.emerging_topics)}个，衰落话题{len(analysis_result.declining_topics)}个")
        return analysis_result
    
    def load_data_from_json(self, json_file_path: str) -> List[CombinedFilterResult]:
        """
        从JSON文件加载新闻数据并转换为筛选结果
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            筛选结果列表
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                news_data = json.load(f)
            
            results = []
            for item in news_data:
                # 创建NewsArticle对象
                article = NewsArticle(
                    url=item.get('url', ''),
                    title=item.get('title', ''),
                    content=item.get('content', ''),
                    published_time=item.get('published_time', ''),
                    author=item.get('author', ''),
                    tags=item.get('tags', []),
                    category=item.get('category', '')
                )
                
                # 创建标签（如果有category信息）
                tags = []
                if item.get('category'):
                    tags.append(ArticleTag(
                        name=item['category'],
                        score=0.8,  # 默认评分
                        confidence=0.7,  # 默认置信度
                        source='imported'
                    ))
                
                # 创建CombinedFilterResult对象
                result = CombinedFilterResult(
                    article=article,
                    keyword_result=None,
                    ai_result=None,
                    final_score=0.5,  # 默认评分
                    selected=True,
                    rejection_reason=None,
                    tags=tags
                )
                
                results.append(result)
            
            logger.info(f"从{json_file_path}加载了{len(results)}篇文章")
            return results
            
        except Exception as e:
            logger.error(f"加载JSON文件失败: {e}")
            return []
    
    def generate_report(self, analysis_result: TopicDistributionResult) -> Dict[str, Any]:
        """
        生成话题分布报告
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            报告字典
        """
        return self.analyzer.generate_topic_report(analysis_result)
    
    def export_visualization_data(self, analysis_result: TopicDistributionResult) -> Dict[str, Any]:
        """
        导出可视化数据
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            可视化数据字典
        """
        return self.analyzer.export_visualization_data(analysis_result)
    
    def save_analysis_result(self, 
                           analysis_result: TopicDistributionResult,
                           output_path: str) -> bool:
        """
        保存分析结果到文件
        
        Args:
            analysis_result: 分析结果
            output_path: 输出文件路径
            
        Returns:
            是否保存成功
        """
        try:
            report = self.generate_report(analysis_result)
            visualization_data = self.export_visualization_data(analysis_result)
            
            output_data = {
                "report": report,
                "visualization": visualization_data,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "analyzer_version": "1.0.0",
                    "total_articles": analysis_result.total_articles,
                    "total_topics": analysis_result.total_topics
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"分析结果已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return False
    
    def get_topic_details(self, 
                         analysis_result: TopicDistributionResult,
                         topic_name: str) -> Optional[Dict[str, Any]]:
        """
        获取特定话题的详细信息
        
        Args:
            analysis_result: 分析结果
            topic_name: 话题名称
            
        Returns:
            话题详细信息
        """
        if topic_name not in analysis_result.topic_distribution:
            return None
        
        topic_info = analysis_result.topic_distribution[topic_name]
        
        return {
            "basic_info": {
                "name": topic_info.name,
                "count": topic_info.count,
                "percentage": topic_info.percentage,
                "avg_score": topic_info.avg_score,
                "confidence": topic_info.confidence,
                "trend": topic_info.recent_trend
            },
            "keywords": topic_info.keywords,
            "articles": [
                {
                    "title": article.title,
                    "url": article.url,
                    "published_time": article.published_time,
                    "content_preview": article.content[:200] if article.content else ""
                }
                for article in topic_info.articles[:10]  # 最多返回10篇文章
            ],
            "correlations": analysis_result.topic_correlations.get(topic_name, {})
        }
    
    def compare_time_periods(self, 
                           period1_results: List[CombinedFilterResult],
                           period2_results: List[CombinedFilterResult],
                           period1_name: str = "Period 1",
                           period2_name: str = "Period 2") -> Dict[str, Any]:
        """
        比较两个时间段的话题分布
        
        Args:
            period1_results: 第一个时间段的结果
            period2_results: 第二个时间段的结果
            period1_name: 第一个时间段名称
            period2_name: 第二个时间段名称
            
        Returns:
            比较结果
        """
        # 分析两个时间段
        analysis1 = self.analyzer.analyze_topic_distribution(period1_results)
        analysis2 = self.analyzer.analyze_topic_distribution(period2_results)
        
        # 计算变化
        topic_changes = {}
        all_topics = set(analysis1.topic_distribution.keys()) | set(analysis2.topic_distribution.keys())
        
        for topic in all_topics:
            info1 = analysis1.topic_distribution.get(topic)
            info2 = analysis2.topic_distribution.get(topic)
            
            if info1 and info2:
                # 两个时期都存在
                change = {
                    "status": "existing",
                    "count_change": info2.count - info1.count,
                    "percentage_change": info2.percentage - info1.percentage,
                    "score_change": info2.avg_score - info1.avg_score
                }
            elif info2 and not info1:
                # 新出现的话题
                change = {
                    "status": "new",
                    "count_change": info2.count,
                    "percentage_change": info2.percentage,
                    "score_change": info2.avg_score
                }
            elif info1 and not info2:
                # 消失的话题
                change = {
                    "status": "disappeared",
                    "count_change": -info1.count,
                    "percentage_change": -info1.percentage,
                    "score_change": -info1.avg_score
                }
            
            topic_changes[topic] = change
        
        return {
            "period1": {
                "name": period1_name,
                "total_articles": analysis1.total_articles,
                "total_topics": analysis1.total_topics,
                "diversity_score": analysis1.diversity_score
            },
            "period2": {
                "name": period2_name,
                "total_articles": analysis2.total_articles,
                "total_topics": analysis2.total_topics,
                "diversity_score": analysis2.diversity_score
            },
            "changes": {
                "topic_changes": topic_changes,
                "diversity_change": analysis2.diversity_score - analysis1.diversity_score,
                "topic_count_change": analysis2.total_topics - analysis1.total_topics,
                "article_count_change": analysis2.total_articles - analysis1.total_articles
            },
            "summary": {
                "new_topics": [t for t, c in topic_changes.items() if c["status"] == "new"],
                "disappeared_topics": [t for t, c in topic_changes.items() if c["status"] == "disappeared"],
                "growing_topics": [t for t, c in topic_changes.items() 
                                 if c["status"] == "existing" and c["percentage_change"] > 5],
                "declining_topics": [t for t, c in topic_changes.items() 
                                   if c["status"] == "existing" and c["percentage_change"] < -5]
            }
        }
    
    def _generate_cache_key(self, results: List[CombinedFilterResult], suffix: str = "") -> str:
        """
        生成缓存键
        
        Args:
            results: 筛选结果列表
            suffix: 后缀
            
        Returns:
            缓存键
        """
        # 使用文章数量和标题哈希生成缓存键
        import hashlib
        
        content = f"{len(results)}_"
        if results:
            # 取前10篇文章的标题生成哈希
            titles = [r.article.title for r in results[:10]]
            content += "_".join(titles)
        
        hash_obj = hashlib.md5(content.encode('utf-8'))
        cache_key = f"topic_distribution_{hash_obj.hexdigest()}"
        
        if suffix:
            cache_key += f"_{suffix}"
        
        return cache_key
    
    def clear_cache(self) -> bool:
        """
        清除相关缓存
        
        Returns:
            是否清除成功
        """
        try:
            # 清除所有以topic_distribution开头的缓存
            self.cache_manager.clear_pattern("topic_distribution_*")
            logger.info("话题分布分析缓存已清除")
            return True
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")
            return False