"""
文章标签生成器
"""
import logging
from typing import List, Dict, Optional, Tuple
from ..models.news import NewsArticle
from .base import KeywordMatch, KeywordFilterResult, AIFilterResult, ArticleTag

logger = logging.getLogger(__name__)


class TagGenerator:
    """文章标签生成器"""
    
    def __init__(self, 
                 min_tag_score: float = 0.2,
                 max_tags_per_article: int = 5,
                 primary_tag_threshold: float = 0.5):
        """
        初始化标签生成器
        
        Args:
            min_tag_score: 最小标签评分阈值
            max_tags_per_article: 每篇文章最大标签数
            primary_tag_threshold: 主要标签阈值
        """
        self.min_tag_score = min_tag_score
        self.max_tags_per_article = max_tags_per_article
        self.primary_tag_threshold = primary_tag_threshold
    
    def generate_tags_from_keyword_result(self, 
                                        keyword_result: KeywordFilterResult) -> List[ArticleTag]:
        """
        从关键词筛选结果生成标签
        
        Args:
            keyword_result: 关键词筛选结果
            
        Returns:
            生成的标签列表
        """
        if not keyword_result.category_scores:
            return []
        
        tags = []
        
        # 基于category_scores生成标签
        for category, score in keyword_result.category_scores.items():
            if score >= self.min_tag_score:
                # 计算置信度：基于该分类的关键词匹配情况
                confidence = self._calculate_tag_confidence(
                    category, keyword_result.matched_keywords, score
                )
                
                tag = ArticleTag(
                    name=category,
                    score=score,
                    confidence=confidence,
                    source="keyword"
                )
                tags.append(tag)
        
        # 按评分排序并限制数量
        tags.sort(key=lambda t: t.score, reverse=True)
        tags = tags[:self.max_tags_per_article]
        
        logger.debug(f"Generated {len(tags)} tags from keyword result for article: {keyword_result.article.title[:50]}")
        
        return tags
    
    def enhance_tags_with_ai_result(self, 
                                  existing_tags: List[ArticleTag],
                                  ai_result: AIFilterResult) -> List[ArticleTag]:
        """
        使用AI筛选结果增强标签
        
        Args:
            existing_tags: 现有标签列表
            ai_result: AI筛选结果
            
        Returns:
            增强后的标签列表
        """
        enhanced_tags = existing_tags.copy()
        
        # 如果AI结果包含标签信息，进行融合
        if hasattr(ai_result.evaluation, 'tags') and ai_result.evaluation.tags:
            ai_tags = self._convert_ai_tags_to_article_tags(ai_result.evaluation.tags)
            enhanced_tags = self._merge_tags(enhanced_tags, ai_tags)
        
        # 根据AI评分调整现有标签的置信度
        for tag in enhanced_tags:
            if tag.source == "keyword":
                # 基于AI总分调整置信度
                ai_confidence_boost = min(0.2, ai_result.evaluation.total_score / 150.0)
                tag.confidence = min(1.0, tag.confidence + ai_confidence_boost)
        
        return enhanced_tags
    
    def _calculate_tag_confidence(self, 
                                category: str, 
                                matches: List[KeywordMatch], 
                                category_score: float) -> float:
        """
        计算标签置信度
        
        Args:
            category: 分类名称
            matches: 关键词匹配列表
            category_score: 分类评分
            
        Returns:
            置信度值 (0-1)
        """
        # 统计该分类的匹配数量
        category_matches = [m for m in matches if m.category == category]
        match_count = len(category_matches)
        
        if match_count == 0:
            return 0.0
        
        # 基础置信度：基于分类评分
        base_confidence = min(0.8, category_score)
        
        # 匹配数量加成
        match_bonus = min(0.2, match_count * 0.05)
        
        # 关键词多样性加成
        unique_keywords = set(m.keyword.lower() for m in category_matches)
        diversity_bonus = min(0.1, len(unique_keywords) * 0.02)
        
        total_confidence = base_confidence + match_bonus + diversity_bonus
        return min(1.0, total_confidence)
    
    def _convert_ai_tags_to_article_tags(self, ai_tags: List[str]) -> List[ArticleTag]:
        """
        将AI生成的标签转换为ArticleTag对象
        
        Args:
            ai_tags: AI生成的标签字符串列表
            
        Returns:
            ArticleTag对象列表
        """
        article_tags = []
        
        for tag_str in ai_tags:
            # AI标签的评分基于其在列表中的位置（前面的更重要）
            position_score = max(0.3, 1.0 - (ai_tags.index(tag_str) * 0.1))
            
            tag = ArticleTag(
                name=tag_str.lower().replace(' ', '_'),
                score=position_score,
                confidence=0.7,  # AI标签的基础置信度
                source="ai"
            )
            article_tags.append(tag)
        
        return article_tags
    
    def _merge_tags(self, 
                   keyword_tags: List[ArticleTag], 
                   ai_tags: List[ArticleTag]) -> List[ArticleTag]:
        """
        合并关键词标签和AI标签
        
        Args:
            keyword_tags: 关键词生成的标签
            ai_tags: AI生成的标签
            
        Returns:
            合并后的标签列表
        """
        merged_tags = {}
        
        # 添加关键词标签
        for tag in keyword_tags:
            merged_tags[tag.name] = tag
        
        # 合并AI标签
        for ai_tag in ai_tags:
            if ai_tag.name in merged_tags:
                # 如果标签已存在，融合评分和置信度
                existing_tag = merged_tags[ai_tag.name]
                merged_tags[ai_tag.name] = ArticleTag(
                    name=ai_tag.name,
                    score=max(existing_tag.score, ai_tag.score),
                    confidence=(existing_tag.confidence + ai_tag.confidence) / 2,
                    source="keyword+ai"
                )
            else:
                # 新的AI标签
                merged_tags[ai_tag.name] = ai_tag
        
        # 转换为列表并排序
        result_tags = list(merged_tags.values())
        result_tags.sort(key=lambda t: t.score, reverse=True)
        
        return result_tags[:self.max_tags_per_article]
    
    def get_primary_tag(self, tags: List[ArticleTag]) -> Optional[ArticleTag]:
        """
        获取主要标签
        
        Args:
            tags: 标签列表
            
        Returns:
            主要标签，如果没有符合条件的标签则返回None
        """
        if not tags:
            return None
        
        # 找到评分最高的标签
        primary_tag = max(tags, key=lambda t: t.score)
        
        # 检查是否达到主要标签阈值
        if primary_tag.score >= self.primary_tag_threshold:
            return primary_tag
        
        return None
    
    def filter_tags_by_confidence(self, 
                                 tags: List[ArticleTag], 
                                 min_confidence: float = 0.5) -> List[ArticleTag]:
        """
        根据置信度过滤标签
        
        Args:
            tags: 标签列表
            min_confidence: 最小置信度阈值
            
        Returns:
            过滤后的标签列表
        """
        return [tag for tag in tags if tag.confidence >= min_confidence]


