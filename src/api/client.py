"""
Inoreader API客户端
"""
import time
from typing import Dict, List, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config.settings import settings
from .auth import InoreaderAuth


class InoreaderAPIError(Exception):
    """Inoreader API错误"""
    pass


class InoreaderClient:
    """Inoreader API客户端"""
    
    def __init__(self):
        self.config = settings.inoreader
        self.auth = InoreaderAuth()
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建带重试机制的HTTP会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发起API请求"""
        if not self.auth.is_authenticated():
            raise InoreaderAPIError("用户未认证，请先登录")
        
        url = f"{self.config.base_url}{endpoint}"
        headers = self.auth.get_auth_headers()
        
        # 合并请求头
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        # 设置超时
        kwargs.setdefault('timeout', settings.app.request_timeout)
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # 处理认证过期
            if response.status_code == 401:
                if self.auth.refresh_access_token():
                    # 重试请求
                    kwargs['headers'] = self.auth.get_auth_headers()
                    response = self.session.request(method, url, **kwargs)
                else:
                    raise InoreaderAPIError("认证已过期，请重新登录")
            
            response.raise_for_status()
            
            # 处理不同的响应类型
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                return response.json()
            else:
                return {'content': response.text, 'status_code': response.status_code}
                
        except requests.RequestException as e:
            raise InoreaderAPIError(f"API请求失败: {e}")
    
    def get_user_info(self) -> Dict[str, Any]:
        """获取用户信息"""
        return self._make_request('GET', 'user-info')
    
    def get_subscription_list(self) -> List[Dict[str, Any]]:
        """获取订阅源列表"""
        response = self._make_request('GET', 'subscription/list')
        return response.get('subscriptions', [])
    
    def get_unread_count(self) -> Dict[str, Any]:
        """获取未读数量"""
        return self._make_request('GET', 'unread-count')
    
    def get_stream_contents(self, 
                          stream_id: str,
                          count: Optional[int] = None,
                          start_time: Optional[int] = None,
                          exclude_read: bool = True) -> Dict[str, Any]:
        """
        获取流内容（文章列表）
        
        Args:
            stream_id: 流ID，可以是订阅源ID或特殊流（如user/-/state/com.google/reading-list）
            count: 返回文章数量，默认使用配置值
            start_time: 开始时间戳
            exclude_read: 是否排除已读文章
        """
        params = {}
        
        if count is None:
            count = settings.app.max_articles_per_request
        params['n'] = count
        
        if start_time:
            params['ot'] = start_time
        
        if exclude_read:
            params['xt'] = 'user/-/state/com.google/read'
        
        return self._make_request('GET', f'stream/contents/{stream_id}', params=params)
    
    def get_reading_list(self, count: Optional[int] = None) -> Dict[str, Any]:
        """获取阅读列表（所有订阅的最新文章）"""
        stream_id = 'user/-/state/com.google/reading-list'
        return self.get_stream_contents(stream_id, count)
    
    def get_starred_items(self, count: Optional[int] = None) -> Dict[str, Any]:
        """获取加星标的文章"""
        stream_id = 'user/-/state/com.google/starred'
        return self.get_stream_contents(stream_id, count, exclude_read=False)
    
    def mark_as_read(self, item_ids: Union[str, List[str]]) -> bool:
        """标记文章为已读"""
        if isinstance(item_ids, str):
            item_ids = [item_ids]
        
        data = {
            'i': item_ids,
            'a': 'user/-/state/com.google/read'
        }
        
        try:
            self._make_request('POST', 'edit-tag', data=data)
            return True
        except InoreaderAPIError:
            return False
    
    def mark_as_unread(self, item_ids: Union[str, List[str]]) -> bool:
        """标记文章为未读"""
        if isinstance(item_ids, str):
            item_ids = [item_ids]
        
        data = {
            'i': item_ids,
            'r': 'user/-/state/com.google/read'
        }
        
        try:
            self._make_request('POST', 'edit-tag', data=data)
            return True
        except InoreaderAPIError:
            return False
    
    def add_star(self, item_ids: Union[str, List[str]]) -> bool:
        """给文章加星标"""
        if isinstance(item_ids, str):
            item_ids = [item_ids]
        
        data = {
            'i': item_ids,
            'a': 'user/-/state/com.google/starred'
        }
        
        try:
            self._make_request('POST', 'edit-tag', data=data)
            return True
        except InoreaderAPIError:
            return False
    
    def remove_star(self, item_ids: Union[str, List[str]]) -> bool:
        """移除文章星标"""
        if isinstance(item_ids, str):
            item_ids = [item_ids]
        
        data = {
            'i': item_ids,
            'r': 'user/-/state/com.google/starred'
        }
        
        try:
            self._make_request('POST', 'edit-tag', data=data)
            return True
        except InoreaderAPIError:
            return False
