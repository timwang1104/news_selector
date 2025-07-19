"""
Inoreader API客户端
"""
import time
import logging
from typing import Dict, List, Optional, Any, Union
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config.settings import settings
from .auth import InoreaderAuth
from ..utils.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class InoreaderAPIError(Exception):
    """Inoreader API错误"""
    pass


class RegionSwitchError(InoreaderAPIError):
    """API区域切换错误"""
    pass


class InoreaderClient:
    """Inoreader API客户端"""

    def __init__(self, auth: Optional[InoreaderAuth] = None, use_cache: bool = True):
        self.config = settings.inoreader
        self.auth = auth if auth is not None else InoreaderAuth()
        self.session = self._create_session()
        self.use_cache = use_cache

        # 区域切换相关
        self.region_switch_attempts = 0
        self.max_region_switches = len(self.config.regions) - 1
    
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
    
    def _get_current_base_url(self) -> str:
        """获取当前API区域的基础URL"""
        current_region = self.config.get_current_region()
        return current_region['base_url']

    def _make_request(self, method: str, endpoint: str, use_cache: Optional[bool] = None, **kwargs) -> Dict[str, Any]:
        """发起API请求"""
        # 确定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self.use_cache

        # 对于GET请求，尝试从缓存获取
        if should_use_cache and method.upper() == 'GET':
            cache_params = kwargs.get('params', {})
            cached_result = cache_manager.get(endpoint, cache_params)
            if cached_result is not None:
                logger.debug(f"使用缓存结果: {endpoint}")
                return cached_result

        # 如果没有缓存数据，检查认证状态
        if not self.auth.is_authenticated():
            raise InoreaderAPIError("用户未认证，请先登录")

        # 发起实际请求
        result = self._make_actual_request(method, endpoint, **kwargs)

        # 对于GET请求，缓存结果
        if should_use_cache and method.upper() == 'GET' and result:
            cache_params = kwargs.get('params', {})
            cache_manager.set(endpoint, result, cache_params)

        return result

    def _make_actual_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发起实际的API请求（带区域切换）"""
        last_exception = None

        # 尝试当前区域和所有备用区域
        for attempt in range(len(self.config.regions)):
            try:
                url = f"{self._get_current_base_url()}{endpoint}"
                headers = self.auth.get_auth_headers()

                # 合并请求头
                if 'headers' in kwargs:
                    headers.update(kwargs['headers'])
                kwargs['headers'] = headers

                # 设置超时
                kwargs.setdefault('timeout', settings.app.request_timeout)

                logger.debug(f"尝试请求 {self.config.get_current_region()['name']}: {url}")

                response = self.session.request(method, url, **kwargs)

                # 处理认证过期
                if response.status_code == 401:
                    if self.auth.refresh_access_token():
                        # 重试请求
                        kwargs['headers'] = self.auth.get_auth_headers()
                        response = self.session.request(method, url, **kwargs)
                    else:
                        raise InoreaderAPIError("认证已过期，请重新登录")

                # 检查是否需要切换区域
                if response.status_code == 429:  # Too Many Requests
                    logger.warning(f"{self.config.get_current_region()['name']} 请求次数已满，尝试切换区域")
                    if not self._switch_to_next_region():
                        raise InoreaderAPIError("所有API区域的请求次数都已满")
                    continue

                response.raise_for_status()

                # 处理不同的响应类型
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    result = response.json()
                else:
                    result = {'content': response.text, 'status_code': response.status_code}

                logger.debug(f"请求成功: {self.config.get_current_region()['name']}")
                return result

            except requests.RequestException as e:
                last_exception = e
                logger.warning(f"{self.config.get_current_region()['name']} 请求失败: {e}")

                # 如果是网络错误，尝试切换区域
                if not self._switch_to_next_region():
                    break

        # 所有区域都失败了
        raise InoreaderAPIError(f"所有API区域请求都失败: {last_exception}")

    def _switch_to_next_region(self) -> bool:
        """切换到下一个API区域"""
        if self.config.switch_to_next_region():
            self.region_switch_attempts += 1
            logger.info(f"切换到 {self.config.get_current_region()['name']}")
            return True
        else:
            logger.error("没有更多可用的API区域")
            return False

    def get_current_region_info(self) -> Dict[str, Any]:
        """获取当前API区域信息"""
        region = self.config.get_current_region()
        return {
            'name': region['name'],
            'description': region['description'],
            'base_url': region['base_url'],
            'switch_attempts': self.region_switch_attempts
        }

    def reset_region(self):
        """重置到第一个API区域"""
        self.config.reset_region()
        self.region_switch_attempts = 0
        logger.info("API区域已重置到第一个区域")

    def clear_cache(self, endpoint: Optional[str] = None):
        """清除缓存"""
        if endpoint:
            cache_manager.invalidate(endpoint)
            logger.info(f"已清除 {endpoint} 的缓存")
        else:
            cache_manager.clear_all()
            logger.info("已清除所有缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return cache_manager.get_cache_stats()
    
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
