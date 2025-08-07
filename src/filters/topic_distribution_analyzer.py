"""话题分布分析器

基于现有的标签分析功能，提供更深入的话题分布分析，包括：
- 话题分布统计
- 话题趋势分析
- 话题关联性分析
- 话题热度评估
"""

import logging
import math
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass

from .base import CombinedFilterResult, ArticleTag
from ..models.news import NewsArticle

logger = logging.getLogger(__name__)


@dataclass
class TopicInfo:
    """话题信息"""
    name: str                    # 话题名称
    count: int                   # 文章数量
    percentage: float            # 占比
    avg_score: float            # 平均评分
    confidence: float           # 置信度
    keywords: List[str]         # 关键词
    recent_trend: str           # 近期趋势 (up/down/stable)
    articles: List[NewsArticle] # 相关文章


@dataclass
class TopicDistributionResult:
    """话题分布分析结果"""
    total_articles: int                    # 总文章数
    total_topics: int                     # 话题总数
    topic_distribution: Dict[str, TopicInfo]  # 话题分布
    diversity_score: float                # 多样性评分
    concentration_index: float            # 集中度指数
    top_topics: List[TopicInfo]          # 热门话题
    emerging_topics: List[TopicInfo]     # 新兴话题
    declining_topics: List[TopicInfo]    # 衰落话题
    topic_correlations: Dict[str, Dict[str, float]]  # 话题关联性
    analysis_timestamp: datetime         # 分析时间戳


