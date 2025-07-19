"""
RSS相关数据模型
"""
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class RSSArticle:
    """RSS文章模型"""
    id: str
    title: str
    summary: str
    content: str
    url: str
    published: datetime
    author: str = ""
    feed_url: str = ""
    is_read: bool = False
    is_starred: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换datetime为ISO格式字符串
        data['published'] = self.published.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSArticle':
        """从字典创建对象"""
        # 转换ISO格式字符串为datetime
        if isinstance(data.get('published'), str):
            data['published'] = datetime.fromisoformat(data['published'])
        return cls(**data)
    
    def get_display_title(self, max_length: int = 80) -> str:
        """获取显示用的标题"""
        if len(self.title) <= max_length:
            return self.title
        return self.title[:max_length-3] + "..."
    
    def get_short_summary(self, max_length: int = 200) -> str:
        """获取简短摘要"""
        if len(self.summary) <= max_length:
            return self.summary
        return self.summary[:max_length-3] + "..."


@dataclass
class RSSFeed:
    """RSS订阅源模型"""
    url: str
    title: str
    description: str = ""
    link: str = ""
    updated: Optional[datetime] = None
    articles: List[RSSArticle] = field(default_factory=list)
    
    # 本地管理字段
    id: Optional[str] = None  # 本地唯一标识
    added_time: Optional[datetime] = None  # 添加时间
    last_fetched: Optional[datetime] = None  # 最后获取时间
    fetch_interval: int = 3600  # 获取间隔（秒），默认1小时
    is_active: bool = True  # 是否激活
    category: str = "默认"  # 分类
    
    def __post_init__(self):
        if self.id is None:
            # 生成唯一ID
            import hashlib
            self.id = hashlib.md5(self.url.encode()).hexdigest()[:16]
        
        if self.added_time is None:
            self.added_time = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        
        # 转换datetime字段
        if self.updated:
            data['updated'] = self.updated.isoformat()
        if self.added_time:
            data['added_time'] = self.added_time.isoformat()
        if self.last_fetched:
            data['last_fetched'] = self.last_fetched.isoformat()
        
        # 转换文章列表
        data['articles'] = [article.to_dict() for article in self.articles]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RSSFeed':
        """从字典创建对象"""
        # 转换datetime字段
        if isinstance(data.get('updated'), str):
            data['updated'] = datetime.fromisoformat(data['updated'])
        if isinstance(data.get('added_time'), str):
            data['added_time'] = datetime.fromisoformat(data['added_time'])
        if isinstance(data.get('last_fetched'), str):
            data['last_fetched'] = datetime.fromisoformat(data['last_fetched'])
        
        # 转换文章列表
        articles_data = data.pop('articles', [])
        feed = cls(**data)
        feed.articles = [RSSArticle.from_dict(article_data) for article_data in articles_data]
        
        return feed
    
    def get_display_title(self, max_length: int = 50) -> str:
        """获取显示用的标题"""
        if len(self.title) <= max_length:
            return self.title
        return self.title[:max_length-3] + "..."
    
    def get_unread_count(self) -> int:
        """获取未读文章数量"""
        return sum(1 for article in self.articles if not article.is_read)
    
    def get_recent_articles(self, hours: int = 24) -> List[RSSArticle]:
        """获取最近的文章"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [article for article in self.articles if article.published > cutoff_time]
    
    def should_fetch(self) -> bool:
        """判断是否应该获取新文章"""
        if not self.is_active:
            return False
        
        if not self.last_fetched:
            return True
        
        time_since_fetch = datetime.now(timezone.utc) - self.last_fetched
        return time_since_fetch.total_seconds() >= self.fetch_interval


@dataclass
class RSSSubscriptionManager:
    """RSS订阅管理器"""
    feeds: List[RSSFeed] = field(default_factory=list)
    storage_path: Optional[Path] = None
    
    def __post_init__(self):
        if self.storage_path is None:
            # 默认存储路径
            self.storage_path = Path.home() / ".news_selector" / "rss_subscriptions.json"
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def add_feed(self, feed: RSSFeed) -> bool:
        """添加订阅源"""
        # 检查是否已存在
        if any(f.url == feed.url for f in self.feeds):
            return False
        
        self.feeds.append(feed)
        self.save()
        return True
    
    def remove_feed(self, feed_id: str) -> bool:
        """删除订阅源"""
        original_count = len(self.feeds)
        self.feeds = [f for f in self.feeds if f.id != feed_id]
        
        if len(self.feeds) < original_count:
            self.save()
            return True
        return False
    
    def get_feed_by_id(self, feed_id: str) -> Optional[RSSFeed]:
        """根据ID获取订阅源"""
        for feed in self.feeds:
            if feed.id == feed_id:
                return feed
        return None
    
    def get_feed_by_url(self, url: str) -> Optional[RSSFeed]:
        """根据URL获取订阅源"""
        for feed in self.feeds:
            if feed.url == url:
                return feed
        return None
    
    def get_active_feeds(self) -> List[RSSFeed]:
        """获取激活的订阅源"""
        return [f for f in self.feeds if f.is_active]
    
    def get_feeds_by_category(self, category: str) -> List[RSSFeed]:
        """根据分类获取订阅源"""
        return [f for f in self.feeds if f.category == category]
    
    def get_all_categories(self) -> List[str]:
        """获取所有分类"""
        categories = set(f.category for f in self.feeds)
        return sorted(list(categories))
    
    def save(self) -> bool:
        """保存到文件"""
        try:
            data = {
                'feeds': [feed.to_dict() for feed in self.feeds],
                'saved_at': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存RSS订阅失败: {e}")
            return False
    
    def load(self) -> bool:
        """从文件加载"""
        try:
            if not self.storage_path.exists():
                return True  # 文件不存在是正常的
            
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            feeds_data = data.get('feeds', [])
            self.feeds = [RSSFeed.from_dict(feed_data) for feed_data in feeds_data]
            
            return True
        except Exception as e:
            print(f"加载RSS订阅失败: {e}")
            return False
