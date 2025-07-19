"""
批量筛选服务 - 管理多个订阅源的自动切换和批量筛选
"""
import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models.news import NewsArticle
from ..models.subscription import Subscription
from ..services.news_service import NewsService
from ..services.subscription_service import SubscriptionService
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
    
    def on_subscription_start(self, subscription: Subscription, current: int, total: int):
        """开始处理订阅源"""
        pass
    
    def on_subscription_fetch_complete(self, subscription: Subscription, articles_count: int):
        """订阅源文章获取完成"""
        pass
    
    def on_subscription_filter_complete(self, subscription: Subscription, selected_count: int):
        """订阅源筛选完成"""
        pass
    
    def on_subscription_error(self, subscription: Subscription, error: str):
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
        self.subscription_filter: Optional[Callable[[Subscription], bool]] = None  # 订阅源过滤函数
        self.subscription_keywords: List[str] = []  # 订阅源标题关键词过滤
        
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


class BatchFilterManager:
    """批量筛选管理器"""
    
    def __init__(self, auth=None):
        self.news_service = NewsService(auth)
        self.subscription_service = SubscriptionService(auth)
        self.filter_service = FilterService()
        
    def filter_subscriptions_batch(self, 
                                 config: BatchFilterConfig,
                                 callback: Optional[BatchFilterProgressCallback] = None) -> BatchFilterResult:
        """
        批量筛选多个订阅源
        
        Args:
            config: 批量筛选配置
            callback: 进度回调
            
        Returns:
            批量筛选结果
        """
        start_time = datetime.now()
        
        # 获取订阅源列表
        subscriptions = self._get_filtered_subscriptions(config)
        
        if not subscriptions:
            logger.warning("No subscriptions found for filtering")
            return BatchFilterResult(
                total_subscriptions=0,
                processed_subscriptions=0,
                processing_start_time=start_time,
                processing_end_time=datetime.now()
            )
        
        logger.info(f"Starting batch filtering for {len(subscriptions)} subscriptions")
        
        # 创建批量结果对象
        batch_result = BatchFilterResult(
            total_subscriptions=len(subscriptions),
            processed_subscriptions=0,
            processing_start_time=start_time
        )
        
        # 通知开始批量筛选
        if callback:
            callback.on_batch_start(len(subscriptions))
        
        # 根据配置选择处理方式
        if config.enable_parallel and len(subscriptions) > 1:
            self._process_subscriptions_parallel(subscriptions, config, batch_result, callback)
        else:
            self._process_subscriptions_sequential(subscriptions, config, batch_result, callback)
        
        # 完成处理
        batch_result.processing_end_time = datetime.now()
        
        # 计算汇总统计
        self._calculate_batch_statistics(batch_result)
        
        # 通知批量筛选完成
        if callback:
            callback.on_batch_complete(batch_result)
        
        logger.info(f"Batch filtering completed: {batch_result.processed_subscriptions}/{batch_result.total_subscriptions} subscriptions processed")
        
        return batch_result
    
    def _get_filtered_subscriptions(self, config: BatchFilterConfig) -> List[Subscription]:
        """获取过滤后的订阅源列表"""
        try:
            all_subscriptions = self.subscription_service.get_all_subscriptions()
            
            # 应用订阅源过滤器
            filtered_subscriptions = []
            for subscription in all_subscriptions:
                # 自定义过滤函数
                if config.subscription_filter and not config.subscription_filter(subscription):
                    continue
                
                # 关键词过滤
                if config.subscription_keywords:
                    title_lower = subscription.title.lower()
                    if not any(keyword.lower() in title_lower for keyword in config.subscription_keywords):
                        continue
                
                filtered_subscriptions.append(subscription)
            
            # 限制数量
            if config.max_subscriptions:
                filtered_subscriptions = filtered_subscriptions[:config.max_subscriptions]
            
            return filtered_subscriptions
            
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {e}")
            return []
    
    def _process_subscriptions_sequential(self, 
                                        subscriptions: List[Subscription],
                                        config: BatchFilterConfig,
                                        batch_result: BatchFilterResult,
                                        callback: Optional[BatchFilterProgressCallback]):
        """顺序处理订阅源"""
        for i, subscription in enumerate(subscriptions):
            try:
                if callback:
                    callback.on_subscription_start(subscription, i + 1, len(subscriptions))
                
                sub_result = self._process_single_subscription(subscription, config, callback)
                batch_result.subscription_results.append(sub_result)
                batch_result.processed_subscriptions += 1
                
            except Exception as e:
                error_msg = f"Failed to process subscription {subscription.title}: {e}"
                logger.error(error_msg)
                batch_result.errors.append(error_msg)
                
                if callback:
                    callback.on_subscription_error(subscription, str(e))
    
    def _process_subscriptions_parallel(self, 
                                      subscriptions: List[Subscription],
                                      config: BatchFilterConfig,
                                      batch_result: BatchFilterResult,
                                      callback: Optional[BatchFilterProgressCallback]):
        """并行处理订阅源"""
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # 提交所有任务
            future_to_subscription = {
                executor.submit(self._process_single_subscription, subscription, config, callback): subscription
                for subscription in subscriptions
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_subscription):
                subscription = future_to_subscription[future]
                try:
                    sub_result = future.result()
                    batch_result.subscription_results.append(sub_result)
                    batch_result.processed_subscriptions += 1
                    
                except Exception as e:
                    error_msg = f"Failed to process subscription {subscription.title}: {e}"
                    logger.error(error_msg)
                    batch_result.errors.append(error_msg)
                    
                    if callback:
                        callback.on_subscription_error(subscription, str(e))
    
    def _process_single_subscription(self, 
                                   subscription: Subscription,
                                   config: BatchFilterConfig,
                                   callback: Optional[BatchFilterProgressCallback]) -> SubscriptionFilterResult:
        """处理单个订阅源"""
        logger.debug(f"Processing subscription: {subscription.title}")
        
        # 获取文章
        fetch_start = time.time()
        articles = self.news_service.get_articles_by_feed(
            feed_id=subscription.id,
            count=config.articles_per_subscription,
            exclude_read=config.exclude_read
        )
        fetch_time = time.time() - fetch_start
        
        if callback:
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
            callback.on_subscription_filter_complete(subscription, filter_result.final_selected_count)
        
        return SubscriptionFilterResult(
            subscription_id=subscription.id,
            subscription_title=subscription.title,
            filter_result=filter_result,
            articles_fetched=len(articles),
            fetch_time=fetch_time
        )
    
    def _apply_result_filters(self, filter_result: FilterChainResult, config: BatchFilterConfig):
        """应用结果过滤配置"""
        if not filter_result.selected_articles:
            return
        
        # 分数阈值过滤
        if config.min_score_threshold is not None:
            filter_result.selected_articles = [
                article for article in filter_result.selected_articles
                if article.final_score >= config.min_score_threshold
            ]
        
        # 数量限制
        if config.max_results_per_subscription is not None:
            # 按分数排序后取前N个
            filter_result.selected_articles.sort(key=lambda x: x.final_score, reverse=True)
            filter_result.selected_articles = filter_result.selected_articles[:config.max_results_per_subscription]
        
        # 更新最终选中数量
        filter_result.final_selected_count = len(filter_result.selected_articles)
    
    def _calculate_batch_statistics(self, batch_result: BatchFilterResult):
        """计算批量统计信息"""
        batch_result.total_articles_fetched = sum(
            sub_result.articles_fetched for sub_result in batch_result.subscription_results
        )
        batch_result.total_articles_selected = sum(
            sub_result.selected_count for sub_result in batch_result.subscription_results
        )
        batch_result.total_fetch_time = sum(
            sub_result.fetch_time for sub_result in batch_result.subscription_results
        )
        batch_result.total_filter_time = sum(
            sub_result.filter_result.total_processing_time for sub_result in batch_result.subscription_results
        )


    def get_sorted_results(self,
                         batch_result: BatchFilterResult,
                         config: BatchFilterConfig) -> List[CombinedFilterResult]:
        """获取排序后的所有结果"""
        all_articles = batch_result.all_selected_articles

        # 排序
        if config.sort_by == "final_score":
            all_articles.sort(key=lambda x: x.final_score, reverse=True)
        elif config.sort_by == "published":
            all_articles.sort(key=lambda x: x.article.published, reverse=True)
        elif config.sort_by == "subscription":
            all_articles.sort(key=lambda x: x.article.feed_title or "")

        return all_articles

    def export_results_to_dict(self, batch_result: BatchFilterResult) -> Dict[str, Any]:
        """将批量筛选结果导出为字典格式"""
        return {
            "summary": {
                "total_subscriptions": batch_result.total_subscriptions,
                "processed_subscriptions": batch_result.processed_subscriptions,
                "success_rate": batch_result.success_rate,
                "total_articles_fetched": batch_result.total_articles_fetched,
                "total_articles_selected": batch_result.total_articles_selected,
                "total_processing_time": batch_result.total_processing_time,
                "processing_start_time": batch_result.processing_start_time.isoformat(),
                "processing_end_time": batch_result.processing_end_time.isoformat() if batch_result.processing_end_time else None
            },
            "subscription_results": [
                {
                    "subscription_id": sub_result.subscription_id,
                    "subscription_title": sub_result.subscription_title,
                    "articles_fetched": sub_result.articles_fetched,
                    "articles_selected": sub_result.selected_count,
                    "fetch_time": sub_result.fetch_time,
                    "filter_time": sub_result.filter_result.total_processing_time,
                    "selected_articles": [
                        {
                            "id": article.article.id,
                            "title": article.article.title,
                            "summary": article.article.summary,
                            "url": article.article.url,
                            "published": article.article.published.isoformat(),
                            "feed_title": article.article.feed_title,
                            "final_score": article.final_score,
                            "keyword_score": article.keyword_result.relevance_score if article.keyword_result else None,
                            "ai_score": article.ai_result.evaluation.total_score if article.ai_result else None,
                            "reasoning": article.ai_result.evaluation.reasoning if article.ai_result else None
                        }
                        for article in sub_result.filter_result.selected_articles
                    ]
                }
                for sub_result in batch_result.subscription_results
            ],
            "errors": batch_result.errors,
            "warnings": batch_result.warnings
        }