class TagStatistics:
    """标签统计信息"""
    
    def __init__(self):
        self.tag_counts: Dict[str, int] = {}
        self.tag_scores: Dict[str, List[float]] = {}
    
    def add_article_tags(self, tags: List[ArticleTag]):
        """添加文章标签到统计中"""
        for tag in tags:
            # 更新计数
            self.tag_counts[tag.name] = self.tag_counts.get(tag.name, 0) + 1
            
            # 更新评分列表
            if tag.name not in self.tag_scores:
                self.tag_scores[tag.name] = []
            self.tag_scores[tag.name].append(tag.score)
    
    def get_tag_distribution(self) -> Dict[str, Dict[str, float]]:
        """获取标签分布统计"""
        distribution = {}
        
        total_articles = sum(self.tag_counts.values())
        if total_articles == 0:
            return distribution
        
        for tag_name, count in self.tag_counts.items():
            scores = self.tag_scores[tag_name]
            distribution[tag_name] = {
                'count': count,
                'percentage': (count / total_articles) * 100,
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'max_score': max(scores) if scores else 0,
                'min_score': min(scores) if scores else 0
            }
        
        return distribution
    
    def get_most_common_tags(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """获取最常见的标签"""
        return sorted(self.tag_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    
    def reset(self):
        """重置统计信息"""
        self.tag_counts.clear()
        self.tag_scores.clear()
