"""
AI语义去重服务
用于在AI筛选后进行基于语义理解的深度去重
"""
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..models.news import NewsArticle
from ..filters.base import CombinedFilterResult
# 移除不存在的ai_service导入

logger = logging.getLogger(__name__)


@dataclass
class SemanticGroup:
    """语义相似文章组"""
    core_topic: str  # 核心主题
    key_entities: List[str]  # 关键实体
    articles: List[CombinedFilterResult]  # 文章列表
    similarity_scores: List[float]  # 相似度分数
    kept_article: Optional[CombinedFilterResult] = None  # 保留的文章
    removed_articles: List[CombinedFilterResult] = None  # 去除的文章

    def __post_init__(self):
        if self.removed_articles is None:
            self.removed_articles = []


class AISemanticDeduplicator:
    """AI语义去重器"""
    
    def __init__(self,
                 semantic_threshold: float = 0.85,
                 time_window_hours: int = 48,
                 max_group_size: int = 5):
        """
        初始化AI语义去重器
        
        Args:
            semantic_threshold: 语义相似度阈值
            time_window_hours: 时间窗口（小时）
            max_group_size: 单个语义组最大文章数
        """
        self.semantic_threshold = semantic_threshold
        self.time_window_hours = time_window_hours
        self.max_group_size = max_group_size
        self.ai_client = self._create_ai_client()
        
        # 统计信息
        self.stats = {
            'original_count': 0,
            'deduplicated_count': 0,
            'removed_count': 0,
            'semantic_groups': []
        }

    def _create_ai_client(self):
        """创建AI客户端"""
        try:
            from ..ai.factory import create_ai_client
            from ..config.filter_config import AIFilterConfig

            # 创建AI配置
            ai_config = AIFilterConfig(
                temperature=0.3,
                max_tokens=2000,
                timeout=60
            )

            # 创建AI客户端
            client = create_ai_client(ai_config)
            print(f"   🤖 AI语义去重客户端初始化成功")
            return client

        except Exception as e:
            logger.error(f"Failed to create AI client for semantic deduplication: {e}")
            print(f"   ❌ AI语义去重客户端初始化失败: {e}")
            return None
    
    def semantic_deduplicate(self, articles: List[CombinedFilterResult]) -> List[CombinedFilterResult]:
        """
        执行AI语义去重
        
        Args:
            articles: 筛选后的文章列表
            
        Returns:
            去重后的文章列表
        """
        if not articles or len(articles) <= 1:
            return articles
        
        print(f"🧠 开始AI语义去重，文章数: {len(articles)}")
        logger.info(f"Starting AI semantic deduplication for {len(articles)} articles")
        
        # 重置统计
        self.stats = {
            'original_count': len(articles),
            'deduplicated_count': 0,
            'removed_count': 0,
            'semantic_groups': []
        }
        
        # 按时间排序（最早的在前）
        sorted_articles = sorted(articles, key=lambda x: x.article.published)
        
        # 执行语义分组
        semantic_groups = self._perform_semantic_grouping(sorted_articles)
        
        # 从每组中选择最佳文章
        deduplicated_articles = self._select_best_from_groups(semantic_groups)
        
        # 更新统计
        self.stats['deduplicated_count'] = len(deduplicated_articles)
        self.stats['removed_count'] = self.stats['original_count'] - self.stats['deduplicated_count']
        
        print(f"✅ AI语义去重完成: 原始{self.stats['original_count']}篇 → 保留{len(deduplicated_articles)}篇 → 去除{self.stats['removed_count']}篇")
        logger.info(f"AI semantic deduplication completed: {self.stats['original_count']} → {len(deduplicated_articles)} articles")
        
        return deduplicated_articles
    
    def _perform_semantic_grouping(self, articles: List[CombinedFilterResult]) -> List[SemanticGroup]:
        """执行语义分组"""
        semantic_groups = []
        processed_indices = set()
        
        print(f"   🔍 开始语义分组分析...")
        
        for i, article in enumerate(articles):
            if i in processed_indices:
                continue
            
            print(f"   📖 分析文章 {i+1}/{len(articles)}: {article.article.title[:40]}...")
            
            # 创建新的语义组
            current_group = SemanticGroup(
                core_topic="",
                key_entities=[],
                articles=[article],
                similarity_scores=[1.0]  # 自己与自己的相似度为1.0
            )
            
            group_indices = {i}
            
            # 在时间窗口内查找语义相似的文章
            time_window_start = article.article.published
            time_window_end = time_window_start + timedelta(hours=self.time_window_hours)
            
            for j, other_article in enumerate(articles[i+1:], start=i+1):
                if j in processed_indices:
                    continue
                
                # 检查时间窗口
                if other_article.article.published > time_window_end:
                    break
                
                # 计算语义相似度
                similarity = self._calculate_semantic_similarity(article, other_article)
                
                if similarity >= self.semantic_threshold:
                    current_group.articles.append(other_article)
                    current_group.similarity_scores.append(similarity)
                    group_indices.add(j)
                    print(f"     🔗 发现语义相似文章: {other_article.article.title[:30]}... (相似度: {similarity:.2f})")
            
            # 如果组内有多篇文章，分析核心主题
            if len(current_group.articles) > 1:
                current_group.core_topic, current_group.key_entities = self._analyze_group_topic(current_group.articles)
                print(f"     📊 语义组: {current_group.core_topic} (共{len(current_group.articles)}篇文章)")
            
            semantic_groups.append(current_group)
            processed_indices.update(group_indices)
        
        print(f"   ✅ 语义分组完成: 发现{len([g for g in semantic_groups if len(g.articles) > 1])}个重复组")
        return semantic_groups
    
    def _calculate_semantic_similarity(self, article1: CombinedFilterResult, article2: CombinedFilterResult) -> float:
        """计算两篇文章的语义相似度"""
        try:
            if not self.ai_client:
                logger.warning("AI client not available for semantic similarity calculation")
                return 0.0

            # 构建比较提示
            prompt = f"""请分析以下两篇新闻文章的语义相似度，判断它们是否报道的是同一个核心事件或主题。

文章1:
标题: {article1.article.title}
摘要: {article1.article.summary}

文章2:
标题: {article2.article.title}
摘要: {article2.article.summary}

请从以下维度分析：
1. 核心事件是否相同
2. 主要实体是否相同（人物、公司、产品等）
3. 时间背景是否相同
4. 新闻价值是否重叠

请给出0-1之间的相似度分数，其中：
- 0.9-1.0: 完全相同的事件，只是表述不同
- 0.8-0.9: 高度相关的事件，核心内容相同
- 0.7-0.8: 相关事件，但有不同角度
- 0.6-0.7: 弱相关
- 0.0-0.6: 不相关

只返回数字分数，不要其他解释。"""

            # 调用AI客户端
            response = self.ai_client._call_ai_api(prompt)

            # 解析分数
            try:
                score = float(response.strip())
                return max(0.0, min(1.0, score))  # 确保在0-1范围内
            except ValueError:
                logger.warning(f"Failed to parse similarity score: {response}")
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def _analyze_group_topic(self, articles: List[CombinedFilterResult]) -> Tuple[str, List[str]]:
        """分析语义组的核心主题和关键实体"""
        try:
            if not self.ai_client:
                logger.warning("AI client not available for group topic analysis")
                return "未知主题", []

            # 构建分析提示
            titles = [article.article.title for article in articles]
            summaries = [article.article.summary for article in articles]

            prompt = f"""请分析以下新闻文章组的核心主题和关键实体：

文章标题：
{chr(10).join([f"{i+1}. {title}" for i, title in enumerate(titles)])}

文章摘要：
{chr(10).join([f"{i+1}. {summary}" for i, summary in enumerate(summaries)])}

请提供：
1. 核心主题（一句话概括）
2. 关键实体（人物、公司、产品、地点等，用逗号分隔）

格式：
主题：[核心主题]
实体：[实体1,实体2,实体3]"""

            # 调用AI客户端
            response = self.ai_client._call_ai_api(prompt)

            # 解析响应
            lines = response.strip().split('\n')
            core_topic = ""
            key_entities = []

            for line in lines:
                if line.startswith('主题：'):
                    core_topic = line[3:].strip()
                elif line.startswith('实体：'):
                    entities_str = line[3:].strip()
                    key_entities = [e.strip() for e in entities_str.split(',') if e.strip()]

            return core_topic or "未知主题", key_entities

        except Exception as e:
            logger.error(f"Error analyzing group topic: {e}")
            return "未知主题", []
    
    def _select_best_from_groups(self, semantic_groups: List[SemanticGroup]) -> List[CombinedFilterResult]:
        """从每个语义组中选择最佳文章"""
        selected_articles = []
        
        for group in semantic_groups:
            if len(group.articles) == 1:
                # 单篇文章直接保留
                selected_articles.append(group.articles[0])
            else:
                # 多篇文章选择最佳的
                best_article = self._select_best_article(group.articles)
                group.kept_article = best_article
                group.removed_articles = [a for a in group.articles if a != best_article]
                
                selected_articles.append(best_article)
                
                # 记录语义组信息
                self.stats['semantic_groups'].append({
                    'core_topic': group.core_topic,
                    'key_entities': group.key_entities,
                    'kept_article': {
                        'title': best_article.article.title,
                        'published': best_article.article.published.isoformat(),
                        'final_score': best_article.final_score
                    },
                    'removed_articles': [
                        {
                            'title': a.article.title,
                            'published': a.article.published.isoformat(),
                            'final_score': a.final_score
                        } for a in group.removed_articles
                    ],
                    'group_size': len(group.articles)
                })
        
        return selected_articles
    
    def _select_best_article(self, articles: List[CombinedFilterResult]) -> CombinedFilterResult:
        """从文章组中选择最佳文章"""
        # 选择策略：综合考虑发布时间和筛选分数
        # 1. 优先选择最早发布的（时效性）
        # 2. 如果时间差不大（<2小时），选择分数更高的
        
        if len(articles) == 1:
            return articles[0]
        
        # 按发布时间排序
        sorted_by_time = sorted(articles, key=lambda x: x.article.published)
        earliest = sorted_by_time[0]
        
        # 检查是否有时间相近但分数更高的文章
        for article in sorted_by_time[1:]:
            time_diff = (article.article.published - earliest.article.published).total_seconds() / 3600
            
            # 如果时间差小于2小时且分数明显更高，选择分数高的
            if time_diff < 2 and article.final_score > earliest.final_score + 0.1:
                return article
        
        # 默认返回最早的
        return earliest
    
    def get_semantic_deduplication_stats(self) -> Dict:
        """获取AI语义去重统计信息"""
        return {
            'original_count': self.stats['original_count'],
            'deduplicated_count': self.stats['deduplicated_count'],
            'removed_count': self.stats['removed_count'],
            'semantic_deduplication_rate': (
                self.stats['removed_count'] / self.stats['original_count'] 
                if self.stats['original_count'] > 0 else 0
            ),
            'semantic_groups_count': len(self.stats['semantic_groups']),
            'semantic_groups': self.stats['semantic_groups'][:5]  # 只返回前5个语义组
        }


