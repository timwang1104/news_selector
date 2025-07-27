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
    KeywordFilterResult, AIFilterResult, ArticleTag
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

        # 初始化标签计数器、生成器和平衡选择器
        self.tag_counter = None
        self.tag_generator = None
        self.balanced_selector = None

        # 安全地访问tag_balance配置
        tag_balance_config = config.tag_balance

        # 如果tag_balance是字典，转换为对象访问
        if isinstance(tag_balance_config, dict):
            enable_tag_limits = tag_balance_config.get('enable_tag_limits', False)
            enable_tag_generation = tag_balance_config.get('enable_tag_generation', False)
            enable_balanced_selection = tag_balance_config.get('enable_balanced_selection', False)
            tag_limits = tag_balance_config.get('tag_limits', {})
            min_tag_score = tag_balance_config.get('min_tag_score', 0.2)
            max_tags_per_article = tag_balance_config.get('max_tags_per_article', 5)
            primary_tag_threshold = tag_balance_config.get('primary_tag_threshold', 0.5)
            underrepresented_boost = tag_balance_config.get('underrepresented_boost', 1.5)
        else:
            # 对象访问
            enable_tag_limits = getattr(tag_balance_config, 'enable_tag_limits', False)
            enable_tag_generation = getattr(tag_balance_config, 'enable_tag_generation', False)
            enable_balanced_selection = getattr(tag_balance_config, 'enable_balanced_selection', False)
            tag_limits = getattr(tag_balance_config, 'tag_limits', {})
            min_tag_score = getattr(tag_balance_config, 'min_tag_score', 0.2)
            max_tags_per_article = getattr(tag_balance_config, 'max_tags_per_article', 5)
            primary_tag_threshold = getattr(tag_balance_config, 'primary_tag_threshold', 0.5)
            underrepresented_boost = getattr(tag_balance_config, 'underrepresented_boost', 1.5)

        if enable_tag_limits:
            from .tag_counter import TagCounter
            self.tag_counter = TagCounter(tag_limits)

        if enable_tag_generation:
            from .tag_generator import TagGenerator
            self.tag_generator = TagGenerator(
                min_tag_score=min_tag_score,
                max_tags_per_article=max_tags_per_article,
                primary_tag_threshold=primary_tag_threshold
            )

        if enable_balanced_selection and self.tag_counter:
            from .balanced_selector import BalancedSelector, BalanceStrategy
            strategy = BalanceStrategy(
                underrepresented_boost=underrepresented_boost
            )
            self.balanced_selector = BalancedSelector(self.tag_counter, strategy)

        # 初始化标签分析器
        if enable_tag_generation:
            from .tag_analyzer import TagAnalyzer
            self.tag_analyzer = TagAnalyzer(tag_limits)
        else:
            self.tag_analyzer = None
    
    def process(self, articles: List[NewsArticle], test_mode: bool = False) -> FilterChainResult:
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
                ai_results = self._execute_ai_filter(keyword_results, result, test_mode)
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
                            callback: FilterProgressCallback, test_mode: bool = False) -> FilterChainResult:
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
                    keyword_results, result, callback, test_mode
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
                         result: FilterChainResult, test_mode: bool = False) -> List[AIFilterResult]:
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
            
            if test_mode:
                # 测试模式：生成模拟AI筛选结果
                print(f"🧪 测试模式：生成模拟AI筛选结果")
                ai_results = self._generate_mock_ai_results(articles)
            else:
                # 正常模式：调用真实AI API
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
                                       callback: FilterProgressCallback, test_mode: bool = False) -> List[AIFilterResult]:
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
        if test_mode:
            # 测试模式：生成模拟结果
            print(f"🧪 测试模式：生成模拟AI筛选结果")
            all_results = self._generate_mock_ai_results(articles)
            # 模拟进度更新
            for i in range(0, len(articles), batch_size):
                callback.on_ai_progress(min(i + batch_size, len(articles)), len(articles))
        else:
            # 正常模式：调用真实AI API
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

            # 生成或增强标签
            tags = self._generate_combined_tags(keyword_result, ai_result)

            combined_result = CombinedFilterResult(
                article=keyword_result.article,
                keyword_result=keyword_result,
                ai_result=ai_result,
                final_score=final_score,
                selected=selected,
                rejection_reason=rejection_reason,
                tags=tags
            )

            combined_results.append(combined_result)

        # 如果启用了标签平衡，应用平衡筛选
        if self.config.tag_balance.enable_balanced_selection and self.tag_counter:
            combined_results = self._apply_balanced_selection(combined_results)

        return combined_results

    def _generate_mock_ai_results(self, articles: List[NewsArticle]) -> List[AIFilterResult]:
        """生成模拟的AI筛选结果（测试模式）"""
        import random
        from ..models.ai_filter_result import AIFilterResult, AIEvaluation
        
        mock_results = []
        for i, article in enumerate(articles):
            # 生成随机评分（15-30分）
            score = random.randint(15, 30)
            
            # 创建模拟评估结果
            evaluation = AIEvaluation(
                relevance_score=random.randint(3, 10),
                importance_score=random.randint(3, 10), 
                quality_score=random.randint(3, 10),
                total_score=score,
                reasoning=f"模拟AI评估：这是一篇关于{article.title[:20]}的文章，评分为{score}分"
            )
            
            # 创建AI筛选结果
            ai_result = AIFilterResult(
                article=article,
                evaluation=evaluation,
                processing_time=random.uniform(0.1, 0.5),  # 模拟处理时间
                selected=score >= 20  # 20分以上被选中
            )
            
            mock_results.append(ai_result)
        
        # 按评分排序
        mock_results.sort(key=lambda x: x.evaluation.total_score, reverse=True)
        
        # 限制结果数量
        max_selected = getattr(self.ai_filter.config, 'max_selected', 3)
        return mock_results[:max_selected]

    def _generate_combined_tags(self, keyword_result: KeywordFilterResult,
                               ai_result: Optional[AIFilterResult]) -> List:
        """生成综合标签"""
        if not self.tag_generator:
            return keyword_result.tags if keyword_result.tags else []

        # 从关键词结果获取标签
        tags = keyword_result.tags if keyword_result.tags else []

        # 如果没有标签，从关键词结果生成
        if not tags:
            tags = self.tag_generator.generate_tags_from_keyword_result(keyword_result)

        # 使用AI结果增强标签
        if ai_result:
            tags = self.tag_generator.enhance_tags_with_ai_result(tags, ai_result)

        return tags

    def _apply_balanced_selection(self, combined_results: List[CombinedFilterResult]) -> List[CombinedFilterResult]:
        """应用标签平衡筛选"""
        if not self.balanced_selector:
            return combined_results

        # 使用平衡选择器进行筛选
        return self.balanced_selector.select_balanced_articles(
            combined_results,
            max_results=self.config.max_final_results
        )

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
        article_title = keyword_result.article.title[:30] + "..."

        # 关键词筛选未通过
        if keyword_result.relevance_score < self.config.keyword_threshold:
            print(f"   ❌ {article_title}: 关键词相关性不足 ({keyword_result.relevance_score:.3f} < {self.config.keyword_threshold})")
            return False, "关键词相关性不足"

        # 修复：只有通过AI筛选的文章才能被最终选中
        # 这确保了统计数字的一致性
        if ai_result is None:
            print(f"   ❌ {article_title}: 没有AI筛选结果，不能被选中 (关键词:{keyword_result.relevance_score:.3f})")
            return False, "没有AI筛选结果"

        # 综合分数判断
        if final_score >= self.config.final_score_threshold:
            ai_score = ai_result.evaluation.total_score if ai_result else 0
            print(f"   ✅ {article_title}: 综合分数通过 (最终:{final_score:.3f}, 关键词:{keyword_result.relevance_score:.3f}, AI:{ai_score}/30)")
            return True, None
        else:
            ai_score = ai_result.evaluation.total_score if ai_result else 0
            print(f"   ❌ {article_title}: 综合评分不足 (最终:{final_score:.3f} < {self.config.final_score_threshold}, 关键词:{keyword_result.relevance_score:.3f}, AI:{ai_score}/30)")
            return False, "综合评分不足"

    def _finalize_results(self, combined_results: List[CombinedFilterResult],
                         result: FilterChainResult):
        """整理最终结果"""
        # 分离选中和被拒绝的文章
        selected = [r for r in combined_results if r.selected]
        rejected = [r for r in combined_results if not r.selected]

        print(f"🔍 _finalize_results调试信息:")
        print(f"   combined_results总数: {len(combined_results)}")
        print(f"   selected数量: {len(selected)}")
        print(f"   rejected数量: {len(rejected)}")
        print(f"   AI筛选通过数量: {result.ai_filtered_count}")

        # 显示选中文章的详细信息
        for i, r in enumerate(selected):
            has_ai = "有AI结果" if r.ai_result else "无AI结果"
            print(f"   选中文章{i+1}: {r.article.title[:30]}... (最终分数:{r.final_score:.3f}, {has_ai})")

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

        # 生成标签统计
        if self.tag_analyzer:
            result.tag_statistics = self.tag_analyzer.analyze_results(selected)
            logger.info(f"标签统计生成完成: {len(result.tag_statistics.tag_distribution)} 个标签")

            # 打印标签分布摘要
            if result.tag_statistics.tag_distribution:
                print("📊 标签分布统计:")
                for tag_name, count in sorted(result.tag_statistics.tag_distribution.items(),
                                            key=lambda x: x[1], reverse=True):
                    fill_ratio = result.tag_statistics.tag_fill_ratios.get(tag_name, 0) * 100
                    print(f"   {tag_name}: {count} 篇 ({fill_ratio:.1f}%)")

                print(f"📈 多样性评分: {result.tag_statistics.tag_diversity_score*100:.1f}%")
                print(f"🏷️  平均标签数: {result.tag_statistics.average_tags_per_article:.1f}")

                if result.tag_statistics.underrepresented_tags:
                    print(f"⚠️  代表性不足: {', '.join(result.tag_statistics.underrepresented_tags[:3])}")
                if result.tag_statistics.overrepresented_tags:
                    print(f"⚡ 过度集中: {', '.join(result.tag_statistics.overrepresented_tags[:3])}")

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
