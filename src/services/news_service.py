"""
新闻服务 - 处理新闻获取和管理的业务逻辑
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from ..api.client import InoreaderClient, InoreaderAPIError
from ..models.news import NewsArticle
from ..models.subscription import StreamInfo


class NewsService:
    """新闻服务"""

    def __init__(self, auth=None, use_cache: bool = True):
        self.client = InoreaderClient(auth, use_cache=use_cache)
        self.use_cache = use_cache
    
    def get_latest_articles(self, 
                          count: Optional[int] = None,
                          exclude_read: bool = True,
                          hours_back: Optional[int] = None) -> List[NewsArticle]:
        """
        获取最新文章列表
        
        Args:
            count: 文章数量限制
            exclude_read: 是否排除已读文章
            hours_back: 获取多少小时内的文章
        
        Returns:
            文章列表
        """
        try:
            # 计算开始时间
            start_time = None
            if hours_back:
                start_datetime = datetime.now() - timedelta(hours=hours_back)
                start_time = int(start_datetime.timestamp())
            
            # 获取阅读列表
            response = self.client.get_reading_list(count)
            
            # 解析文章
            articles = []
            for item in response.get('items', []):
                try:
                    article = NewsArticle.from_api_response(item)
                    
                    # 时间过滤
                    if start_time and article.published.timestamp() < start_time:
                        continue
                    
                    # 已读过滤
                    if exclude_read and article.is_read:
                        continue
                    
                    articles.append(article)
                except Exception as e:
                    print(f"解析文章失败: {e}")
                    continue
            
            # 按发布时间排序（最新的在前）
            articles.sort(key=lambda x: x.published, reverse=True)
            
            return articles
            
        except InoreaderAPIError as e:
            print(f"获取文章失败: {e}")
            return []
    
    def get_articles_by_feed(self, 
                           feed_id: str,
                           count: Optional[int] = None,
                           exclude_read: bool = True) -> List[NewsArticle]:
        """
        获取指定订阅源的文章
        
        Args:
            feed_id: 订阅源ID
            count: 文章数量限制
            exclude_read: 是否排除已读文章
        
        Returns:
            文章列表
        """
        try:
            response = self.client.get_stream_contents(
                stream_id=feed_id,
                count=count,
                exclude_read=exclude_read
            )
            
            articles = []
            for item in response.get('items', []):
                try:
                    article = NewsArticle.from_api_response(item)
                    articles.append(article)
                except Exception as e:
                    print(f"解析文章失败: {e}")
                    continue
            
            # 按发布时间排序
            articles.sort(key=lambda x: x.published, reverse=True)
            
            return articles
            
        except InoreaderAPIError as e:
            print(f"获取订阅源文章失败: {e}")
            return []
    
    def get_starred_articles(self, count: Optional[int] = None) -> List[NewsArticle]:
        """获取加星标的文章"""
        try:
            response = self.client.get_starred_items(count)
            
            articles = []
            for item in response.get('items', []):
                try:
                    article = NewsArticle.from_api_response(item)
                    articles.append(article)
                except Exception as e:
                    print(f"解析文章失败: {e}")
                    continue
            
            # 按发布时间排序
            articles.sort(key=lambda x: x.published, reverse=True)
            
            return articles
            
        except InoreaderAPIError as e:
            print(f"获取星标文章失败: {e}")
            return []
    
    def mark_article_as_read(self, article_id: str) -> bool:
        """标记文章为已读"""
        try:
            return self.client.mark_as_read(article_id)
        except InoreaderAPIError as e:
            print(f"标记文章已读失败: {e}")
            return False
    
    def mark_article_as_unread(self, article_id: str) -> bool:
        """标记文章为未读"""
        try:
            return self.client.mark_as_unread(article_id)
        except InoreaderAPIError as e:
            print(f"标记文章未读失败: {e}")
            return False
    
    def star_article(self, article_id: str) -> bool:
        """给文章加星标"""
        try:
            return self.client.add_star(article_id)
        except InoreaderAPIError as e:
            print(f"添加星标失败: {e}")
            return False
    
    def unstar_article(self, article_id: str) -> bool:
        """移除文章星标"""
        try:
            return self.client.remove_star(article_id)
        except InoreaderAPIError as e:
            print(f"移除星标失败: {e}")
            return False
    
    def search_articles(self, 
                       keyword: str,
                       articles: Optional[List[NewsArticle]] = None) -> List[NewsArticle]:
        """
        在文章中搜索关键词
        
        Args:
            keyword: 搜索关键词
            articles: 要搜索的文章列表，如果为None则搜索最新文章
        
        Returns:
            匹配的文章列表
        """
        if articles is None:
            articles = self.get_latest_articles(count=200, exclude_read=False)
        
        keyword_lower = keyword.lower()
        matched_articles = []
        
        for article in articles:
            # 在标题、摘要和内容中搜索
            if (keyword_lower in article.title.lower() or
                keyword_lower in article.summary.lower() or
                keyword_lower in article.content.lower() or
                (article.feed_title and keyword_lower in article.feed_title.lower())):
                matched_articles.append(article)
        
        return matched_articles
    
    def filter_articles_by_feed(self, 
                               articles: List[NewsArticle],
                               feed_title: str) -> List[NewsArticle]:
        """按订阅源标题过滤文章"""
        feed_title_lower = feed_title.lower()
        return [
            article for article in articles
            if article.feed_title and feed_title_lower in article.feed_title.lower()
        ]
    
    def get_articles_summary(self, articles: List[NewsArticle]) -> Dict[str, Any]:
        """获取文章列表的统计摘要"""
        if not articles:
            return {
                'total_count': 0,
                'unread_count': 0,
                'starred_count': 0,
                'feeds': {}
            }
        
        total_count = len(articles)
        unread_count = sum(1 for article in articles if not article.is_read)
        starred_count = sum(1 for article in articles if article.is_starred)
        
        # 按订阅源统计
        feeds = {}
        for article in articles:
            if article.feed_title:
                if article.feed_title not in feeds:
                    feeds[article.feed_title] = {
                        'count': 0,
                        'unread': 0,
                        'starred': 0
                    }
                feeds[article.feed_title]['count'] += 1
                if not article.is_read:
                    feeds[article.feed_title]['unread'] += 1
                if article.is_starred:
                    feeds[article.feed_title]['starred'] += 1
        
        return {
            'total_count': total_count,
            'unread_count': unread_count,
            'starred_count': starred_count,
            'feeds': feeds
        }

    def refresh_cache(self):
        """刷新缓存 - 清除所有缓存数据"""
        self.client.clear_cache()

    def refresh_articles_cache(self):
        """刷新文章缓存"""
        # 清除相关的缓存
        self.client.clear_cache('stream/contents/user/-/state/com.google/reading-list')
        self.client.clear_cache('stream/contents/user/-/state/com.google/starred')

    def refresh_feed_cache(self, feed_id: str):
        """刷新特定订阅源的缓存"""
        self.client.clear_cache(f'stream/contents/feed/{feed_id}')

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        cache_stats = self.client.get_cache_stats()
        region_info = self.client.get_current_region_info()

        return {
            'cache_stats': cache_stats,
            'current_region': region_info,
            'cache_enabled': self.use_cache
        }
