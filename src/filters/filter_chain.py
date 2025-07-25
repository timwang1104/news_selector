"""
筛选链管理器实现
"""
import time
import logging
from datetime import datetime
from typing import List, Optional, Callable, Tuple, Dict, Any
from ..models.news import NewsArticle
from ..config.filter_config import FilterChainConfig
from .keyword_filter import KeywordFilter
from .ai_filter import AIFilter
from .base import (
    FilterChainResult, CombinedFilterResult, 
    KeywordFilterResult, AIFilterResult
)

logger = logging.getLogger(__name__)


class FilterProgressCallback:
    """筛选进度回调接口"""

    def on_start(self, total_articles: int):
        """筛选开始"""
        pass

    def on_keyword_progress(self, processed: int, total: int):
        """关键词筛选进度"""
        pass

    def on_keyword_complete(self, results_count: int):
        """关键词筛选完成"""
        pass

    def on_ai_start(self, total_articles: int):
        """AI筛选开始"""
        pass

    def on_ai_article_start(self, article_title: str, current: int, total: int):
        """开始评估单篇文章"""
        pass

    def on_ai_article_complete(self, article_title: str, evaluation_score: float, processing_time: float):
        """单篇文章评估完成"""
        pass

    def on_ai_batch_start(self, batch_size: int, batch_number: int, total_batches: int):
        """AI批处理开始"""
        pass

    def on_ai_batch_complete(self, batch_size: int, batch_number: int, total_batches: int, avg_score: float):
        """AI批处理完成"""
        pass

    def on_ai_progress(self, processed: int, total: int):
        """AI筛选进度"""
        pass

    def on_ai_ranking_start(self, total_results: int):
        """AI结果排序开始"""
        pass

    def on_ai_ranking_complete(self, selected_count: int, total_count: int):
        """AI结果排序完成"""
        pass

    def on_ai_complete(self, results_count: int):
        """AI筛选完成"""
        pass

    def on_ai_error(self, article_title: str, error: str):
        """AI评估错误"""
        pass

    def on_ai_fallback(self, article_title: str, reason: str):
        """AI降级处理"""
        pass

    def on_complete(self, final_count: int):
        """筛选完成"""
        pass

    def on_error(self, error: str):
        """筛选错误"""
        pass


