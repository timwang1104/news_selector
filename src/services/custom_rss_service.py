"""
自定义RSS订阅管理服务
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from .rss_service import RSSService
from ..models.rss import RSSFeed, RSSArticle, RSSSubscriptionManager

logger = logging.getLogger(__name__)


class CustomRSSService:
    """自定义RSS订阅管理服务"""
    
    def __init__(self):
        self.rss_service = RSSService()
        self.subscription_manager = RSSSubscriptionManager()
        self._lock = threading.Lock()
        
        # 加载已保存的订阅
        self.subscription_manager.load()
    
    def add_subscription(self, url: str, category: str = "默认") -> Tuple[bool, str]:
        """
        添加RSS订阅
        
        Args:
            url: RSS URL
            category: 分类
            
        Returns:
            (是否成功, 消息)
        """
        try:
            # 验证URL
            is_valid, error_msg = self.rss_service.validate_rss_url(url)
            if not is_valid:
                return False, error_msg
            
            # 检查是否已存在
            if self.subscription_manager.get_feed_by_url(url):
                return False, "该RSS源已存在"
            
            # 解析RSS feed
            feed = self.rss_service.parse_rss_feed(url)
            if not feed:
                return False, "无法解析RSS feed"
            
            # 设置分类和其他属性
            feed.category = category
            feed.last_fetched = datetime.now(timezone.utc)
            
            # 添加到管理器
            with self._lock:
                success = self.subscription_manager.add_feed(feed)
            
            if success:
                return True, f"成功添加RSS订阅: {feed.title}"
            else:
                return False, "添加失败"
                
        except Exception as e:
            logger.error(f"添加RSS订阅失败: {e}")
            return False, f"添加失败: {e}"
    
    def remove_subscription(self, feed_id: str) -> Tuple[bool, str]:
        """
        删除RSS订阅
        
        Args:
            feed_id: 订阅源ID
            
        Returns:
            (是否成功, 消息)
        """
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if not feed:
                    return False, "订阅源不存在"
                
                success = self.subscription_manager.remove_feed(feed_id)
            
            if success:
                return True, f"成功删除RSS订阅: {feed.title}"
            else:
                return False, "删除失败"
                
        except Exception as e:
            logger.error(f"删除RSS订阅失败: {e}")
            return False, f"删除失败: {e}"
    
    def get_all_subscriptions(self) -> List[RSSFeed]:
        """获取所有订阅源"""
        with self._lock:
            return self.subscription_manager.feeds.copy()
    
    def get_active_subscriptions(self) -> List[RSSFeed]:
        """获取激活的订阅源"""
        with self._lock:
            return self.subscription_manager.get_active_feeds()
    
    def get_subscriptions_by_category(self, category: str) -> List[RSSFeed]:
        """根据分类获取订阅源"""
        with self._lock:
            return self.subscription_manager.get_feeds_by_category(category)
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        with self._lock:
            return self.subscription_manager.get_all_categories()
    
    def update_subscription(self, feed_id: str, url: str, category: str = "默认") -> Tuple[bool, str]:
        """
        更新RSS订阅

        Args:
            feed_id: 订阅源ID
            url: 新的RSS URL
            category: 新的分类

        Returns:
            (是否成功, 消息)
        """
        try:
            with self._lock:
                # 获取现有订阅源
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if not feed:
                    return False, "订阅源不存在"

                # 如果URL发生变化，需要验证新URL
                if feed.url != url:
                    # 验证新URL
                    is_valid, error_msg = self.rss_service.validate_rss_url(url)
                    if not is_valid:
                        return False, error_msg

                    # 检查新URL是否与其他订阅源冲突
                    existing_feed = self.subscription_manager.get_feed_by_url(url)
                    if existing_feed and existing_feed.id != feed_id:
                        return False, "该RSS URL已被其他订阅源使用"

                    # 解析新的RSS feed获取最新信息
                    new_feed_data = self.rss_service.parse_rss_feed(url)
                    if not new_feed_data:
                        return False, "无法解析RSS源"

                    # 更新feed信息
                    feed.url = url
                    feed.title = new_feed_data.title
                    feed.description = new_feed_data.description
                    feed.link = new_feed_data.link

                # 更新分类
                feed.category = category
                feed.updated_at = datetime.now(timezone.utc)

                # 保存更改
                self.subscription_manager.save()

                return True, f"成功更新RSS订阅: {feed.title}"

        except Exception as e:
            logger.error(f"更新RSS订阅失败: {e}")
            return False, f"更新失败: {e}"

    def update_feed_category(self, feed_id: str, category: str) -> bool:
        """更新订阅源分类"""
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if feed:
                    feed.category = category
                    self.subscription_manager.save()
                    return True
            return False
        except Exception as e:
            logger.error(f"更新分类失败: {e}")
            return False
    
    def toggle_feed_active(self, feed_id: str) -> bool:
        """切换订阅源激活状态"""
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if feed:
                    feed.is_active = not feed.is_active
                    self.subscription_manager.save()
                    return True
            return False
        except Exception as e:
            logger.error(f"切换激活状态失败: {e}")
            return False
    
    def refresh_feed(self, feed_id: str) -> Tuple[bool, str, int]:
        """
        刷新单个订阅源
        
        Args:
            feed_id: 订阅源ID
            
        Returns:
            (是否成功, 消息, 新文章数量)
        """
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if not feed:
                    return False, "订阅源不存在", 0
                
                if not feed.is_active:
                    return False, "订阅源未激活", 0
            
            # 获取新文章
            new_articles = self.rss_service.get_feed_articles(feed.url)
            if new_articles is None:
                return False, "获取文章失败", 0
            
            # 更新文章列表
            with self._lock:
                # 获取现有文章ID
                existing_ids = {article.id for article in feed.articles}
                
                # 添加新文章
                new_count = 0
                for article in new_articles:
                    if article.id not in existing_ids:
                        feed.articles.append(article)
                        new_count += 1
                
                # 按发布时间排序，保留最新的100篇文章
                feed.articles.sort(key=lambda x: x.published, reverse=True)
                feed.articles = feed.articles[:100]
                
                # 更新最后获取时间
                feed.last_fetched = datetime.now(timezone.utc)
                
                # 保存
                self.subscription_manager.save()
            
            return True, f"刷新成功，获取到 {new_count} 篇新文章", new_count
            
        except Exception as e:
            logger.error(f"刷新订阅源失败: {e}")
            return False, f"刷新失败: {e}", 0
    
    def refresh_all_feeds(self, max_workers: int = 5) -> Dict[str, Tuple[bool, str, int]]:
        """
        刷新所有激活的订阅源
        
        Args:
            max_workers: 最大并发数
            
        Returns:
            {feed_id: (是否成功, 消息, 新文章数量)}
        """
        active_feeds = self.get_active_subscriptions()
        results = {}
        
        if not active_feeds:
            return results
        
        # 使用线程池并发刷新
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交任务
            future_to_feed = {
                executor.submit(self.refresh_feed, feed.id): feed.id 
                for feed in active_feeds
            }
            
            # 收集结果
            for future in as_completed(future_to_feed):
                feed_id = future_to_feed[future]
                try:
                    results[feed_id] = future.result()
                except Exception as e:
                    logger.error(f"刷新订阅源 {feed_id} 时出错: {e}")
                    results[feed_id] = (False, f"刷新出错: {e}", 0)
        
        return results
    
    def get_all_articles(self, category: Optional[str] = None, 
                        unread_only: bool = False,
                        hours_back: Optional[int] = None) -> List[RSSArticle]:
        """
        获取所有文章
        
        Args:
            category: 分类过滤
            unread_only: 仅未读文章
            hours_back: 多少小时内的文章
            
        Returns:
            文章列表
        """
        all_articles = []
        
        with self._lock:
            feeds = self.subscription_manager.feeds
            if category:
                feeds = [f for f in feeds if f.category == category]
        
        # 收集所有文章
        for feed in feeds:
            if not feed.is_active:
                continue
                
            for article in feed.articles:
                # 未读过滤
                if unread_only and article.is_read:
                    continue
                
                # 时间过滤
                if hours_back:
                    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                    if article.published < cutoff_time:
                        continue
                
                all_articles.append(article)
        
        # 按发布时间排序
        all_articles.sort(key=lambda x: x.published, reverse=True)
        
        return all_articles
    
    def mark_article_read(self, article_id: str, feed_id: str) -> bool:
        """标记文章为已读"""
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if feed:
                    for article in feed.articles:
                        if article.id == article_id:
                            article.is_read = True
                            self.subscription_manager.save()
                            return True
            return False
        except Exception as e:
            logger.error(f"标记文章已读失败: {e}")
            return False
    
    def toggle_article_star(self, article_id: str, feed_id: str) -> bool:
        """切换文章星标状态"""
        try:
            with self._lock:
                feed = self.subscription_manager.get_feed_by_id(feed_id)
                if feed:
                    for article in feed.articles:
                        if article.id == article_id:
                            article.is_starred = not article.is_starred
                            self.subscription_manager.save()
                            return True
            return False
        except Exception as e:
            logger.error(f"切换文章星标失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            feeds = self.subscription_manager.feeds
            
            total_feeds = len(feeds)
            active_feeds = len([f for f in feeds if f.is_active])
            total_articles = sum(len(f.articles) for f in feeds)
            unread_articles = sum(f.get_unread_count() for f in feeds)
            starred_articles = sum(
                len([a for a in f.articles if a.is_starred]) for f in feeds
            )
            
            categories = self.subscription_manager.get_all_categories()
            
            return {
                'total_feeds': total_feeds,
                'active_feeds': active_feeds,
                'total_articles': total_articles,
                'unread_articles': unread_articles,
                'starred_articles': starred_articles,
                'categories': categories,
                'category_count': len(categories)
            }
