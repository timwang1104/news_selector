"""
标签统计分析器
"""
import logging
import math
from typing import List, Dict, Optional, Tuple
from collections import Counter
from .base import CombinedFilterResult, ArticleTag, TagStatistics

logger = logging.getLogger(__name__)


class TagAnalyzer:
    """标签统计分析器"""
    
    def __init__(self, tag_limits: Dict[str, int] = None):
        """
        初始化标签分析器
        
        Args:
            tag_limits: 标签数量限制配置
        """
        self.tag_limits = tag_limits or {}
    
    def analyze_results(self, results: List[CombinedFilterResult]) -> TagStatistics:
        """
        分析筛选结果的标签统计
        
        Args:
            results: 筛选结果列表
            
        Returns:
            标签统计信息
        """
        if not results:
            return TagStatistics()
        
        # 收集标签信息
        tag_distribution = self._calculate_tag_distribution(results)
        tag_fill_ratios = self._calculate_fill_ratios(tag_distribution)
        
        # 分析代表性
        underrepresented_tags = self._find_underrepresented_tags(tag_fill_ratios)
        overrepresented_tags = self._find_overrepresented_tags(tag_fill_ratios)
        
        # 计算文章标签统计
        tagged_count, untagged_count = self._count_tagged_articles(results)
        avg_tags_per_article = self._calculate_average_tags_per_article(results)
        
        # 计算多样性评分
        diversity_score = self._calculate_diversity_score(tag_distribution)
        
        return TagStatistics(
            tag_distribution=tag_distribution,
            tag_fill_ratios=tag_fill_ratios,
            underrepresented_tags=underrepresented_tags,
            overrepresented_tags=overrepresented_tags,
            total_tagged_articles=tagged_count,
            untagged_articles=untagged_count,
            average_tags_per_article=avg_tags_per_article,
            tag_diversity_score=diversity_score
        )
    
    def _calculate_tag_distribution(self, results: List[CombinedFilterResult]) -> Dict[str, int]:
        """计算标签分布"""
        tag_counts = Counter()
        
        for result in results:
            if result.tags:
                # 使用主要标签进行统计
                primary_tag = max(result.tags, key=lambda t: t.score)
                tag_counts[primary_tag.name] += 1
        
        return dict(tag_counts)
    
    def _calculate_fill_ratios(self, tag_distribution: Dict[str, int]) -> Dict[str, float]:
        """计算标签填充比例"""
        fill_ratios = {}
        
        for tag_name, count in tag_distribution.items():
            limit = self.tag_limits.get(tag_name, 0)
            if limit > 0:
                fill_ratios[tag_name] = count / limit
            else:
                fill_ratios[tag_name] = 1.0  # 无限制的标签视为100%填充
        
        # 为有限制但未出现的标签添加0%填充
        for tag_name, limit in self.tag_limits.items():
            if tag_name not in fill_ratios:
                fill_ratios[tag_name] = 0.0
        
        return fill_ratios
    
    def _find_underrepresented_tags(self, fill_ratios: Dict[str, float], 
                                   threshold: float = 0.5) -> List[str]:
        """找出代表性不足的标签"""
        return [
            tag_name for tag_name, ratio in fill_ratios.items()
            if ratio < threshold
        ]
    
    def _find_overrepresented_tags(self, fill_ratios: Dict[str, float], 
                                  threshold: float = 0.9) -> List[str]:
        """找出过度代表的标签"""
        return [
            tag_name for tag_name, ratio in fill_ratios.items()
            if ratio > threshold
        ]
    
    def _count_tagged_articles(self, results: List[CombinedFilterResult]) -> Tuple[int, int]:
        """统计有标签和无标签的文章数量"""
        tagged_count = 0
        untagged_count = 0
        
        for result in results:
            if result.tags:
                tagged_count += 1
            else:
                untagged_count += 1
        
        return tagged_count, untagged_count
    
    def _calculate_average_tags_per_article(self, results: List[CombinedFilterResult]) -> float:
        """计算每篇文章的平均标签数"""
        if not results:
            return 0.0
        
        total_tags = sum(len(result.tags) if result.tags else 0 for result in results)
        return total_tags / len(results)
    
    def _calculate_diversity_score(self, tag_distribution: Dict[str, int]) -> float:
        """
        计算标签多样性评分
        使用香农熵来衡量分布的均匀性
        """
        if not tag_distribution:
            return 0.0
        
        total_count = sum(tag_distribution.values())
        if total_count == 0:
            return 0.0
        
        # 计算香农熵
        entropy = 0.0
        for count in tag_distribution.values():
            if count > 0:
                probability = count / total_count
                entropy -= probability * math.log2(probability)
        
        # 归一化到0-1范围
        max_entropy = math.log2(len(tag_distribution)) if len(tag_distribution) > 1 else 1.0
        diversity_score = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return diversity_score
    
    def generate_balance_report(self, statistics: TagStatistics) -> Dict[str, any]:
        """
        生成标签平衡报告
        
        Args:
            statistics: 标签统计信息
            
        Returns:
            平衡报告字典
        """
        total_articles = statistics.total_tagged_articles + statistics.untagged_articles
        
        report = {
            "summary": {
                "total_articles": total_articles,
                "tagged_articles": statistics.total_tagged_articles,
                "untagged_articles": statistics.untagged_articles,
                "tag_coverage": (statistics.total_tagged_articles / total_articles * 100) if total_articles > 0 else 0,
                "average_tags_per_article": statistics.average_tags_per_article,
                "diversity_score": statistics.tag_diversity_score * 100,  # 转换为百分比
                "unique_tags": len(statistics.tag_distribution)
            },
            "distribution": {
                "tag_counts": statistics.tag_distribution,
                "fill_ratios": {k: v * 100 for k, v in statistics.tag_fill_ratios.items()},  # 转换为百分比
                "underrepresented": statistics.underrepresented_tags,
                "overrepresented": statistics.overrepresented_tags
            },
            "recommendations": self._generate_recommendations(statistics)
        }
        
        return report
    
    def _generate_recommendations(self, statistics: TagStatistics) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 检查标签覆盖率
        total_articles = statistics.total_tagged_articles + statistics.untagged_articles
        if total_articles > 0:
            coverage = statistics.total_tagged_articles / total_articles
            if coverage < 0.8:
                recommendations.append(f"标签覆盖率较低({coverage*100:.1f}%)，建议优化标签生成策略")
        
        # 检查多样性
        if statistics.tag_diversity_score < 0.6:
            recommendations.append(f"标签分布不够均匀(多样性评分:{statistics.tag_diversity_score*100:.1f}%)，建议调整平衡策略")
        
        # 检查代表性不足的标签
        if statistics.underrepresented_tags:
            recommendations.append(f"以下标签代表性不足: {', '.join(statistics.underrepresented_tags[:5])}")
        
        # 检查过度代表的标签
        if statistics.overrepresented_tags:
            recommendations.append(f"以下标签可能过度集中: {', '.join(statistics.overrepresented_tags[:3])}")
        
        # 检查平均标签数
        if statistics.average_tags_per_article < 1.0:
            recommendations.append("每篇文章平均标签数较少，建议降低标签生成阈值")
        elif statistics.average_tags_per_article > 3.0:
            recommendations.append("每篇文章平均标签数较多，建议提高标签生成阈值")
        
        return recommendations
    
    def compare_distributions(self, 
                            current_stats: TagStatistics,
                            target_distribution: Dict[str, int]) -> Dict[str, any]:
        """
        比较当前分布与目标分布
        
        Args:
            current_stats: 当前标签统计
            target_distribution: 目标分布
            
        Returns:
            比较结果
        """
        comparison = {
            "deviations": {},
            "total_deviation": 0.0,
            "balance_score": 0.0
        }
        
        total_current = sum(current_stats.tag_distribution.values())
        total_target = sum(target_distribution.values())
        
        if total_current == 0 or total_target == 0:
            return comparison
        
        total_deviation = 0.0
        
        for tag_name, target_count in target_distribution.items():
            current_count = current_stats.tag_distribution.get(tag_name, 0)
            
            # 计算比例偏差
            target_ratio = target_count / total_target
            current_ratio = current_count / total_current
            deviation = abs(current_ratio - target_ratio)
            
            comparison["deviations"][tag_name] = {
                "target_count": target_count,
                "current_count": current_count,
                "target_ratio": target_ratio * 100,
                "current_ratio": current_ratio * 100,
                "deviation": deviation * 100
            }
            
            total_deviation += deviation
        
        comparison["total_deviation"] = total_deviation * 100
        comparison["balance_score"] = max(0, 100 - total_deviation * 100)
        
        return comparison
    
    def export_detailed_report(self, 
                              results: List[CombinedFilterResult],
                              include_articles: bool = False) -> Dict[str, any]:
        """
        导出详细的标签分析报告
        
        Args:
            results: 筛选结果列表
            include_articles: 是否包含文章详情
            
        Returns:
            详细报告
        """
        statistics = self.analyze_results(results)
        balance_report = self.generate_balance_report(statistics)
        
        detailed_report = {
            "analysis_timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            )),
            "statistics": statistics,
            "balance_report": balance_report,
            "tag_limits": self.tag_limits
        }
        
        if include_articles:
            detailed_report["articles_by_tag"] = self._group_articles_by_tag(results)
        
        return detailed_report
    
    def _group_articles_by_tag(self, results: List[CombinedFilterResult]) -> Dict[str, List[Dict]]:
        """按标签分组文章"""
        articles_by_tag = {}
        
        for result in results:
            if result.tags:
                primary_tag = max(result.tags, key=lambda t: t.score)
                tag_name = primary_tag.name
            else:
                tag_name = "untagged"
            
            if tag_name not in articles_by_tag:
                articles_by_tag[tag_name] = []
            
            article_info = {
                "title": result.article.title,
                "url": result.article.url,
                "final_score": result.final_score,
                "selected": result.selected,
                "tags": [{"name": t.name, "score": t.score, "confidence": t.confidence} 
                        for t in result.tags] if result.tags else []
            }
            
            articles_by_tag[tag_name].append(article_info)
        
        return articles_by_tag
