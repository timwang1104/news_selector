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
from ..services.filter_service import get_filter_service, FilterProgressCallback
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

        # 去重配置
        self.enable_global_deduplication: bool = True  # 是否启用全局去重（跨新闻源）
        self.deduplication_threshold: float = 0.8  # 去重相似度阈值
        self.deduplication_time_window: int = 72  # 去重时间窗口（小时）

        # AI语义去重配置
        self.enable_ai_semantic_deduplication: bool = True  # 是否启用AI语义去重
        self.ai_semantic_threshold: float = 0.85  # AI语义相似度阈值
        self.ai_semantic_time_window: int = 48  # AI语义去重时间窗口（小时）

        # 结果配置
        self.max_results_per_subscription: Optional[int] = None  # 每个订阅源最大结果数
        self.min_score_threshold: Optional[float] = None  # 最小分数阈值
        self.max_total_articles: Optional[int] = None  # 批量筛选最大文章数限制
        self.sort_by: str = "final_score"  # 排序方式: final_score, published, subscription
        self.group_by_subscription: bool = True  # 是否按订阅源分组显示

    def set_ai_filter_rules(self, min_score: int = 20, max_articles: int = 30):
        """
        设置AI筛选规则的便捷方法

        Args:
            min_score: AI筛选最低分数阈值（默认20分）
            max_articles: 批量筛选最大文章数限制（默认30篇）
        """
        self.max_total_articles = max_articles
        print(f"🎯 设置AI筛选规则: 最低分数 {min_score} 分，最大文章数 {max_articles} 篇")

        # 同时更新FilterService的AI配置
        try:
            get_filter_service().update_config("ai", min_score_threshold=min_score, batch_max_articles=max_articles)
            print(f"✅ AI筛选配置已更新")
        except Exception as e:
            print(f"⚠️  更新AI筛选配置失败: {e}")