# 全局AI去重器实例
_ai_deduplicator_instance = None


def get_ai_deduplicator(semantic_threshold: float = 0.85,
                       time_window_hours: int = 48) -> AISemanticDeduplicator:
    """
    获取AI语义去重器实例
    
    Args:
        semantic_threshold: 语义相似度阈值
        time_window_hours: 时间窗口
        
    Returns:
        AI语义去重器实例
    """
    global _ai_deduplicator_instance
    if _ai_deduplicator_instance is None:
        _ai_deduplicator_instance = AISemanticDeduplicator(
            semantic_threshold=semantic_threshold,
            time_window_hours=time_window_hours
        )
    return _ai_deduplicator_instance


def ai_semantic_deduplicate(articles: List[CombinedFilterResult],
                           semantic_threshold: float = 0.85,
                           time_window_hours: int = 48) -> Tuple[List[CombinedFilterResult], Dict]:
    """
    AI语义去重的便捷函数
    
    Args:
        articles: 文章列表
        semantic_threshold: 语义相似度阈值
        time_window_hours: 时间窗口
        
    Returns:
        (去重后的文章列表, 统计信息)
    """
    deduplicator = get_ai_deduplicator(
        semantic_threshold=semantic_threshold,
        time_window_hours=time_window_hours
    )
    
    deduplicated_articles = deduplicator.semantic_deduplicate(articles)
    stats = deduplicator.get_semantic_deduplication_stats()
    
    return deduplicated_articles, stats
