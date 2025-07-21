"""
AI智能筛选器实现
"""
import time
import logging
from typing import List, Optional
from ..models.news import NewsArticle
from ..config.filter_config import AIFilterConfig
from ..ai.factory import create_ai_client
from ..ai.exceptions import AIClientError
from ..ai.cache import AIResultCache
from .base import BaseFilter, AIFilterResult, FilterMetrics

logger = logging.getLogger(__name__)


class AIFilter(BaseFilter):
    """AI智能筛选器"""
    
    def __init__(self, config: AIFilterConfig):
        self.config = config
        self.client = create_ai_client(config)
        self.cache = AIResultCache(ttl=config.cache_ttl, max_size=config.cache_size) if config.enable_cache else None
        self.metrics = FilterMetrics()
    
    def filter(self, articles: List[NewsArticle]) -> List[AIFilterResult]:
        """筛选文章列表"""
        if not articles:
            return []

        print(f"🤖 AI筛选开始: 准备处理 {len(articles)} 篇文章")
        for i, article in enumerate(articles):
            print(f"   待筛选文章{i+1}: {article.title}")

        # 限制处理数量
        if len(articles) > self.config.max_requests:
            logger.warning(f"Too many articles ({len(articles)}), limiting to {self.config.max_requests}")
            print(f"⚠️  文章数量超限，限制为前 {self.config.max_requests} 篇")
            articles = articles[:self.config.max_requests]

        results = []

        # 批量处理
        for batch_num, batch in enumerate(self._create_batches(articles, self.config.batch_size)):
            print(f"🔄 处理第 {batch_num + 1} 批: {len(batch)} 篇文章")
            batch_results = self._process_batch(batch)
            results.extend(batch_results)

        # 调试信息：显示所有评分
        print(f"🔍 AI筛选详情: 总共处理 {len(articles)} 篇文章，获得 {len(results)} 个有效结果")
        if results:
            scores = [r.evaluation.total_score for r in results]
            print(f"📊 AI评分分布: 最高={max(scores):.1f}, 最低={min(scores):.1f}, 平均={sum(scores)/len(scores):.1f}")
            for i, result in enumerate(results[:5]):  # 显示前5个结果
                print(f"   #{i+1}: 分数={result.evaluation.total_score:.1f}, 标题={result.article.title[:50]}...")
        else:
            print(f"⚠️  AI筛选无有效结果: 可能是API调用失败或所有文章评分过低")

        # 按总分排序，取评分最高的前N条
        results.sort(key=lambda x: x.evaluation.total_score, reverse=True)

        # 取前max_selected条结果
        max_selected = getattr(self.config, 'max_selected', 3)  # 默认3条
        selected_results = results[:max_selected]

        print(f"✅ AI筛选最终结果: 选择了前 {len(selected_results)} 条评分最高的文章")
        logger.info(f"AI筛选完成: 处理了{len(results)}篇文章，选择了前{len(selected_results)}条评分最高的文章")

        return selected_results
    
    def filter_single(self, article: NewsArticle) -> Optional[AIFilterResult]:
        """筛选单篇文章"""
        start_time = time.time()
        article_title = article.title[:60] + "..." if len(article.title) > 60 else article.title

        logger.debug(f"开始AI筛选: {article_title}")

        try:
            # 检查缓存
            cached_evaluation = None
            if self.cache:
                logger.debug(f"检查缓存: {article_title}")
                cached_evaluation = self.cache.get(article)
                if cached_evaluation:
                    self.metrics.record_cache_hit()
                    processing_time = time.time() - start_time

                    logger.info(f"缓存命中: {article_title} - 评分: {cached_evaluation.total_score}/30 (缓存)")

                    return AIFilterResult(
                        article=article,
                        evaluation=cached_evaluation,
                        processing_time=processing_time,
                        ai_model=self.config.model_name,
                        cached=True
                    )
                else:
                    self.metrics.record_cache_miss()
                    logger.debug(f"缓存未命中: {article_title}")

            # AI评估
            logger.debug(f"开始AI评估: {article_title}")
            evaluation = self.client.evaluate_article(article)

            # 记录评估详情
            logger.info(f"AI评估完成: {article_title}")
            logger.info(f"  政策相关性: {evaluation.relevance_score}/10")
            logger.info(f"  创新影响: {evaluation.innovation_impact}/10")
            logger.info(f"  实用性: {evaluation.practicality}/10")
            logger.info(f"  总分: {evaluation.total_score}/30")
            logger.info(f"  置信度: {evaluation.confidence:.2f}")
            if evaluation.reasoning:
                logger.debug(f"  评估理由: {evaluation.reasoning[:200]}...")

            # 缓存结果
            if self.cache and evaluation.confidence >= self.config.min_confidence:
                self.cache.set(article, evaluation)
                logger.debug(f"结果已缓存: {article_title}")

            processing_time = time.time() - start_time
            self.metrics.record_processing_time(processing_time * 1000)

            # 判断评估质量
            if evaluation.total_score >= 20:
                quality_level = "优秀"
            elif evaluation.total_score >= 15:
                quality_level = "良好"
            elif evaluation.total_score >= 10:
                quality_level = "一般"
            else:
                quality_level = "较差"

            logger.info(f"评估质量: {quality_level} (耗时: {processing_time:.2f}秒)")

            result = AIFilterResult(
                article=article,
                evaluation=evaluation,
                processing_time=processing_time,
                ai_model=self.config.model_name,
                cached=False
            )

            # 返回评估结果，由调用方进行排名筛选
            return result

        except AIClientError as e:
            self.metrics.record_error()
            logger.error(f"AI筛选失败: {article_title} - {e}")

            # 降级策略
            if self.config.fallback_enabled:
                logger.warning(f"启用降级策略: {article_title}")
                return self._fallback_filter(article, start_time)
            else:
                logger.error(f"降级策略已禁用，跳过文章: {article_title}")
                return None
        except Exception as e:
            self.metrics.record_error()
            logger.error(f"AI筛选异常: {article_title} - {e}")
            return None
    
    def _process_batch(self, articles: List[NewsArticle]) -> List[AIFilterResult]:
        """处理文章批次"""
        # 检查缓存，分离已缓存和未缓存的文章
        cached_results = []
        uncached_articles = []
        
        if self.cache:
            for article in articles:
                cached_evaluation = self.cache.get(article)
                if cached_evaluation:
                    self.metrics.record_cache_hit()
                    cached_results.append(AIFilterResult(
                        article=article,
                        evaluation=cached_evaluation,
                        processing_time=0.0,
                        ai_model=self.config.model_name,
                        cached=True
                    ))
                else:
                    self.metrics.record_cache_miss()
                    uncached_articles.append(article)
        else:
            uncached_articles = articles
        
        # 批量评估未缓存的文章
        uncached_results = []
        if uncached_articles:
            print(f"🤖 开始AI批量评估: {len(uncached_articles)} 篇文章")
            try:
                start_time = time.time()
                evaluations = self.client.batch_evaluate(uncached_articles)
                processing_time = time.time() - start_time

                print(f"✅ AI批量评估完成: 耗时 {processing_time:.2f}s, 获得 {len(evaluations)} 个评估结果")

                for i, (article, evaluation) in enumerate(zip(uncached_articles, evaluations)):
                    print(f"   文章{i+1}: 分数={evaluation.total_score:.1f}, 置信度={evaluation.confidence:.2f}, 标题={article.title[:40]}...")

                    # 缓存结果
                    if self.cache and evaluation.confidence >= self.config.min_confidence:
                        self.cache.set(article, evaluation)

                    uncached_results.append(AIFilterResult(
                        article=article,
                        evaluation=evaluation,
                        processing_time=processing_time / len(uncached_articles),
                        ai_model=self.config.model_name,
                        cached=False
                    ))

                self.metrics.record_processing_time(processing_time * 1000)

            except AIClientError as e:
                self.metrics.record_error()
                print(f"❌ AI批量评估失败: {e}")
                logger.error(f"Batch AI evaluation failed: {e}")

                # 降级策略
                if self.config.fallback_enabled:
                    print(f"🔄 启用降级策略")
                    for article in uncached_articles:
                        fallback_result = self._fallback_filter(article, time.time())
                        if fallback_result:
                            uncached_results.append(fallback_result)
            except Exception as e:
                print(f"❌ AI评估异常: {e}")
                logger.error(f"AI evaluation exception: {e}")
        
        return cached_results + uncached_results
    
    def _fallback_filter(self, article: NewsArticle, start_time: float) -> Optional[AIFilterResult]:
        """降级筛选策略"""
        article_title = article.title[:60] + "..." if len(article.title) > 60 else article.title

        logger.info(f"执行降级评估: {article_title}")

        # 使用简单的启发式评估
        fallback_evaluation = self.client._fallback_evaluation(article)

        processing_time = time.time() - start_time

        logger.info(f"降级评估完成: {article_title} - 评分: {fallback_evaluation.total_score}/30 (降级)")
        logger.debug(f"降级理由: {fallback_evaluation.reasoning}")

        return AIFilterResult(
            article=article,
            evaluation=fallback_evaluation,
            processing_time=processing_time,
            ai_model="fallback",
            cached=False
        )
    
    def _create_batches(self, articles: List[NewsArticle], batch_size: int) -> List[List[NewsArticle]]:
        """创建文章批次"""
        batches = []
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def get_metrics(self) -> dict:
        """获取筛选指标"""
        metrics = self.metrics.get_performance_summary()
        
        # 添加缓存统计
        if self.cache:
            cache_stats = self.cache.get_stats()
            metrics.update(cache_stats)
        
        return metrics
    
    def reset_metrics(self):
        """重置指标"""
        self.metrics.reset()
    
    def clear_cache(self):
        """清空缓存"""
        if self.cache:
            self.cache.clear()
    
    def cleanup_cache(self):
        """清理过期缓存"""
        if self.cache:
            self.cache.cleanup_expired()
