"""
批量筛选服务 - 管理多个订阅源的自动切换和批量筛选
"""
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.news import NewsArticle
from ..models.rss import RSSFeed, RSSArticle
from ..services.custom_rss_service import CustomRSSService
from ..services.filter_service import FilterService, FilterProgressCallback
from ..filters.base import (
    FilterChainResult,
    SubscriptionFilterResult,
    BatchFilterResult,
    CombinedFilterResult
)

logger = logging.getLogger(__name__)



class BatchFilterProgressCallback:
    """批量筛选进度回调接口"""
    
    def on_batch_start(self, total_subscriptions: int):
        """批量筛选开始"""
        pass
    
    def on_subscription_start(self, subscription, current: int, total: int):
        """开始处理订阅源"""
        pass
    
    def on_subscription_fetch_complete(self, subscription, articles_count: int):
        """订阅源文章获取完成"""
        pass
    
    def on_subscription_filter_complete(self, subscription, selected_count: int):
        """订阅源筛选完成"""
        pass
    
    def on_subscription_error(self, subscription, error: str):
        """订阅源处理错误"""
        pass
    
    def on_batch_complete(self, result: BatchFilterResult):
        """批量筛选完成"""
        pass


class BatchFilterConfig:
    """批量筛选配置"""
    
    def __init__(self):
        # 订阅源筛选配置
        self.max_subscriptions: Optional[int] = None  # 最大处理订阅源数量
        self.subscription_filter: Optional[Callable[[any], bool]] = None  # 订阅源过滤函数

        # 文章获取配置
        self.articles_per_subscription: int = 50  # 每个订阅源获取的文章数量
        self.exclude_read: bool = True  # 是否排除已读文章
        self.hours_back: Optional[int] = 24  # 获取多少小时内的文章

        # 筛选配置
        self.filter_type: str = "chain"  # 筛选类型: keyword, ai, chain
        self.enable_parallel: bool = True  # 是否启用并行处理
        self.max_workers: int = 3  # 最大并行工作线程数

        # 结果配置
        self.max_results_per_subscription: Optional[int] = None  # 每个订阅源最大结果数
        self.min_score_threshold: Optional[float] = None  # 最小分数阈值
        self.sort_by: str = "final_score"  # 排序方式: final_score, published, subscription
        self.group_by_subscription: bool = True  # 是否按订阅源分组显示




