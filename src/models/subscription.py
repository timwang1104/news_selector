"""
订阅源数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SubscriptionCategory:
    """订阅分类"""
    id: str
    label: str


@dataclass
class Subscription:
    """订阅源模型"""
    id: str
    title: str
    url: str
    html_url: str
    icon_url: Optional[str] = None
    categories: List[SubscriptionCategory] = field(default_factory=list)
    first_item_msec: Optional[int] = None
    sort_id: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> 'Subscription':
        """从API响应创建订阅源对象"""
        # 解析分类
        categories = []
        for category in item.get('categories', []):
            if isinstance(category, dict):
                cat_id = category.get('id', '')
                cat_label = category.get('label', cat_id)
                categories.append(SubscriptionCategory(id=cat_id, label=cat_label))
        
        return cls(
            id=item.get('id', ''),
            title=item.get('title', ''),
            url=item.get('url', ''),
            html_url=item.get('htmlUrl', ''),
            icon_url=item.get('iconUrl'),
            categories=categories,
            first_item_msec=item.get('firstitemmsec'),
            sort_id=item.get('sortid')
        )
    
    def get_display_title(self, max_length: int = 50) -> str:
        """获取显示用的标题"""
        if len(self.title) <= max_length:
            return self.title
        
        return self.title[:max_length-3] + "..."
    
    def get_category_names(self) -> List[str]:
        """获取分类名称列表"""
        return [cat.label for cat in self.categories]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'html_url': self.html_url,
            'icon_url': self.icon_url,
            'categories': [{'id': cat.id, 'label': cat.label} for cat in self.categories],
            'first_item_msec': self.first_item_msec,
            'sort_id': self.sort_id
        }


@dataclass
class UnreadCount:
    """未读数量统计"""
    id: str
    count: int
    newest_item_timestamp: Optional[int] = None
    
    @classmethod
    def from_api_response(cls, item: Dict[str, Any]) -> 'UnreadCount':
        """从API响应创建未读数量对象"""
        return cls(
            id=item.get('id', ''),
            count=item.get('count', 0),
            newest_item_timestamp=item.get('newestItemTimestampUsec')
        )


@dataclass
class StreamInfo:
    """流信息（用于获取文章列表的响应）"""
    id: str
    title: str
    description: str
    updated: datetime
    items: List[Any] = field(default_factory=list)  # 实际使用时会是NewsArticle列表
    continuation: Optional[str] = None
    
    @classmethod
    def from_api_response(cls, response: Dict[str, Any]) -> 'StreamInfo':
        """从API响应创建流信息对象"""
        updated = datetime.fromtimestamp(response.get('updated', 0))
        
        return cls(
            id=response.get('id', ''),
            title=response.get('title', ''),
            description=response.get('description', ''),
            updated=updated,
            items=response.get('items', []),
            continuation=response.get('continuation')
        )