class TopicDistributionAnalyzer:
    """话题分布分析器"""
    
    def __init__(self, min_topic_threshold: float = 0.01, 
                 correlation_threshold: float = 0.3):
        """
        初始化话题分布分析器
        
        Args:
            min_topic_threshold: 最小话题阈值（低于此比例的话题将被归类为"其他"）
            correlation_threshold: 话题关联性阈值
        """
        self.min_topic_threshold = min_topic_threshold
        self.correlation_threshold = correlation_threshold
    
    def analyze_topic_distribution(self, 
                                 results: List[CombinedFilterResult],
                                 historical_data: Optional[List[CombinedFilterResult]] = None) -> TopicDistributionResult:
        """
        分析话题分布
        
        Args:
            results: 当前筛选结果
            historical_data: 历史数据（用于趋势分析）
            
        Returns:
            话题分布分析结果
        """
        if not results:
            return self._create_empty_result()
        
        # 基础统计
        topic_stats = self._calculate_basic_statistics(results)
        
        # 计算话题信息
        topic_distribution = self._build_topic_distribution(results, topic_stats)
        
        # 计算多样性和集中度
        diversity_score = self._calculate_diversity_score(topic_stats)
        concentration_index = self._calculate_concentration_index(topic_stats)
        
        # 识别热门、新兴和衰落话题
        top_topics = self._identify_top_topics(topic_distribution)
        emerging_topics, declining_topics = self._analyze_topic_trends(
            topic_distribution, historical_data
        )
        
        # 计算话题关联性
        topic_correlations = self._calculate_topic_correlations(results)
        
        return TopicDistributionResult(
            total_articles=len(results),
            total_topics=len(topic_distribution),
            topic_distribution=topic_distribution,
            diversity_score=diversity_score,
            concentration_index=concentration_index,
            top_topics=top_topics,
            emerging_topics=emerging_topics,
            declining_topics=declining_topics,
            topic_correlations=topic_correlations,
            analysis_timestamp=datetime.now()
        )
    
    def _create_empty_result(self) -> TopicDistributionResult:
        """创建空的分析结果"""
        return TopicDistributionResult(
            total_articles=0,
            total_topics=0,
            topic_distribution={},
            diversity_score=0.0,
            concentration_index=0.0,
            top_topics=[],
            emerging_topics=[],
            declining_topics=[],
            topic_correlations={},
            analysis_timestamp=datetime.now()
        )
    
    def _calculate_basic_statistics(self, results: List[CombinedFilterResult]) -> Dict[str, Dict]:
        """计算基础话题统计"""
        topic_stats = defaultdict(lambda: {
            'count': 0,
            'scores': [],
            'confidences': [],
            'articles': [],
            'keywords': set()
        })
        
        for result in results:
            if result.tags:
                # 使用主要标签作为话题
                primary_tag = max(result.tags, key=lambda t: t.score)
                topic_name = primary_tag.name
                
                topic_stats[topic_name]['count'] += 1
                topic_stats[topic_name]['scores'].append(primary_tag.score)
                topic_stats[topic_name]['confidences'].append(primary_tag.confidence)
                topic_stats[topic_name]['articles'].append(result.article)
                
                # 提取关键词（从文章标题和内容中）
                keywords = self._extract_keywords_from_article(result.article)
                topic_stats[topic_name]['keywords'].update(keywords)
            else:
                # 无标签文章归类为"未分类"
                topic_stats['未分类']['count'] += 1
                topic_stats['未分类']['scores'].append(0.0)
                topic_stats['未分类']['confidences'].append(0.0)
                topic_stats['未分类']['articles'].append(result.article)
        
        return dict(topic_stats)
    
    def _extract_keywords_from_article(self, article: NewsArticle) -> List[str]:
        """从文章中提取关键词"""
        # 简单的关键词提取逻辑
        # 在实际应用中，可以使用更复杂的NLP技术
        keywords = []
        
        # 从标题中提取
        title_words = article.title.split()
        keywords.extend([word for word in title_words if len(word) > 2])
        
        # 从内容中提取（取前100个字符）
        if article.content:
            content_preview = article.content[:100]
            content_words = content_preview.split()
            keywords.extend([word for word in content_words if len(word) > 2])
        
        return keywords[:10]  # 限制关键词数量
    
    def _build_topic_distribution(self, 
                                results: List[CombinedFilterResult],
                                topic_stats: Dict[str, Dict]) -> Dict[str, TopicInfo]:
        """构建话题分布信息"""
        total_articles = len(results)
        topic_distribution = {}
        
        for topic_name, stats in topic_stats.items():
            count = stats['count']
            percentage = (count / total_articles) * 100 if total_articles > 0 else 0
            
            # 计算平均评分和置信度
            avg_score = sum(stats['scores']) / len(stats['scores']) if stats['scores'] else 0.0
            avg_confidence = sum(stats['confidences']) / len(stats['confidences']) if stats['confidences'] else 0.0
            
            # 过滤小话题
            if percentage < self.min_topic_threshold * 100:
                continue
            
            topic_info = TopicInfo(
                name=topic_name,
                count=count,
                percentage=percentage,
                avg_score=avg_score,
                confidence=avg_confidence,
                keywords=list(stats['keywords'])[:10],  # 取前10个关键词
                recent_trend='stable',  # 默认稳定，需要历史数据才能计算趋势
                articles=stats['articles']
            )
            
            topic_distribution[topic_name] = topic_info
        
        return topic_distribution
    
    def _calculate_diversity_score(self, topic_stats: Dict[str, Dict]) -> float:
        """计算话题多样性评分（使用香农熵）"""
        if not topic_stats:
            return 0.0
        
        total_count = sum(stats['count'] for stats in topic_stats.values())
        if total_count == 0:
            return 0.0
        
        entropy = 0.0
        for stats in topic_stats.values():
            if stats['count'] > 0:
                probability = stats['count'] / total_count
                entropy -= probability * math.log2(probability)
        
        # 归一化到0-1范围
        max_entropy = math.log2(len(topic_stats)) if len(topic_stats) > 1 else 1.0
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return diversity_score
    
    def _calculate_concentration_index(self, topic_stats: Dict[str, Dict]) -> float:
        """计算话题集中度指数（赫芬达尔指数）"""
        if not topic_stats:
            return 0.0
        
        total_count = sum(stats['count'] for stats in topic_stats.values())
        if total_count == 0:
            return 0.0
        
        hhi = sum((stats['count'] / total_count) ** 2 for stats in topic_stats.values())
        return hhi
    
    def _identify_top_topics(self, topic_distribution: Dict[str, TopicInfo]) -> List[TopicInfo]:
        """识别热门话题"""
        # 按文章数量和平均评分综合排序
        topics = list(topic_distribution.values())
        topics.sort(key=lambda t: (t.count * t.avg_score), reverse=True)
        return topics[:5]  # 返回前5个热门话题
    
    def _analyze_topic_trends(self, 
                            current_distribution: Dict[str, TopicInfo],
                            historical_data: Optional[List[CombinedFilterResult]]) -> Tuple[List[TopicInfo], List[TopicInfo]]:
        """分析话题趋势"""
        emerging_topics = []
        declining_topics = []
        
        if not historical_data:
            return emerging_topics, declining_topics
        
        # 计算历史话题分布
        historical_stats = self._calculate_basic_statistics(historical_data)
        historical_distribution = self._build_topic_distribution(historical_data, historical_stats)
        
        # 比较当前和历史分布
        for topic_name, current_info in current_distribution.items():
            if topic_name in historical_distribution:
                historical_info = historical_distribution[topic_name]
                growth_rate = (current_info.percentage - historical_info.percentage) / historical_info.percentage
                
                if growth_rate > 0.5:  # 增长超过50%
                    current_info.recent_trend = 'up'
                    emerging_topics.append(current_info)
                elif growth_rate < -0.3:  # 下降超过30%
                    current_info.recent_trend = 'down'
                    declining_topics.append(current_info)
                else:
                    current_info.recent_trend = 'stable'
            else:
                # 新出现的话题
                current_info.recent_trend = 'up'
                emerging_topics.append(current_info)
        
        return emerging_topics[:3], declining_topics[:3]  # 返回前3个
    
    def _calculate_topic_correlations(self, results: List[CombinedFilterResult]) -> Dict[str, Dict[str, float]]:
        """计算话题间的关联性"""
        correlations = defaultdict(lambda: defaultdict(float))
        
        # 构建话题共现矩阵
        topic_cooccurrence = defaultdict(lambda: defaultdict(int))
        topic_counts = defaultdict(int)
        
        for result in results:
            if result.tags and len(result.tags) > 1:
                # 获取所有标签对应的话题
                topics = [tag.name for tag in result.tags if tag.score > 0.3]
                
                # 计算话题共现
                for i, topic1 in enumerate(topics):
                    topic_counts[topic1] += 1
                    for j, topic2 in enumerate(topics):
                        if i != j:
                            topic_cooccurrence[topic1][topic2] += 1
        
        # 计算相关系数
        for topic1, cooccur_dict in topic_cooccurrence.items():
            for topic2, cooccur_count in cooccur_dict.items():
                if topic_counts[topic1] > 0 and topic_counts[topic2] > 0:
                    # 使用Jaccard相似度
                    correlation = cooccur_count / (topic_counts[topic1] + topic_counts[topic2] - cooccur_count)
                    if correlation >= self.correlation_threshold:
                        correlations[topic1][topic2] = correlation
        
        return dict(correlations)
    
    def generate_topic_report(self, analysis_result: TopicDistributionResult) -> Dict[str, Any]:
        """生成话题分布报告"""
        report = {
            "summary": {
                "total_articles": analysis_result.total_articles,
                "total_topics": analysis_result.total_topics,
                "diversity_score": round(analysis_result.diversity_score * 100, 2),
                "concentration_index": round(analysis_result.concentration_index, 3),
                "analysis_time": analysis_result.analysis_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            },
            "topic_distribution": {
                topic_name: {
                    "count": info.count,
                    "percentage": round(info.percentage, 2),
                    "avg_score": round(info.avg_score, 3),
                    "confidence": round(info.confidence, 3),
                    "trend": info.recent_trend,
                    "keywords": info.keywords[:5]  # 显示前5个关键词
                }
                for topic_name, info in analysis_result.topic_distribution.items()
            },
            "insights": {
                "top_topics": [
                    {
                        "name": topic.name,
                        "count": topic.count,
                        "percentage": round(topic.percentage, 2)
                    }
                    for topic in analysis_result.top_topics
                ],
                "emerging_topics": [
                    {
                        "name": topic.name,
                        "count": topic.count,
                        "trend": topic.recent_trend
                    }
                    for topic in analysis_result.emerging_topics
                ],
                "declining_topics": [
                    {
                        "name": topic.name,
                        "count": topic.count,
                        "trend": topic.recent_trend
                    }
                    for topic in analysis_result.declining_topics
                ]
            },
            "correlations": analysis_result.topic_correlations,
            "recommendations": self._generate_recommendations(analysis_result)
        }
        
        return report
    
    def _generate_recommendations(self, analysis_result: TopicDistributionResult) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        # 多样性建议
        if analysis_result.diversity_score < 0.6:
            recommendations.append(f"话题多样性较低({analysis_result.diversity_score*100:.1f}%)，建议扩大信息源覆盖范围")
        
        # 集中度建议
        if analysis_result.concentration_index > 0.5:
            recommendations.append(f"话题过于集中(集中度指数:{analysis_result.concentration_index:.3f})，建议平衡不同话题的关注度")
        
        # 新兴话题建议
        if analysis_result.emerging_topics:
            emerging_names = [t.name for t in analysis_result.emerging_topics[:3]]
            recommendations.append(f"关注新兴话题: {', '.join(emerging_names)}")
        
        # 衰落话题建议
        if analysis_result.declining_topics:
            declining_names = [t.name for t in analysis_result.declining_topics[:2]]
            recommendations.append(f"以下话题热度下降: {', '.join(declining_names)}，可考虑调整关注策略")
        
        # 话题数量建议
        if analysis_result.total_topics < 3:
            recommendations.append("话题类别较少，建议增加筛选标签的多样性")
        elif analysis_result.total_topics > 15:
            recommendations.append("话题类别过多，建议合并相似话题或提高筛选阈值")
        
        return recommendations
    
    def export_visualization_data(self, analysis_result: TopicDistributionResult) -> Dict[str, Any]:
        """导出可视化数据"""
        # 饼图数据
        pie_data = {
            "labels": list(analysis_result.topic_distribution.keys()),
            "values": [info.count for info in analysis_result.topic_distribution.values()],
            "colors": self._generate_colors(len(analysis_result.topic_distribution))
        }
        
        # 趋势数据
        trend_data = {
            "emerging": [
                {"name": t.name, "count": t.count, "percentage": t.percentage}
                for t in analysis_result.emerging_topics
            ],
            "declining": [
                {"name": t.name, "count": t.count, "percentage": t.percentage}
                for t in analysis_result.declining_topics
            ]
        }
        
        # 关联性网络数据
        network_data = {
            "nodes": [
                {"id": topic_name, "size": info.count, "group": info.recent_trend}
                for topic_name, info in analysis_result.topic_distribution.items()
            ],
            "links": [
                {"source": topic1, "target": topic2, "weight": correlation}
                for topic1, correlations in analysis_result.topic_correlations.items()
                for topic2, correlation in correlations.items()
            ]
        }
        
        return {
            "pie_chart": pie_data,
            "trend_analysis": trend_data,
            "correlation_network": network_data,
            "summary_stats": {
                "diversity_score": analysis_result.diversity_score,
                "concentration_index": analysis_result.concentration_index,
                "total_topics": analysis_result.total_topics,
                "total_articles": analysis_result.total_articles
            }
        }
    
    def _generate_colors(self, count: int) -> List[str]:
        """生成颜色列表"""
        # 预定义的颜色方案
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
            '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D2B4DE'
        ]
        
        # 如果需要更多颜色，循环使用
        return [colors[i % len(colors)] for i in range(count)]