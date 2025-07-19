"""
订阅管理服务 - 处理订阅源管理的业务逻辑
"""
from typing import List, Optional, Dict, Any

from ..api.client import InoreaderClient, InoreaderAPIError
from ..models.subscription import Subscription, UnreadCount


class SubscriptionService:
    """订阅管理服务"""

    def __init__(self, auth=None, use_cache: bool = True):
        self.client = InoreaderClient(auth, use_cache=use_cache)
        self.use_cache = use_cache
    
    def get_all_subscriptions(self) -> List[Subscription]:
        """获取所有订阅源"""
        try:
            subscriptions_data = self.client.get_subscription_list()
            
            subscriptions = []
            for sub_data in subscriptions_data:
                try:
                    subscription = Subscription.from_api_response(sub_data)
                    subscriptions.append(subscription)
                except Exception as e:
                    print(f"解析订阅源失败: {e}")
                    continue
            
            # 按标题排序
            subscriptions.sort(key=lambda x: x.title.lower())
            
            return subscriptions
            
        except InoreaderAPIError as e:
            print(f"获取订阅源列表失败: {e}")
            return []
    
    def get_subscriptions_by_category(self, category_name: str) -> List[Subscription]:
        """根据分类获取订阅源"""
        all_subscriptions = self.get_all_subscriptions()
        
        category_name_lower = category_name.lower()
        filtered_subscriptions = []
        
        for subscription in all_subscriptions:
            for category in subscription.categories:
                if category_name_lower in category.label.lower():
                    filtered_subscriptions.append(subscription)
                    break
        
        return filtered_subscriptions
    
    def search_subscriptions(self, keyword: str) -> List[Subscription]:
        """搜索订阅源"""
        all_subscriptions = self.get_all_subscriptions()
        
        keyword_lower = keyword.lower()
        matched_subscriptions = []
        
        for subscription in all_subscriptions:
            if (keyword_lower in subscription.title.lower() or
                keyword_lower in subscription.url.lower() or
                any(keyword_lower in cat.label.lower() for cat in subscription.categories)):
                matched_subscriptions.append(subscription)
        
        return matched_subscriptions
    
    def get_subscription_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """根据ID获取订阅源"""
        all_subscriptions = self.get_all_subscriptions()
        
        for subscription in all_subscriptions:
            if subscription.id == subscription_id:
                return subscription
        
        return None
    
    def get_unread_counts(self) -> Dict[str, int]:
        """获取各订阅源的未读数量"""
        try:
            unread_data = self.client.get_unread_count()
            
            unread_counts = {}
            for item in unread_data.get('unreadcounts', []):
                try:
                    unread_count = UnreadCount.from_api_response(item)
                    unread_counts[unread_count.id] = unread_count.count
                except Exception as e:
                    print(f"解析未读数量失败: {e}")
                    continue
            
            return unread_counts
            
        except InoreaderAPIError as e:
            print(f"获取未读数量失败: {e}")
            return {}
    
    def get_subscriptions_with_unread_counts(self) -> List[Dict[str, Any]]:
        """获取带未读数量的订阅源列表"""
        subscriptions = self.get_all_subscriptions()
        unread_counts = self.get_unread_counts()
        
        result = []
        for subscription in subscriptions:
            unread_count = unread_counts.get(subscription.id, 0)
            result.append({
                'subscription': subscription,
                'unread_count': unread_count
            })
        
        # 按未读数量排序（未读多的在前）
        result.sort(key=lambda x: x['unread_count'], reverse=True)
        
        return result
    
    def get_categories(self) -> List[str]:
        """获取所有分类名称"""
        all_subscriptions = self.get_all_subscriptions()
        
        categories = set()
        for subscription in all_subscriptions:
            for category in subscription.categories:
                categories.add(category.label)
        
        return sorted(list(categories))
    
    def get_subscription_statistics(self) -> Dict[str, Any]:
        """获取订阅源统计信息"""
        subscriptions = self.get_all_subscriptions()
        unread_counts = self.get_unread_counts()
        
        total_subscriptions = len(subscriptions)
        # 确保所有值都是整数
        total_unread = 0
        for value in unread_counts.values():
            if isinstance(value, str):
                try:
                    total_unread += int(value)
                except ValueError:
                    pass
            else:
                total_unread += value
        
        # 按分类统计
        category_stats = {}
        for subscription in subscriptions:
            for category in subscription.categories:
                if category.label not in category_stats:
                    category_stats[category.label] = {
                        'count': 0,
                        'unread': 0
                    }
                category_stats[category.label]['count'] += 1
                unread_value = unread_counts.get(subscription.id, 0)
                # 确保是整数类型
                if isinstance(unread_value, str):
                    try:
                        unread_value = int(unread_value)
                    except ValueError:
                        unread_value = 0
                category_stats[category.label]['unread'] += unread_value
        
        # 找出最活跃的订阅源（未读数量最多的前10个）
        subscriptions_with_unread = [
            {
                'subscription': sub,
                'unread_count': unread_counts.get(sub.id, 0)
            }
            for sub in subscriptions
        ]
        subscriptions_with_unread.sort(key=lambda x: x['unread_count'], reverse=True)
        most_active = subscriptions_with_unread[:10]
        
        return {
            'total_subscriptions': total_subscriptions,
            'total_unread': total_unread,
            'categories': category_stats,
            'most_active_feeds': most_active
        }
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            return self.client.get_user_info()
        except InoreaderAPIError as e:
            print(f"获取用户信息失败: {e}")
            return None

    def refresh_cache(self):
        """刷新缓存 - 清除所有缓存数据"""
        self.client.clear_cache()

    def refresh_subscriptions_cache(self):
        """刷新订阅源列表缓存"""
        self.client.clear_cache('subscription/list')
        self.client.clear_cache('unread-count')

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        cache_stats = self.client.get_cache_stats()
        region_info = self.client.get_current_region_info()

        return {
            'cache_stats': cache_stats,
            'current_region': region_info,
            'cache_enabled': self.use_cache
        }
