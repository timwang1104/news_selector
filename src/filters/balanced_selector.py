"""
标签平衡筛选策略
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .base import CombinedFilterResult, ArticleTag
from .tag_counter import TagCounter

logger = logging.getLogger(__name__)


@dataclass
class BalanceStrategy:
    """平衡策略配置"""
    quality_weight: float = 0.7      # 质量权重
    balance_weight: float = 0.3      # 平衡权重
    diversity_bonus: float = 0.1     # 多样性奖励
    underrepresented_boost: float = 1.5  # 代表性不足标签的权重提升


class BalancedSelector:
    """标签平衡筛选器"""
    
    def __init__(self, 
                 tag_counter: TagCounter,
                 strategy: BalanceStrategy = None):
        """
        初始化平衡筛选器
        
        Args:
            tag_counter: 标签计数器
            strategy: 平衡策略配置
        """
        self.tag_counter = tag_counter
        self.strategy = strategy or BalanceStrategy()
        
    def select_balanced_articles(self, 
                                candidates: List[CombinedFilterResult],
                                max_results: int = None) -> List[CombinedFilterResult]:
        """
        执行标签平衡筛选
        
        Args:
            candidates: 候选文章列表
            max_results: 最大结果数量
            
        Returns:
            平衡筛选后的文章列表
        """
        if not candidates:
            return []
        
        # 重置计数器
        self.tag_counter.reset()
        
        # 过滤出已选中的候选文章
        selected_candidates = [c for c in candidates if c.selected]
        rejected_candidates = [c for c in candidates if not c.selected]
        
        logger.info(f"开始标签平衡筛选: {len(selected_candidates)} 个候选文章")
        
        # 计算每篇文章的平衡分数
        scored_candidates = self._calculate_balance_scores(selected_candidates)
        
        # 执行平衡选择
        final_selected = self._execute_balanced_selection(scored_candidates, max_results)
        
        # 更新未选中文章的状态
        selected_ids = {self._get_article_id(r.article) for r in final_selected}
        final_rejected = []
        
        for candidate in selected_candidates:
            if self._get_article_id(candidate.article) not in selected_ids:
                candidate.selected = False
                candidate.rejection_reason = "标签平衡筛选未通过"
                final_rejected.append(candidate)
        
        # 合并所有结果
        all_results = final_selected + final_rejected + rejected_candidates
        
        logger.info(f"标签平衡筛选完成: 选中 {len(final_selected)} 篇文章")
        self._log_selection_summary(final_selected)
        
        return all_results
    
    def _calculate_balance_scores(self, 
                                 candidates: List[CombinedFilterResult]) -> List[Tuple[CombinedFilterResult, float]]:
        """
        计算每篇文章的平衡分数
        
        Args:
            candidates: 候选文章列表
            
        Returns:
            (文章, 平衡分数) 的元组列表
        """
        scored_candidates = []
        
        # 获取标签优先级权重
        tag_priorities = self.tag_counter.get_balanced_selection_priority()
        underrepresented_tags = set(self.tag_counter.get_underrepresented_tags())
        
        for candidate in candidates:
            # 基础质量分数
            quality_score = candidate.final_score
            
            # 标签平衡分数
            balance_score = self._calculate_tag_balance_score(
                candidate.tags, tag_priorities, underrepresented_tags
            )
            
            # 多样性奖励
            diversity_score = self._calculate_diversity_score(candidate.tags)
            
            # 综合平衡分数
            total_balance_score = (
                quality_score * self.strategy.quality_weight +
                balance_score * self.strategy.balance_weight +
                diversity_score * self.strategy.diversity_bonus
            )
            
            scored_candidates.append((candidate, total_balance_score))
        
        # 按平衡分数排序
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        return scored_candidates
    
    def _calculate_tag_balance_score(self, 
                                   tags: List[ArticleTag],
                                   tag_priorities: Dict[str, float],
                                   underrepresented_tags: set) -> float:
        """
        计算标签平衡分数
        
        Args:
            tags: 文章标签列表
            tag_priorities: 标签优先级权重
            underrepresented_tags: 代表性不足的标签集合
            
        Returns:
            标签平衡分数
        """
        if not tags:
            return 0.5  # 无标签文章的中等分数
        
        # 获取主要标签
        primary_tag = max(tags, key=lambda t: t.score)
        
        # 基础平衡分数
        base_score = tag_priorities.get(primary_tag.name, 0.5)
        
        # 代表性不足标签的额外奖励
        if primary_tag.name in underrepresented_tags:
            base_score *= self.strategy.underrepresented_boost
        
        # 标签质量调整
        tag_quality_factor = primary_tag.score * primary_tag.confidence
        
        return min(1.0, base_score * tag_quality_factor)
    
    def _calculate_diversity_score(self, tags: List[ArticleTag]) -> float:
        """
        计算多样性分数
        
        Args:
            tags: 文章标签列表
            
        Returns:
            多样性分数
        """
        if not tags:
            return 0.0
        
        # 标签数量奖励（更多标签 = 更高多样性）
        tag_count_score = min(0.5, len(tags) * 0.1)
        
        # 标签分布均匀性（评分差异小 = 更均匀）
        if len(tags) > 1:
            scores = [tag.score for tag in tags]
            score_variance = sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)
            uniformity_score = max(0.0, 0.3 - score_variance)
        else:
            uniformity_score = 0.0
        
        return tag_count_score + uniformity_score
    
    def _execute_balanced_selection(self, 
                                   scored_candidates: List[Tuple[CombinedFilterResult, float]],
                                   max_results: int = None) -> List[CombinedFilterResult]:
        """
        执行平衡选择
        
        Args:
            scored_candidates: 评分后的候选文章列表
            max_results: 最大结果数量
            
        Returns:
            选中的文章列表
        """
        selected = []
        
        for candidate, balance_score in scored_candidates:
            # 检查是否可以选择该文章
            if self.tag_counter.can_select_article(candidate.tags):
                # 尝试添加文章
                if self.tag_counter.add_selected_article(candidate):
                    selected.append(candidate)
                    
                    # 检查是否达到最大结果数量
                    if max_results and len(selected) >= max_results:
                        break
                else:
                    # 添加失败，可能是标签已满
                    logger.debug(f"无法添加文章到标签计数器: {candidate.article.title[:50]}")
            else:
                # 不能选择，标签可能已满
                logger.debug(f"标签已满，无法选择文章: {candidate.article.title[:50]}")
        
        return selected
    
    def _log_selection_summary(self, selected_articles: List[CombinedFilterResult]):
        """记录选择摘要"""
        if not selected_articles:
            return
        
        # 统计标签分布
        tag_distribution = {}
        for article in selected_articles:
            if article.tags:
                primary_tag = max(article.tags, key=lambda t: t.score)
                tag_name = primary_tag.name
                tag_distribution[tag_name] = tag_distribution.get(tag_name, 0) + 1
        
        logger.info("标签分布统计:")
        for tag_name, count in sorted(tag_distribution.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {tag_name}: {count} 篇文章")
    
    def _get_article_id(self, article) -> str:
        """获取文章ID"""
        return getattr(article, 'id', '') or getattr(article, 'url', '')
    
    def get_selection_report(self) -> Dict[str, any]:
        """
        获取选择报告
        
        Returns:
            选择报告字典
        """
        return self.tag_counter.export_selection_report()


class AdaptiveBalanceStrategy:
    """自适应平衡策略"""
    
    def __init__(self, base_strategy: BalanceStrategy = None):
        self.base_strategy = base_strategy or BalanceStrategy()
        self.selection_history = []
    
    def adapt_strategy(self, 
                      current_distribution: Dict[str, int],
                      target_distribution: Dict[str, int]) -> BalanceStrategy:
        """
        根据当前分布和目标分布调整策略
        
        Args:
            current_distribution: 当前标签分布
            target_distribution: 目标标签分布
            
        Returns:
            调整后的策略
        """
        # 计算分布偏差
        total_current = sum(current_distribution.values())
        total_target = sum(target_distribution.values())
        
        if total_current == 0 or total_target == 0:
            return self.base_strategy
        
        # 计算需要调整的标签
        underrepresented_ratio = 0.0
        for tag, target_count in target_distribution.items():
            current_count = current_distribution.get(tag, 0)
            target_ratio = target_count / total_target
            current_ratio = current_count / total_current if total_current > 0 else 0
            
            if current_ratio < target_ratio * 0.8:  # 低于目标80%认为代表性不足
                underrepresented_ratio += (target_ratio - current_ratio)
        
        # 调整策略参数
        adapted_strategy = BalanceStrategy(
            quality_weight=max(0.5, self.base_strategy.quality_weight - underrepresented_ratio * 0.2),
            balance_weight=min(0.5, self.base_strategy.balance_weight + underrepresented_ratio * 0.2),
            diversity_bonus=self.base_strategy.diversity_bonus,
            underrepresented_boost=min(2.0, self.base_strategy.underrepresented_boost + underrepresented_ratio)
        )
        
        return adapted_strategy