class CustomRSSBatchFilterManager:
    """自定义RSS批量筛选管理器"""

    def __init__(self):
        self.custom_rss_service = CustomRSSService()
        self.filter_service = get_filter_service()

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

        # 处理订阅源 - 支持全局去重
        if config.enable_global_deduplication:
            self._process_rss_feeds_with_global_deduplication(rss_feeds, config, batch_result, callback)
        else:
            # 传统处理方式（每个源单独去重）
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

    def _process_rss_feeds_with_global_deduplication(self,
                                                   feeds: List[RSSFeed],
                                                   config: BatchFilterConfig,
                                                   batch_result: BatchFilterResult,
                                                   callback: Optional[BatchFilterProgressCallback]):
        """使用全局去重处理RSS订阅源"""
        logger.info(f"Starting global deduplication processing for {len(feeds)} RSS feeds")

        # 第一阶段：收集所有文章
        all_articles = []
        articles_by_source = {}  # 记录每篇文章来自哪个源

        if callback:
            callback.on_batch_start(len(feeds))

        print(f"🔄 第一阶段：收集所有新闻源的文章...")

        for i, feed in enumerate(feeds):
            try:
                if callback:
                    subscription = self._rss_feed_to_subscription(feed)
                    callback.on_subscription_start(subscription, i + 1, len(feeds))

                # 获取文章但不进行筛选
                articles = self._get_rss_feed_articles(feed, config)

                # 记录文章来源
                for article in articles:
                    articles_by_source[article.id] = {
                        'feed_id': feed.id,
                        'feed_title': feed.title,
                        'article': article
                    }

                all_articles.extend(articles)

                print(f"   📰 {feed.title}: 获取 {len(articles)} 篇文章")

                if callback:
                    callback.on_subscription_filter_complete(feed, len(articles))

            except Exception as e:
                logger.error(f"Failed to fetch articles from feed {feed.title}: {e}")
                print(f"❌ 获取文章失败 {feed.title}: {e}")

                # 创建空结果
                empty_result = SubscriptionFilterResult(
                    subscription_id=feed.id,
                    subscription_title=feed.title,
                    filter_result=FilterChainResult(total_articles=0, processing_start_time=datetime.now()),
                    articles_fetched=0,
                    fetch_time=0.0
                )
                batch_result.subscription_results.append(empty_result)
                batch_result.processed_subscriptions += 1

        print(f"✅ 收集完成：共获取 {len(all_articles)} 篇文章")

        # 第二阶段：全局去重和筛选
        if all_articles:
            print(f"🔄 第二阶段：全局去重和筛选...")

            # 通知开始全局去重
            if callback and hasattr(callback, 'on_global_deduplication_start'):
                callback.on_global_deduplication_start(len(all_articles))

            # 临时设置AI语义去重配置到筛选服务
            self._apply_ai_semantic_config_to_filter_service(config)

            # 执行全局筛选（包含去重和AI语义去重）
            filter_result = self.filter_service.filter_articles(
                articles=all_articles,
                filter_type=config.filter_type,
                enable_deduplication=True  # 强制启用基础去重
            )

            print(f"✅ 全局筛选完成：")
            print(f"   原始文章：{filter_result.original_articles_count}")
            print(f"   去重后：{filter_result.deduplicated_articles_count}")
            print(f"   去除重复：{filter_result.removed_duplicates_count}")
            print(f"   最终筛选：{len(filter_result.selected_articles)}")

            # 通知去重完成
            if callback and hasattr(callback, 'on_global_deduplication_complete'):
                callback.on_global_deduplication_complete(
                    filter_result.original_articles_count,
                    filter_result.deduplicated_articles_count,
                    filter_result.removed_duplicates_count
                )

            # 通知筛选完成
            if callback and hasattr(callback, 'on_global_filtering_complete'):
                callback.on_global_filtering_complete(len(filter_result.selected_articles))

            # 第三阶段：按来源分组结果
            print(f"🔄 第三阶段：按来源分组结果...")

            # 通知开始分组
            if callback and hasattr(callback, 'on_result_distribution_start'):
                callback.on_result_distribution_start()

            self._distribute_results_by_source(filter_result, articles_by_source, feeds, batch_result, config)

            # 通知分组完成
            if callback and hasattr(callback, 'on_result_distribution_complete'):
                callback.on_result_distribution_complete()

        else:
            print(f"⚠️  没有获取到任何文章")
            # 为所有订阅源创建空结果
            for feed in feeds:
                empty_result = SubscriptionFilterResult(
                    subscription_id=feed.id,
                    subscription_title=feed.title,
                    filter_result=FilterChainResult(total_articles=0, processing_start_time=datetime.now()),
                    articles_fetched=0,
                    fetch_time=0.0
                )
                batch_result.subscription_results.append(empty_result)
                batch_result.processed_subscriptions += 1

    def _distribute_results_by_source(self,
                                    global_filter_result: FilterChainResult,
                                    articles_by_source: Dict,
                                    feeds: List[RSSFeed],
                                    batch_result: BatchFilterResult,
                                    config: BatchFilterConfig):
        """将全局筛选结果按来源分组"""

        # 为每个订阅源创建结果统计
        source_stats = {}
        for feed in feeds:
            source_stats[feed.id] = {
                'feed': feed,
                'original_articles': 0,
                'selected_articles': [],
                'rejected_articles': []
            }

        # 统计原始文章数
        for article_id, source_info in articles_by_source.items():
            feed_id = source_info['feed_id']
            if feed_id in source_stats:
                source_stats[feed_id]['original_articles'] += 1

        # 分配筛选通过的文章
        for combined_result in global_filter_result.selected_articles:
            # CombinedFilterResult对象，需要访问其article属性
            article_id = combined_result.article.id
            if article_id in articles_by_source:
                source_info = articles_by_source[article_id]
                feed_id = source_info['feed_id']
                if feed_id in source_stats:
                    source_stats[feed_id]['selected_articles'].append(combined_result)

        # 分配被拒绝的文章（如果需要）
        if hasattr(global_filter_result, 'rejected_articles') and global_filter_result.rejected_articles:
            for combined_result in global_filter_result.rejected_articles:
                # CombinedFilterResult对象，需要访问其article属性
                article_id = combined_result.article.id
                if article_id in articles_by_source:
                    source_info = articles_by_source[article_id]
                    feed_id = source_info['feed_id']
                    if feed_id in source_stats:
                        source_stats[feed_id]['rejected_articles'].append(combined_result)

        # 为每个订阅源创建SubscriptionFilterResult
        for feed_id, stats in source_stats.items():
            feed = stats['feed']

            # 创建该源的筛选结果
            source_filter_result = FilterChainResult(
                total_articles=stats['original_articles'],
                processing_start_time=global_filter_result.processing_start_time
            )

            # 设置选中的文章
            source_filter_result.selected_articles = stats['selected_articles']

            # 复制全局去重统计信息
            source_filter_result.original_articles_count = global_filter_result.original_articles_count
            source_filter_result.deduplicated_articles_count = global_filter_result.deduplicated_articles_count
            source_filter_result.removed_duplicates_count = global_filter_result.removed_duplicates_count
            source_filter_result.deduplication_stats = global_filter_result.deduplication_stats

            # 设置筛选统计
            source_filter_result.final_selected_count = len(stats['selected_articles'])
            source_filter_result.processing_end_time = global_filter_result.processing_end_time

            # 应用结果过滤
            self._apply_result_filters(source_filter_result, config)

            # 创建订阅源结果
            subscription_result = SubscriptionFilterResult(
                subscription_id=feed.id,
                subscription_title=feed.title,
                filter_result=source_filter_result,
                articles_fetched=stats['original_articles'],
                fetch_time=0.0  # 全局处理模式下无单独获取时间
            )

            batch_result.subscription_results.append(subscription_result)
            batch_result.processed_subscriptions += 1

            print(f"   📊 {feed.title}: 原始{stats['original_articles']}篇 → 筛选{len(stats['selected_articles'])}篇")

    def _apply_ai_semantic_config_to_filter_service(self, batch_config: BatchFilterConfig):
        """将AI语义去重配置应用到筛选服务"""
        try:
            # 获取筛选服务的筛选链
            filter_chain = self.filter_service.filter_chain
            if not filter_chain:
                print(f"   ⚠️  筛选链未初始化，跳过AI语义去重配置")
                return

            # 从批量配置中读取AI语义去重设置
            enable_ai_semantic = getattr(batch_config, 'enable_ai_semantic_deduplication', True)
            ai_semantic_threshold = getattr(batch_config, 'ai_semantic_threshold', 0.85)
            ai_semantic_time_window = getattr(batch_config, 'ai_semantic_time_window', 48)

            # 也从配置文件读取AI语义去重设置
            try:
                import json
                from pathlib import Path

                config_file = Path("config/filter_config.json")
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        file_config = json.load(f)

                        # 读取AI语义去重配置
                        if 'ai_semantic_deduplication' in file_config:
                            ai_dedup_config = file_config['ai_semantic_deduplication']
                            enable_ai_semantic = ai_dedup_config.get('enabled', enable_ai_semantic)
                            ai_semantic_threshold = ai_dedup_config.get('threshold', ai_semantic_threshold)
                            ai_semantic_time_window = ai_dedup_config.get('time_window_hours', ai_semantic_time_window)

                        # 读取chain配置中的AI语义去重设置
                        if 'chain' in file_config:
                            chain_config = file_config['chain']
                            if 'enable_ai_semantic_deduplication' in chain_config:
                                enable_ai_semantic = chain_config['enable_ai_semantic_deduplication']
                            if 'ai_semantic_threshold' in chain_config:
                                ai_semantic_threshold = chain_config['ai_semantic_threshold']
                            if 'ai_semantic_time_window' in chain_config:
                                ai_semantic_time_window = chain_config['ai_semantic_time_window']

            except Exception as e:
                logger.warning(f"Failed to load AI semantic deduplication config from file: {e}")

            # 应用配置到筛选链
            if hasattr(filter_chain, 'config'):
                filter_chain.config.enable_ai_semantic_deduplication = enable_ai_semantic
                filter_chain.config.ai_semantic_threshold = ai_semantic_threshold
                filter_chain.config.ai_semantic_time_window = ai_semantic_time_window

            print(f"   🧠 AI语义去重配置: 启用={enable_ai_semantic}, 阈值={ai_semantic_threshold}, 窗口={ai_semantic_time_window}小时")

        except Exception as e:
            logger.error(f"Failed to apply AI semantic config to filter service: {e}")
            print(f"   ❌ AI语义去重配置应用失败: {e}")

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
                # 检查是否已达到文章数量限制
                if config.max_total_articles:
                    current_total = sum(r.filter_result.final_selected_count for r in batch_result.subscription_results)
                    if current_total >= config.max_total_articles:
                        print(f"🛑 批量筛选提前退出: 已达到文章数量限制 {config.max_total_articles} 篇")
                        logger.info(f"Batch filtering stopped: reached max articles limit ({config.max_total_articles})")
                        batch_result.warnings.append(f"已达到最大文章数量限制 {config.max_total_articles}，提前退出筛选")
                        break

                if callback:
                    subscription = self._rss_feed_to_subscription(feed)
                    callback.on_subscription_start(subscription, i + 1, len(feeds))

                result = self._process_single_rss_feed(feed, config, callback)
                batch_result.subscription_results.append(result)
                batch_result.processed_subscriptions += 1

                # 处理完成后再次检查文章数量
                if config.max_total_articles:
                    current_total = sum(r.filter_result.final_selected_count for r in batch_result.subscription_results)
                    print(f"📊 当前累计筛选文章数: {current_total}/{config.max_total_articles}")
                    if current_total >= config.max_total_articles:
                        print(f"🛑 批量筛选达到限制: 累计筛选了 {current_total} 篇文章")
                        logger.info(f"Batch filtering completed: reached max articles limit ({current_total} articles)")
                        break

            except Exception as e:
                logger.error(f"Error processing RSS feed {feed.title}: {e}")
                batch_result.errors.append(f"RSS feed {feed.title}: {e}")

    def _process_rss_feeds_parallel(self,
                                  feeds: List[RSSFeed],
                                  config: BatchFilterConfig,
                                  batch_result: BatchFilterResult,
                                  callback: Optional[BatchFilterProgressCallback]):
        """并行处理RSS订阅源"""
        # 如果设置了文章数量限制，使用顺序处理以便更好地控制
        if config.max_total_articles:
            print(f"⚠️  检测到文章数量限制 ({config.max_total_articles})，切换到顺序处理模式")
            logger.info(f"Switching to sequential processing due to max articles limit: {config.max_total_articles}")
            self._process_rss_feeds_sequential(feeds, config, batch_result, callback)
            return

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

    def _rss_feed_to_subscription(self, feed: RSSFeed):
        """将RSS Feed转换为订阅源对象（用于回调）"""
        # 创建一个简单的订阅源对象，包含必要的信息
        class SimpleSubscription:
            def __init__(self, feed: RSSFeed):
                self.id = feed.id
                self.title = feed.title
                self.url = feed.url
                self.category = getattr(feed, 'category', '默认')
                self.description = getattr(feed, 'description', '')

        return SimpleSubscription(feed)

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