class CustomRSSBatchFilterManager:
    """自定义RSS批量筛选管理器"""

    def __init__(self):
        self.custom_rss_service = CustomRSSService()
        self.filter_service = FilterService()

    def filter_subscriptions_batch(self,
                                 config: BatchFilterConfig,
                                 callback: Optional[BatchFilterProgressCallback] = None) -> BatchFilterResult:
        """
        批量筛选自定义RSS订阅源

        Args:
            config: 批量筛选配置
            callback: 进度回调

        Returns:
            批量筛选结果
        """
        start_time = datetime.now()

        # 获取自定义RSS订阅源列表
        rss_feeds = self._get_filtered_rss_feeds(config)

        if not rss_feeds:
            logger.warning("No RSS feeds found for filtering")
            return BatchFilterResult(
                total_subscriptions=0,
                processed_subscriptions=0,
                processing_start_time=start_time,
                processing_end_time=datetime.now()
            )

        logger.info(f"Starting batch filtering for {len(rss_feeds)} RSS feeds")

        # 创建批量结果对象
        batch_result = BatchFilterResult(
            total_subscriptions=len(rss_feeds),
            processed_subscriptions=0,
            processing_start_time=start_time
        )

        # 通知批量筛选开始
        if callback:
            callback.on_batch_start(len(rss_feeds))

        # 处理订阅源
        if config.enable_parallel:
            self._process_rss_feeds_parallel(rss_feeds, config, batch_result, callback)
        else:
            self._process_rss_feeds_sequential(rss_feeds, config, batch_result, callback)

        # 完成处理
        batch_result.processing_end_time = datetime.now()

        # 计算汇总统计
        self._calculate_batch_statistics(batch_result)

        # 通知批量筛选完成
        if callback:
            callback.on_batch_complete(batch_result)

        logger.info(f"Batch filtering completed: {batch_result.processed_subscriptions}/{batch_result.total_subscriptions} RSS feeds processed")

        return batch_result

    def _get_filtered_rss_feeds(self, config: BatchFilterConfig) -> List[RSSFeed]:
        """获取过滤后的RSS订阅源列表"""
        try:
            all_feeds = self.custom_rss_service.get_active_subscriptions()

            # 应用订阅源过滤器
            filtered_feeds = []

            for feed in all_feeds:
                # 自定义过滤函数
                if config.subscription_filter and not config.subscription_filter(feed):
                    continue

                # 直接添加所有通过自定义过滤器的订阅源
                filtered_feeds.append(feed)

            # 限制数量
            if config.max_subscriptions:
                filtered_feeds = filtered_feeds[:config.max_subscriptions]

            logger.info(f"Filtered {len(filtered_feeds)} RSS feeds from {len(all_feeds)} total")
            return filtered_feeds

        except Exception as e:
            logger.error(f"Failed to get RSS feeds: {e}")
            return []



    def _process_rss_feeds_sequential(self,
                                    feeds: List[RSSFeed],
                                    config: BatchFilterConfig,
                                    batch_result: BatchFilterResult,
                                    callback: Optional[BatchFilterProgressCallback]):
        """顺序处理RSS订阅源"""
        for i, feed in enumerate(feeds):
            try:
                if callback:
                    subscription = self._rss_feed_to_subscription(feed)
                    callback.on_subscription_start(subscription, i + 1, len(feeds))

                result = self._process_single_rss_feed(feed, config, callback)
                batch_result.subscription_results.append(result)
                batch_result.processed_subscriptions += 1

            except Exception as e:
                logger.error(f"Error processing RSS feed {feed.title}: {e}")
                batch_result.errors.append(f"RSS feed {feed.title}: {e}")

    def _process_rss_feeds_parallel(self,
                                  feeds: List[RSSFeed],
                                  config: BatchFilterConfig,
                                  batch_result: BatchFilterResult,
                                  callback: Optional[BatchFilterProgressCallback]):
        """并行处理RSS订阅源"""
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # 提交任务
            future_to_feed = {
                executor.submit(self._process_single_rss_feed, feed, config, callback): feed
                for feed in feeds
            }

            # 收集结果
            for i, future in enumerate(as_completed(future_to_feed)):
                feed = future_to_feed[future]
                try:
                    if callback:
                        subscription = self._rss_feed_to_subscription(feed)
                        callback.on_subscription_start(subscription, i + 1, len(feeds))

                    result = future.result()
                    batch_result.subscription_results.append(result)
                    batch_result.processed_subscriptions += 1

                except Exception as e:
                    logger.error(f"Error processing RSS feed {feed.title}: {e}")
                    batch_result.errors.append(f"RSS feed {feed.title}: {e}")

    def _process_single_rss_feed(self,
                               feed: RSSFeed,
                               config: BatchFilterConfig,
                               callback: Optional[BatchFilterProgressCallback]) -> SubscriptionFilterResult:
        """处理单个RSS订阅源"""
        logger.debug(f"Processing RSS feed: {feed.title}")

        # 获取文章
        fetch_start = time.time()
        articles = self._get_rss_feed_articles(feed, config)
        fetch_time = time.time() - fetch_start

        if callback:
            subscription = self._rss_feed_to_subscription(feed)
            callback.on_subscription_fetch_complete(subscription, len(articles))

        # 筛选文章
        if articles:
            filter_result = self.filter_service.filter_articles(
                articles=articles,
                filter_type=config.filter_type
            )

            # 应用结果过滤
            self._apply_result_filters(filter_result, config)
        else:
            # 创建空的筛选结果
            filter_result = FilterChainResult(
                total_articles=0,
                processing_start_time=datetime.now()
            )
            filter_result.processing_end_time = datetime.now()

        if callback:
            callback.on_subscription_filter_complete(feed, filter_result.final_selected_count)

        return SubscriptionFilterResult(
            subscription_id=feed.id,
            subscription_title=feed.title,
            filter_result=filter_result,
            articles_fetched=len(articles),
            fetch_time=fetch_time
        )

    def _get_rss_feed_articles(self, feed: RSSFeed, config: BatchFilterConfig) -> List[NewsArticle]:
        """获取RSS订阅源的文章"""
        try:
            # 从RSS feed中获取文章
            rss_articles = feed.articles

            # 应用时间过滤
            if config.hours_back:
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.hours_back)
                rss_articles = [
                    article for article in rss_articles
                    if article.published >= cutoff_time
                ]

            # 应用已读过滤
            if config.exclude_read:
                rss_articles = [
                    article for article in rss_articles
                    if not article.is_read
                ]

            # 限制数量
            if config.articles_per_subscription:
                rss_articles = rss_articles[:config.articles_per_subscription]

            # 转换为NewsArticle对象
            news_articles = []
            for rss_article in rss_articles:
                news_article = self._rss_article_to_news_article(rss_article, feed)
                news_articles.append(news_article)

            return news_articles

        except Exception as e:
            logger.error(f"Failed to get articles from RSS feed {feed.title}: {e}")
            return []

    def _rss_article_to_news_article(self, rss_article: RSSArticle, feed: RSSFeed) -> NewsArticle:
        """将RSSArticle转换为NewsArticle对象"""
        # 需要添加updated字段，如果RSS文章没有updated时间，使用published时间
        updated_time = getattr(rss_article, 'updated', None) or rss_article.published

        # 处理作者信息
        author = None
        if rss_article.author:
            from ..models.news import NewsAuthor
            author = NewsAuthor(name=rss_article.author)

        return NewsArticle(
            id=rss_article.id,
            title=rss_article.title,
            summary=rss_article.summary,
            content=rss_article.content,
            url=rss_article.url,
            published=rss_article.published,
            updated=updated_time,
            author=author,
            categories=[],  # RSS文章通常没有分类信息
            is_read=rss_article.is_read,
            is_starred=False,  # RSS文章通常没有星标功能
            feed_id=feed.id,
            feed_title=feed.title
        )

    def _apply_result_filters(self, filter_result: FilterChainResult, config: BatchFilterConfig):
        """应用结果过滤配置"""
        # 应用最小分数阈值
        if config.min_score_threshold is not None:
            if hasattr(filter_result, 'final_results') and filter_result.final_results:
                filter_result.final_results = [
                    result for result in filter_result.final_results
                    if getattr(result, 'final_score', 0) >= config.min_score_threshold
                ]
                filter_result.final_selected_count = len(filter_result.final_results)

        # 应用每个订阅源最大结果数限制
        if config.max_results_per_subscription is not None:
            if hasattr(filter_result, 'final_results') and filter_result.final_results:
                # 按分数排序并取前N个
                if hasattr(filter_result.final_results[0], 'final_score'):
                    filter_result.final_results.sort(
                        key=lambda x: getattr(x, 'final_score', 0),
                        reverse=True
                    )
                filter_result.final_results = filter_result.final_results[:config.max_results_per_subscription]
                filter_result.final_selected_count = len(filter_result.final_results)

    def _calculate_batch_statistics(self, batch_result: BatchFilterResult):
        """计算批量筛选统计信息"""
        batch_result.total_articles_fetched = sum(
            result.articles_fetched for result in batch_result.subscription_results
        )
        batch_result.total_articles_selected = sum(
            result.filter_result.final_selected_count for result in batch_result.subscription_results
        )

        # total_processing_time是只读属性，由processing_end_time - processing_start_time自动计算
        # 不需要手动设置


# 全局批量筛选管理器实例
custom_rss_batch_filter_manager = CustomRSSBatchFilterManager()
