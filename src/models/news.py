"""
新闻文章数据模型
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from html import unescape


@dataclass
class NewsAuthor:
    """文章作者"""
    name: str
    email: Optional[str] = None


@dataclass
class NewsCategory:
    """文章分类"""
    id: str
    label: str


@dataclass
class NewsEnclosure:
    """文章附件（如图片、音频等）"""
    url: str
    type: str
    length: Optional[int] = None


@dataclass
class NewsArticle:
    """新闻文章模型"""
    id: str
    title: str
    summary: str
    content: str
    url: str
    published: datetime
    updated: datetime
    author: Optional[NewsAuthor] = None
    categories: List[NewsCategory] = field(default_factory=list)
    enclosures: List[NewsEnclosure] = field(default_factory=list)
    is_read: bool = False
    is_starred: bool = False
    feed_id: Optional[str] = None
    feed_title: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> 'NewsArticle':
        """从API响应创建文章对象"""
        # 检查输入数据类型
        if not isinstance(item, dict):
            raise ValueError(f"期望字典类型，但收到: {type(item)}")

        # 解析发布时间
        published = datetime.fromtimestamp(item.get('published', 0))
        updated = datetime.fromtimestamp(item.get('updated', item.get('published', 0)))
        
        # 解析作者
        author = None
        if 'author' in item:
            author_name = item['author']
            author = NewsAuthor(name=author_name)
        
        # 解析分类
        categories = []
        for category in item.get('categories', []):
            if isinstance(category, str):
                # 简单字符串分类
                categories.append(NewsCategory(id=category, label=category))
            elif isinstance(category, dict):
                # 详细分类信息
                cat_id = category.get('id', category.get('label', ''))
                cat_label = category.get('label', cat_id)
                categories.append(NewsCategory(id=cat_id, label=cat_label))
        
        # 解析附件
        enclosures = []
        for enc in item.get('enclosure', []):
            if isinstance(enc, dict):
                enclosures.append(NewsEnclosure(
                    url=enc.get('href', ''),
                    type=enc.get('type', ''),
                    length=enc.get('length')
                ))
        
        # 检查文章状态
        categories_list = item.get('categories', [])
        is_read = any('read' in cat for cat in categories_list if isinstance(cat, str))
        is_starred = any('starred' in cat for cat in categories_list if isinstance(cat, str))
        
        # 获取内容
        summary_data = item.get('summary', {})
        if isinstance(summary_data, dict):
            summary = cls._clean_html(summary_data.get('content', ''))
        else:
            summary = cls._clean_html(str(summary_data))

        content_data = item.get('content', {})
        if isinstance(content_data, dict):
            content = cls._clean_html(content_data.get('content', summary))
        else:
            content = cls._clean_html(str(content_data)) if content_data else summary
        
        # 获取订阅源信息
        origin = item.get('origin', {})
        feed_id = origin.get('streamId', '')
        feed_title = origin.get('title', '')
        
        return cls(
            id=item.get('id', ''),
            title=cls._clean_html(item.get('title', '')),
            summary=summary,
            content=content,
            url=cls._extract_url(item),
            published=published,
            updated=updated,
            author=author,
            categories=categories,
            enclosures=enclosures,
            is_read=is_read,
            is_starred=is_starred,
            feed_id=feed_id,
            feed_title=feed_title
        )
    
    @staticmethod
    def _extract_url(item: Dict[str, Any]) -> str:
        """提取文章URL"""
        # 尝试从canonical字段获取
        canonical = item.get('canonical', [])
        if canonical and isinstance(canonical, list) and len(canonical) > 0:
            if isinstance(canonical[0], dict):
                url = canonical[0].get('href', '')
                if url:
                    return url

        # 尝试从alternate字段获取
        alternate = item.get('alternate', [])
        if alternate and isinstance(alternate, list) and len(alternate) > 0:
            if isinstance(alternate[0], dict):
                url = alternate[0].get('href', '')
                if url:
                    return url

        return ''

    @staticmethod
    def _clean_html(html_content: str) -> str:
        """清理HTML内容，提取纯文本"""
        if not html_content:
            return ""
        
        # 解码HTML实体
        content = unescape(html_content)
        
        # 移除HTML标签
        content = re.sub(r'<[^>]+>', '', content)
        
        # 清理多余的空白字符
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def get_short_summary(self, max_length: int = 200) -> str:
        """获取短摘要"""
        summary = self.summary or self.content
        if len(summary) <= max_length:
            return summary
        
        # 在单词边界截断
        truncated = summary[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # 如果最后一个空格位置合理
            truncated = truncated[:last_space]
        
        return truncated + "..."
    
    def get_display_title(self, max_length: int = 80) -> str:
        """获取显示用的标题"""
        if len(self.title) <= max_length:
            return self.title
        
        return self.title[:max_length-3] + "..."
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'summary': self.summary,
            'content': self.content,
            'url': self.url,
            'published': self.published.isoformat(),
            'updated': self.updated.isoformat(),
            'author': self.author.name if self.author else None,
            'categories': [{'id': cat.id, 'label': cat.label} for cat in self.categories],
            'is_read': self.is_read,
            'is_starred': self.is_starred,
            'feed_id': self.feed_id,
            'feed_title': self.feed_title
        }
