"""
标签级数量统计和限制管理器
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from .base import ArticleTag, CombinedFilterResult

logger = logging.getLogger(__name__)


@dataclass
class TagLimit:
    """标签数量限制配置"""
    tag_name: str
    max_count: int
    current_count: int = 0
    priority: float = 1.0  # 优先级，用于平衡筛选

    @property
    def remaining_count(self) -> int:
        """剩余可筛选数量"""
        return max(0, self.max_count - self.current_count)
    
    @property
    def is_full(self) -> bool:
        """是否已达到上限"""
        return self.current_count >= self.max_count
    
    @property
    def fill_ratio(self) -> float:
        """填充比例 (0-1)"""
        if self.max_count == 0:
            return 1.0
        return self.current_count / self.max_count


class TagCounter:
    """标签级数量统计和限制管理器"""
    
    def __init__(self, tag_limits: Dict[str, int] = None):
        """
        初始化标签计数器
        
        Args:
            tag_limits: 标签数量限制配置 {tag_name: max_count}
        """
        self.tag_limits: Dict[str, TagLimit] = {}
        self.selected_articles: List[CombinedFilterResult] = []
        
        if tag_limits:
            self.set_tag_limits(tag_limits)
    
    def set_tag_limits(self, tag_limits: Dict[str, int]):
        """
        设置标签数量限制
        
        Args:
            tag_limits: 标签数量限制配置 {tag_name: max_count}
        """
        self.tag_limits.clear()
        for tag_name, max_count in tag_limits.items():
            self.tag_limits[tag_name] = TagLimit(
                tag_name=tag_name,
                max_count=max_count
            )
        
        logger.info(f"Set tag limits for {len(tag_limits)} tags")
    
    def update_tag_priorities(self, priorities: Dict[str, float]):
        """
        更新标签优先级
        
        Args:
            priorities: 标签优先级配置 {tag_name: priority}
        """
        for tag_name, priority in priorities.items():
            if tag_name in self.tag_limits:
                self.tag_limits[tag_name].priority = priority
    
    def can_select_article(self, article_tags: List[ArticleTag]) -> bool:
        """
        检查是否可以选择该文章（基于标签数量限制）
        
        Args:
            article_tags: 文章标签列表
            
        Returns:
            是否可以选择
        """
        if not article_tags:
            return True
        
        # 获取文章的主要标签
        primary_tag = self._get_primary_tag(article_tags)
        if not primary_tag:
            return True
        
        # 检查主要标签是否还有剩余名额
        tag_limit = self.tag_limits.get(primary_tag.name)
        if tag_limit is None:
            return True  # 没有限制的标签可以选择
        
        return not tag_limit.is_full
    
    def add_selected_article(self, result: CombinedFilterResult) -> bool:
        """
        添加已选择的文章，更新计数
        
        Args:
            result: 筛选结果
            
        Returns:
            是否成功添加
        """
        if not result.tags:
            # 没有标签的文章直接添加
            self.selected_articles.append(result)
            return True
        
        # 获取主要标签
        primary_tag = self._get_primary_tag(result.tags)
        if not primary_tag:
            self.selected_articles.append(result)
            return True
        
        # 检查标签限制
        tag_limit = self.tag_limits.get(primary_tag.name)
        if tag_limit is None:
            # 没有限制的标签
            self.selected_articles.append(result)
            return True
        
        if tag_limit.is_full:
            logger.debug(f"Tag '{primary_tag.name}' is full, cannot add article: {result.article.title[:50]}")
            return False
        
        # 更新计数并添加文章
        tag_limit.current_count += 1
        self.selected_articles.append(result)
        
        logger.debug(f"Added article to tag '{primary_tag.name}' ({tag_limit.current_count}/{tag_limit.max_count})")
        return True
    
    def get_tag_status(self) -> Dict[str, Dict[str, any]]:
        """
        获取所有标签的状态信息
        
        Returns:
            标签状态字典
        """
        status = {}
        
        for tag_name, tag_limit in self.tag_limits.items():
            status[tag_name] = {
                'max_count': tag_limit.max_count,
                'current_count': tag_limit.current_count,
                'remaining_count': tag_limit.remaining_count,
                'fill_ratio': tag_limit.fill_ratio,
                'is_full': tag_limit.is_full,
                'priority': tag_limit.priority
            }
        
        return status
    
    def get_underrepresented_tags(self, threshold: float = 0.5) -> List[str]:
        """
        获取代表性不足的标签（填充比例低于阈值）
        
        Args:
            threshold: 填充比例阈值
            
        Returns:
            代表性不足的标签名称列表
        """
        underrepresented = []
        
        for tag_name, tag_limit in self.tag_limits.items():
            if tag_limit.fill_ratio < threshold:
                underrepresented.append(tag_name)
        
        return underrepresented
    
    def get_balanced_selection_priority(self) -> Dict[str, float]:
        """
        获取平衡选择的优先级权重
        
        Returns:
            标签优先级权重字典 {tag_name: weight}
        """
        priorities = {}
        
        for tag_name, tag_limit in self.tag_limits.items():
            if tag_limit.is_full:
                priorities[tag_name] = 0.0
            else:
                # 优先级 = 基础优先级 * (1 - 填充比例) * 剩余名额比例
                remaining_ratio = tag_limit.remaining_count / tag_limit.max_count
                fill_penalty = 1.0 - tag_limit.fill_ratio
                
                priorities[tag_name] = tag_limit.priority * fill_penalty * remaining_ratio
        
        return priorities
    
    def calculate_article_selection_weight(self, article_tags: List[ArticleTag]) -> float:
        """
        计算文章的选择权重（用于平衡筛选）
        
        Args:
            article_tags: 文章标签列表
            
        Returns:
            选择权重
        """
        if not article_tags:
            return 1.0
        
        primary_tag = self._get_primary_tag(article_tags)
        if not primary_tag:
            return 1.0
        
        # 获取标签的平衡优先级
        priorities = self.get_balanced_selection_priority()
        tag_priority = priorities.get(primary_tag.name, 1.0)
        
        # 结合文章标签评分和标签优先级
        article_quality = primary_tag.score
        
        return article_quality * tag_priority
    
    def get_statistics(self) -> Dict[str, any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        total_selected = len(self.selected_articles)
        total_capacity = sum(limit.max_count for limit in self.tag_limits.values())
        
        tag_distribution = {}
        for tag_name, tag_limit in self.tag_limits.items():
            tag_distribution[tag_name] = {
                'count': tag_limit.current_count,
                'percentage': (tag_limit.current_count / total_selected * 100) if total_selected > 0 else 0,
                'capacity_usage': tag_limit.fill_ratio * 100
            }
        
        return {
            'total_selected': total_selected,
            'total_capacity': total_capacity,
            'capacity_usage': (total_selected / total_capacity * 100) if total_capacity > 0 else 0,
            'tag_distribution': tag_distribution,
            'underrepresented_tags': self.get_underrepresented_tags(),
            'full_tags': [name for name, limit in self.tag_limits.items() if limit.is_full]
        }
    
    def reset(self):
        """重置计数器"""
        for tag_limit in self.tag_limits.values():
            tag_limit.current_count = 0
        self.selected_articles.clear()
        
        logger.info("Tag counter reset")
    
    def _get_primary_tag(self, tags: List[ArticleTag]) -> Optional[ArticleTag]:
        """
        获取主要标签（评分最高的标签）
        
        Args:
            tags: 标签列表
            
        Returns:
            主要标签
        """
        if not tags:
            return None
        
        return max(tags, key=lambda t: t.score)
    
    def export_selection_report(self) -> Dict[str, any]:
        """
        导出选择报告
        
        Returns:
            详细的选择报告
        """
        report = {
            'summary': self.get_statistics(),
            'tag_details': self.get_tag_status(),
            'selected_articles': []
        }
        
        # 按标签分组的文章信息
        articles_by_tag = {}
        for article in self.selected_articles:
            primary_tag = self._get_primary_tag(article.tags) if article.tags else None
            tag_name = primary_tag.name if primary_tag else 'untagged'
            
            if tag_name not in articles_by_tag:
                articles_by_tag[tag_name] = []
            
            articles_by_tag[tag_name].append({
                'title': article.article.title,
                'url': article.article.url,
                'final_score': article.final_score,
                'tags': [{'name': t.name, 'score': t.score} for t in article.tags] if article.tags else []
            })
        
        report['articles_by_tag'] = articles_by_tag
        
        return report