class CLIBatchProgressCallback(BatchFilterProgressCallback):
    """命令行批量筛选进度回调"""

    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.total_subscriptions = 0
        self.current_subscription = 0

    def on_batch_start(self, total_subscriptions: int):
        """批量筛选开始"""
        self.total_subscriptions = total_subscriptions
        if self.show_progress:
            print(f"🚀 开始批量筛选 {total_subscriptions} 个订阅源...")

    def on_subscription_start(self, subscription: Subscription, current: int, total: int):
        """开始处理订阅源"""
        self.current_subscription = current
        if self.show_progress:
            print(f"📰 [{current}/{total}] 处理订阅源: {subscription.get_display_title()}")

    def on_subscription_fetch_complete(self, subscription: Subscription, articles_count: int):
        """订阅源文章获取完成"""
        if self.show_progress:
            print(f"   📥 获取到 {articles_count} 篇文章")

    def on_subscription_filter_complete(self, subscription: Subscription, selected_count: int):
        """订阅源筛选完成"""
        if self.show_progress:
            print(f"   ✅ 筛选完成，选中 {selected_count} 篇文章")

    def on_subscription_error(self, subscription: Subscription, error: str):
        """订阅源处理错误"""
        print(f"   ❌ 处理失败: {error}")

    def on_batch_complete(self, result: BatchFilterResult):
        """批量筛选完成"""
        if self.show_progress:
            print(f"\n🎉 批量筛选完成!")
            print(f"   处理订阅源: {result.processed_subscriptions}/{result.total_subscriptions}")
            print(f"   获取文章: {result.total_articles_fetched} 篇")
            print(f"   选中文章: {result.total_articles_selected} 篇")
            print(f"   总耗时: {result.total_processing_time:.2f} 秒")

            if result.errors:
                print(f"   错误数量: {len(result.errors)}")


# 全局批量筛选管理器实例
batch_filter_manager = BatchFilterManager()