class FilterChain:
    """筛选链管理器"""
    
    def __init__(self, 
                 keyword_filter: KeywordFilter,
                 ai_filter: AIFilter,
                 config: FilterChainConfig):
        self.keyword_filter = keyword_filter
        self.ai_filter = ai_filter
        self.config = config
    
    def process(self, articles: List[NewsArticle]) -> FilterChainResult:
        """执行完整的筛选流程"""
        start_time = datetime.now()
        result = FilterChainResult(
            total_articles=len(articles),
            processing_start_time=start_time
        )
        
        try:
            logger.info(f"Starting filter chain for {len(articles)} articles")
            
            # 第一步：关键词筛选
            keyword_results = self._execute_keyword_filter(articles, result)
            logger.info(f"Keyword filter completed: {len(keyword_results)} articles passed")
            
            # 第二步：AI筛选
            ai_results = []
            print(f"🔍 综合筛选检查: enable_ai_filter={self.config.enable_ai_filter}, keyword_results={len(keyword_results)}")
            if self.config.enable_ai_filter and keyword_results:
                print(f"🤖 开始执行AI筛选: {len(keyword_results)} 篇关键词筛选结果")
                ai_results = self._execute_ai_filter(keyword_results, result)
                print(f"✅ AI筛选完成: {len(ai_results)} 篇文章通过")
                logger.info(f"AI filter completed: {len(ai_results)} articles passed")
            elif not self.config.enable_ai_filter:
                print("⚠️  AI筛选已禁用")
            elif not keyword_results:
                print("⚠️  关键词筛选无结果，跳过AI筛选")
            
            # 第三步：结果整合
            final_results = self._combine_results(keyword_results, ai_results)
            self._finalize_results(final_results, result)
            
            logger.info(f"Filter chain completed: {result.final_selected_count} articles selected")
            
        except Exception as e:
            result.errors.append(f"筛选流程异常: {str(e)}")
            logger.error(f"Filter chain error: {e}", exc_info=True)
        
        finally:
            result.processing_end_time = datetime.now()
            result.total_processing_time = (
                result.processing_end_time - start_time
            ).total_seconds()
        
        return result
    
    def process_with_callback(self, articles: List[NewsArticle], 
                            callback: FilterProgressCallback) -> FilterChainResult:
        """带进度回调的筛选流程"""
        callback.on_start(len(articles))
        
        try:
            start_time = datetime.now()
            result = FilterChainResult(
                total_articles=len(articles),
                processing_start_time=start_time
            )
            
            # 关键词筛选
            keyword_results = []
            if self.config.enable_keyword_filter:
                keyword_results = self._execute_keyword_filter_with_callback(
                    articles, result, callback
                )
                callback.on_keyword_complete(len(keyword_results))
            
            # AI筛选
            ai_results = []
            if self.config.enable_ai_filter and keyword_results:
                ai_results = self._execute_ai_filter_with_callback(
                    keyword_results, result, callback
                )
                callback.on_ai_complete(len(ai_results))
            
            # 整合结果
            final_results = self._combine_results(keyword_results, ai_results)
            self._finalize_results(final_results, result)
            
            result.processing_end_time = datetime.now()
            result.total_processing_time = (
                result.processing_end_time - start_time
            ).total_seconds()
            
            callback.on_complete(result.final_selected_count)
            return result
            
        except Exception as e:
            callback.on_error(str(e))
            raise
    
    def _execute_keyword_filter(self, articles: List[NewsArticle], 
                              result: FilterChainResult) -> List[KeywordFilterResult]:
        """执行关键词筛选"""
        if not self.config.enable_keyword_filter:
            return []
        
        start_time = time.time()
        try:
            keyword_results = self.keyword_filter.filter(articles)
            
            # 应用阈值过滤
            filtered_results = [
                r for r in keyword_results 
                if r.relevance_score >= self.config.keyword_threshold
            ]
            
            # 限制结果数量
            if len(filtered_results) > self.config.max_keyword_results:
                filtered_results = sorted(
                    filtered_results, 
                    key=lambda x: x.relevance_score, 
                    reverse=True
                )[:self.config.max_keyword_results]
            
            result.keyword_filtered_count = len(filtered_results)
            result.keyword_filter_time = time.time() - start_time
            
            return filtered_results
            
        except Exception as e:
            result.errors.append(f"关键词筛选失败: {str(e)}")
            if self.config.fail_fast:
                raise
            return []
    
    def _execute_ai_filter(self, keyword_results: List[KeywordFilterResult],
                         result: FilterChainResult) -> List[AIFilterResult]:
        """执行AI筛选"""
        start_time = time.time()
        try:
            # 提取文章
            articles = [kr.article for kr in keyword_results]
            
            # 限制AI处理数量
            if len(articles) > self.config.max_ai_requests:
                # 按关键词分数排序，取前N个
                sorted_results = sorted(
                    keyword_results,
                    key=lambda x: x.relevance_score,
                    reverse=True
                )
                articles = [r.article for r in sorted_results[:self.config.max_ai_requests]]
                result.warnings.append(
                    f"AI筛选数量限制，仅处理前{self.config.max_ai_requests}篇文章"
                )
            
            ai_results = self.ai_filter.filter(articles)

            # AI筛选器已经按评分排序并返回前N条结果，无需再次过滤
            result.ai_filtered_count = len(ai_results)
            result.ai_filter_time = time.time() - start_time

            return ai_results
            
        except Exception as e:
            result.errors.append(f"AI筛选失败: {str(e)}")
            if self.config.fail_fast:
                raise
            return []
    
    def _execute_keyword_filter_with_callback(self, articles: List[NewsArticle],
                                            result: FilterChainResult,
                                            callback: FilterProgressCallback) -> List[KeywordFilterResult]:
        """带回调的关键词筛选"""
        keyword_results = []
        batch_size = self.config.batch_size
        
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_results = []
            
            for article in batch:
                single_result = self.keyword_filter.filter_single(article)
                if single_result and single_result.relevance_score >= self.config.keyword_threshold:
                    batch_results.append(single_result)
            
            keyword_results.extend(batch_results)
            callback.on_keyword_progress(min(i + batch_size, len(articles)), len(articles))
        
        # 限制结果数量
        if len(keyword_results) > self.config.max_keyword_results:
            keyword_results = sorted(
                keyword_results,
                key=lambda x: x.relevance_score,
                reverse=True
            )[:self.config.max_keyword_results]
        
        result.keyword_filtered_count = len(keyword_results)
        return keyword_results
    
    def _execute_ai_filter_with_callback(self, keyword_results: List[KeywordFilterResult],
                                       result: FilterChainResult,
                                       callback: FilterProgressCallback) -> List[AIFilterResult]:
        """带回调的AI筛选"""
        articles = [kr.article for kr in keyword_results]
        
        # 限制AI处理数量
        if len(articles) > self.config.max_ai_requests:
            sorted_results = sorted(
                keyword_results,
                key=lambda x: x.relevance_score,
                reverse=True
            )
            articles = [r.article for r in sorted_results[:self.config.max_ai_requests]]
        
        ai_results = []
        batch_size = 5  # AI筛选使用较小的批次

        # 收集所有AI评估结果
        all_results = []
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batch_results = []

            for article in batch:
                single_result = self.ai_filter.filter_single(article)
                if single_result:
                    batch_results.append(single_result)

            all_results.extend(batch_results)
            callback.on_ai_progress(min(i + batch_size, len(articles)), len(articles))

        # 按评分排序并取前N条
        all_results.sort(key=lambda x: x.evaluation.total_score, reverse=True)
        max_selected = getattr(self.ai_filter.config, 'max_selected', 3)
        ai_results = all_results[:max_selected]

        # 通知所有AI评估结果（用于更新界面显示）
        if callback and hasattr(callback, 'on_all_ai_results'):
            callback.on_all_ai_results(all_results)

        result.ai_filtered_count = len(ai_results)
        return ai_results

    def _combine_results(self, keyword_results: List[KeywordFilterResult],
                        ai_results: List[AIFilterResult]) -> List[CombinedFilterResult]:
        """整合关键词和AI筛选结果"""
        combined_results = []

        # 创建AI结果的快速查找字典
        ai_results_dict = {
            self._get_article_id(r.article): r for r in ai_results
        }

        for keyword_result in keyword_results:
            article_id = self._get_article_id(keyword_result.article)
            ai_result = ai_results_dict.get(article_id)

            # 计算最终分数
            final_score = self._calculate_final_score(keyword_result, ai_result)

            # 判断是否选中
            selected, rejection_reason = self._determine_selection(
                keyword_result, ai_result, final_score
            )

            combined_result = CombinedFilterResult(
                article=keyword_result.article,
                keyword_result=keyword_result,
                ai_result=ai_result,
                final_score=final_score,
                selected=selected,
                rejection_reason=rejection_reason
            )

            combined_results.append(combined_result)

        return combined_results

    def _calculate_final_score(self, keyword_result: KeywordFilterResult,
                             ai_result: Optional[AIFilterResult]) -> float:
        """计算最终综合分数"""
        keyword_score = keyword_result.relevance_score

        if ai_result is None:
            # 仅有关键词分数
            return keyword_score

        # 综合评分：关键词分数 * 0.3 + AI分数 * 0.7
        ai_score = ai_result.evaluation.total_score / 30.0  # 归一化到0-1
        final_score = keyword_score * 0.3 + ai_score * 0.7

        return final_score

    def _determine_selection(self, keyword_result: KeywordFilterResult,
                           ai_result: Optional[AIFilterResult],
                           final_score: float) -> Tuple[bool, Optional[str]]:
        """判断文章是否被选中"""
        # 关键词筛选未通过
        if keyword_result.relevance_score < self.config.keyword_threshold:
            return False, "关键词相关性不足"

        # AI筛选已经按排名选择了最优文章，无需再次阈值判断
        # AI筛选失败但关键词分数较高
        if ai_result is None and keyword_result.relevance_score >= 0.8:
            return True, None

        # 综合分数判断
        if final_score >= self.config.final_score_threshold:
            return True, None
        else:
            return False, "综合评分不足"

    def _finalize_results(self, combined_results: List[CombinedFilterResult],
                         result: FilterChainResult):
        """整理最终结果"""
        # 分离选中和被拒绝的文章
        selected = [r for r in combined_results if r.selected]
        rejected = [r for r in combined_results if not r.selected]

        # 按最终分数排序
        if self.config.sort_by == "final_score":
            selected.sort(key=lambda x: x.final_score, reverse=True)
        elif self.config.sort_by == "relevance":
            selected.sort(key=lambda x: x.keyword_result.relevance_score if x.keyword_result else 0, reverse=True)
        elif self.config.sort_by == "timestamp":
            selected.sort(key=lambda x: x.article.published_at or datetime.min, reverse=True)

        # 限制最终结果数量
        if len(selected) > self.config.max_final_results:
            selected = selected[:self.config.max_final_results]

        result.selected_articles = selected
        result.final_selected_count = len(selected)

        if self.config.include_rejected:
            result.rejected_articles = rejected

    def _get_article_id(self, article: NewsArticle) -> str:
        """获取文章唯一标识"""
        return article.id or f"{article.title}_{article.published_at}"

    def get_metrics(self) -> Dict[str, Any]:
        """获取筛选链性能指标"""
        metrics = {
            "keyword_filter": self.keyword_filter.get_metrics(),
            "ai_filter": self.ai_filter.get_metrics()
        }
        return metrics

    def reset_metrics(self):
        """重置所有筛选器的指标"""
        self.keyword_filter.reset_metrics()
        self.ai_filter.reset_metrics()
