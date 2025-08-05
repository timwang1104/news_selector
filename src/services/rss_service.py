"""
RSS解析服务 - 处理RSS feed的解析和文章提取
"""
import feedparser
import requests
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
import re
import logging

from ..models.rss import RSSFeed, RSSArticle

logger = logging.getLogger(__name__)


class RSSService:
    """RSS解析服务"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'News Selector RSS Reader/1.0'
        })
    
    def validate_rss_url(self, url: str) -> Tuple[bool, str]:
        """
        验证RSS URL是否有效
        
        Args:
            url: RSS URL
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 基本URL格式验证
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "无效的URL格式"
            
            # 尝试获取RSS内容
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            # 解析RSS内容
            feed = feedparser.parse(response.content)
            
            # 检查是否是有效的RSS/Atom feed
            if feed.bozo and feed.bozo_exception:
                # 如果有解析错误，但仍然有entries，可能是格式不完全标准但可用
                if not feed.entries:
                    return False, f"RSS解析错误: {feed.bozo_exception}"
            
            if not hasattr(feed, 'feed') or not feed.entries:
                return False, "不是有效的RSS/Atom feed或没有文章"
            
            return True, ""
            
        except requests.RequestException as e:
            return False, f"网络请求失败: {e}"
        except Exception as e:
            return False, f"验证失败: {e}"
    
    def parse_rss_feed(self, url: str) -> Optional[RSSFeed]:
        """
        解析RSS feed
        
        Args:
            url: RSS URL
            
        Returns:
            RSSFeed对象，失败时返回None
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            
            if feed.bozo and feed.bozo_exception and not feed.entries:
                logger.error(f"RSS解析失败: {feed.bozo_exception}")
                return None
            
            # 提取feed信息
            feed_info = feed.feed
            title = getattr(feed_info, 'title', url)
            description = getattr(feed_info, 'description', '')
            link = getattr(feed_info, 'link', '')
            
            # 获取更新时间
            updated = None
            if hasattr(feed_info, 'updated_parsed') and feed_info.updated_parsed:
                updated = datetime(*feed_info.updated_parsed[:6], tzinfo=timezone.utc)
            
            # 解析文章
            articles = []
            for entry in feed.entries:
                article = self._parse_rss_entry(entry, url)
                if article:
                    articles.append(article)
            
            return RSSFeed(
                url=url,
                title=title,
                description=description,
                link=link,
                updated=updated or datetime.now(timezone.utc),
                articles=articles
            )
            
        except Exception as e:
            logger.error(f"解析RSS feed失败: {e}")
            return None
    
    def _parse_rss_entry(self, entry: Any, feed_url: str) -> Optional[RSSArticle]:
        """
        解析RSS条目为文章对象
        
        Args:
            entry: feedparser解析的条目
            feed_url: RSS feed URL
            
        Returns:
            RSSArticle对象，失败时返回None
        """
        try:
            # 基本信息
            title = getattr(entry, 'title', '无标题')
            link = getattr(entry, 'link', '')
            
            # 内容
            summary = ''
            content = ''
            
            if hasattr(entry, 'summary'):
                summary = self._clean_html(entry.summary)
            
            if hasattr(entry, 'content') and entry.content:
                # content可能是列表
                if isinstance(entry.content, list) and entry.content:
                    content = self._clean_html(entry.content[0].value)
                else:
                    content = self._clean_html(str(entry.content))
            elif hasattr(entry, 'description'):
                content = self._clean_html(entry.description)
            else:
                content = summary
            
            # 发布时间
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            else:
                published = datetime.now(timezone.utc)
            
            # 作者
            author = ''
            if hasattr(entry, 'author'):
                author = entry.author
            elif hasattr(entry, 'authors') and entry.authors:
                author = entry.authors[0].get('name', '')
            
            # 生成唯一ID
            article_id = getattr(entry, 'id', '') or getattr(entry, 'guid', '') or link
            if not article_id:
                # 如果没有ID，使用标题和链接的组合生成
                article_id = f"{feed_url}#{hash(title + link)}"
            
            return RSSArticle(
                id=article_id,
                title=title,
                summary=summary,
                content=content,
                url=link,
                published=published,
                author=author,
                feed_url=feed_url
            )
            
        except Exception as e:
            logger.error(f"解析RSS条目失败: {e}")
            return None
    
    def _clean_html(self, html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        
        Args:
            html_content: HTML内容
            
        Returns:
            清理后的文本
        """
        if not html_content:
            return ''
        
        # A simple approach to remove HTML tags
        clean = re.sub('<.*?>', '', html_content)
        return clean.strip()

    def fetch_articles_for_analysis(self, url: str) -> List[Dict[str, Any]]:
        """
        Fetches articles from an RSS feed and returns them as a list of dicts
        suitable for preference analysis storage.

        Args:
            url: The RSS feed URL.

        Returns:
            A list of article dictionaries, or an empty list if fetching fails.
        """
        rss_feed = self.parse_rss_feed(url)
        if not rss_feed or not rss_feed.articles:
            logger.warning(f"Could not fetch or parse RSS feed for analysis: {url}")
            return []

        articles_for_db = []
        for article in rss_feed.articles:
            articles_for_db.append({
                'title': article.title,
                'content': self._clean_html(article.content or article.summary),
                'published_at': article.published,
                'url': article.url
            })
        
        return articles_for_db
        
        # 移除HTML标签
        clean_text = re.sub(r'<[^>]+>', '', html_content)
        
        # 解码HTML实体
        import html
        clean_text = html.unescape(clean_text)
        
        # 清理多余的空白字符
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def get_feed_articles(self, url: str, max_articles: Optional[int] = None) -> List[RSSArticle]:
        """
        获取RSS feed的文章列表
        
        Args:
            url: RSS URL
            max_articles: 最大文章数量
            
        Returns:
            文章列表
        """
        feed = self.parse_rss_feed(url)
        if not feed:
            return []
        
        articles = feed.articles
        if max_articles and len(articles) > max_articles:
            articles = articles[:max_articles]
        
        return articles
