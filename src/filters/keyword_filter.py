"""
关键词筛选器实现
"""
import re
import time
import logging
from typing import List, Dict, Optional, Tuple
from ..models.news import NewsArticle
from ..config.filter_config import KeywordConfig
from .base import BaseFilter, KeywordMatch, KeywordFilterResult, FilterMetrics
from ..config.keyword_config import keyword_config_manager

logger = logging.getLogger(__name__)


class KeywordMatcher:
    """关键词匹配器"""
    
    def __init__(self, config: KeywordConfig):
        self.config = config
        self.keyword_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """预编译关键词正则表达式"""
        patterns = {}

        # 从配置管理器获取关键词
        keywords_data = keyword_config_manager.get_keywords()

        for category, keywords in keywords_data.items():
            if not keywords:
                continue
            
            # 构建正则表达式
            escaped_keywords = [re.escape(keyword) for keyword in keywords]
            
            if self.config.word_boundary:
                # 使用单词边界
                pattern = r'\b(?:' + '|'.join(escaped_keywords) + r')\b'
            else:
                pattern = '|'.join(escaped_keywords)
            
            flags = re.IGNORECASE if not self.config.case_sensitive else 0
            patterns[category] = re.compile(pattern, flags)
        
        return patterns
    
    def find_matches(self, text: str) -> List[KeywordMatch]:
        """在文本中查找关键词匹配"""
        if not text:
            return []
        
        matches = []
        
        for category, pattern in self.keyword_patterns.items():
            for match in pattern.finditer(text):
                keyword = match.group()
                position = match.start()
                context = self._extract_context(text, position, keyword)
                
                matches.append(KeywordMatch(
                    keyword=keyword,
                    category=category,
                    position=position,
                    context=context,
                    match_type="exact"
                ))
        
        return matches
    
    def _extract_context(self, text: str, position: int, keyword: str, 
                        context_length: int = 50) -> str:
        """提取关键词上下文"""
        start = max(0, position - context_length)
        end = min(len(text), position + len(keyword) + context_length)
        
        context = text[start:end]
        
        # 标记关键词
        keyword_start = position - start
        keyword_end = keyword_start + len(keyword)
        
        return (
            context[:keyword_start] + 
            f"**{context[keyword_start:keyword_end]}**" + 
            context[keyword_end:]
        )


class RelevanceScorer:
    """相关性评分器"""
    
    def __init__(self, config: KeywordConfig):
        self.config = config
        self.position_weights = {
            'title': 3.0,
            'summary': 2.0,
            'content': 1.0
        }
    
    def calculate_score(self, matches: List[KeywordMatch], 
                       article: NewsArticle) -> float:
        """计算文章相关性评分"""
        if not matches:
            return 0.0
        
        # 基础分数：匹配关键词数量
        unique_keywords = set(match.keyword.lower() for match in matches)
        base_score = len(unique_keywords) * 0.1
        
        # 位置加权分数
        position_score = 0.0
        for match in matches:
            position = self._get_match_position(match, article)
            position_weight = self.position_weights.get(position, 1.0)
            
            # 分类权重
            category_weight = self.config.weights.get(match.category, 1.0)
            
            # 累加分数
            position_score += position_weight * category_weight * 0.05
        
        # 分类覆盖度奖励
        categories = set(match.category for match in matches)
        category_bonus = len(categories) * 0.1
        
        # 关键词密度奖励
        text_length = len(article.title or "") + len(article.summary or "")
        if text_length > 0:
            density_bonus = min(len(matches) / text_length * 1000, 0.2)
        else:
            density_bonus = 0.0
        
        # 综合分数
        total_score = base_score + position_score + category_bonus + density_bonus
        
        # 归一化到 0-1 范围
        return min(total_score, 1.0)
    
    def calculate_category_scores(self, matches: List[KeywordMatch]) -> Dict[str, float]:
        """计算各分类的评分"""
        category_scores = {}
        
        # 按分类分组匹配
        category_matches = {}
        for match in matches:
            if match.category not in category_matches:
                category_matches[match.category] = []
            category_matches[match.category].append(match)
        
        # 计算每个分类的分数
        for category, cat_matches in category_matches.items():
            unique_keywords = set(match.keyword.lower() for match in cat_matches)
            keyword_count = len(unique_keywords)
            match_count = len(cat_matches)
            
            # 分类权重
            category_weight = self.config.weights.get(category, 1.0)
            
            # 分类分数 = 关键词数量 * 匹配次数 * 分类权重
            category_score = keyword_count * 0.3 + match_count * 0.1
            category_score *= category_weight
            
            category_scores[category] = min(category_score, 1.0)
        
        return category_scores
    
    def _get_match_position(self, match: KeywordMatch, article: NewsArticle) -> str:
        """判断匹配位置"""
        title_length = len(article.title or "")
        summary_length = len(article.summary or "")
        
        if match.position < title_length:
            return 'title'
        elif match.position < title_length + summary_length:
            return 'summary'
        else:
            return 'content'


class KeywordFilter(BaseFilter):
    """关键词筛选器"""
    
    def __init__(self, config: KeywordConfig):
        self.config = config
        self.matcher = KeywordMatcher(config)
        self.scorer = RelevanceScorer(config)
        self.metrics = FilterMetrics()
    
    def filter(self, articles: List[NewsArticle]) -> List[KeywordFilterResult]:
        """筛选文章列表"""
        results = []
        
        for article in articles:
            result = self.filter_single(article)
            if result and result.relevance_score >= self.config.threshold:
                results.append(result)
        
        # 按相关性分数排序
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # 限制结果数量
        if len(results) > self.config.max_results:
            results = results[:self.config.max_results]
        
        return results
    
    def filter_single(self, article: NewsArticle) -> Optional[KeywordFilterResult]:
        """筛选单篇文章"""
        start_time = time.time()
        
        try:
            # 准备文本内容
            text_content = self._prepare_text(article)
            
            # 查找关键词匹配
            matches = self.matcher.find_matches(text_content)
            
            # 检查最少匹配数量
            if len(matches) < self.config.min_matches:
                return None
            
            # 计算相关性评分
            relevance_score = self.scorer.calculate_score(matches, article)
            
            # 计算分类评分
            category_scores = self.scorer.calculate_category_scores(matches)
            
            processing_time = time.time() - start_time
            self.metrics.record_processing_time(processing_time * 1000)
            
            return KeywordFilterResult(
                article=article,
                matched_keywords=matches,
                relevance_score=relevance_score,
                category_scores=category_scores,
                processing_time=processing_time
            )
            
        except Exception as e:
            self.metrics.record_error()
            logger.error(f"Keyword filtering error for article {article.id}: {e}")
            return None
    
    def _prepare_text(self, article: NewsArticle) -> str:
        """准备用于匹配的文本内容"""
        parts = []
        
        # 标题（权重最高，重复添加）
        if article.title:
            parts.extend([article.title] * 3)
        
        # 摘要（权重中等，重复添加）
        if article.summary:
            parts.extend([article.summary] * 2)
        
        # 内容（权重最低）
        if article.content:
            # 限制内容长度以提高性能
            content = article.content[:2000]
            parts.append(content)
        
        return " ".join(parts)
    
    def get_metrics(self) -> Dict:
        """获取筛选指标"""
        return self.metrics.get_performance_summary()
    
    def reset_metrics(self):
        """重置指标"""
        self.metrics.reset()
