"""
订阅源导出服务 - 处理Inoreader订阅源的导出和导入功能
"""
import json
import logging
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from urllib.parse import urlparse

from .subscription_service import SubscriptionService
from .custom_rss_service import CustomRSSService
from ..models.subscription import Subscription

logger = logging.getLogger(__name__)


class SubscriptionExportService:
    """订阅源导出服务"""
    
    def __init__(self, auth=None):
        self.subscription_service = SubscriptionService(auth)
        self.custom_rss_service = CustomRSSService()
    
    def export_inoreader_subscriptions(self) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        导出Inoreader订阅源
        
        Returns:
            (是否成功, 消息, 订阅源列表)
        """
        try:
            logger.info("开始导出Inoreader订阅源...")
            
            # 获取所有订阅源
            subscriptions = self.subscription_service.get_all_subscriptions()
            
            if not subscriptions:
                return False, "未找到任何订阅源", []
            
            # 转换为导出格式
            export_data = []
            for sub in subscriptions:
                # 提取RSS URL
                rss_url = self._extract_rss_url(sub)
                if not rss_url:
                    logger.warning(f"无法提取RSS URL: {sub.title}")
                    continue
                
                # 确定分类
                category = self._determine_category(sub)
                
                export_item = {
                    "title": sub.title,
                    "url": rss_url,
                    "category": category,
                    "description": getattr(sub, 'description', '') or f"来自Inoreader的订阅源: {sub.title}",
                    "original_id": sub.id,
                    "export_time": datetime.now().isoformat()
                }
                export_data.append(export_item)
            
            # 数据处理：去重和标准化
            export_data = self.normalize_urls(export_data)
            export_data = self.deduplicate_export_data(export_data)

            logger.info(f"成功导出 {len(export_data)} 个订阅源")
            return True, f"成功导出 {len(export_data)} 个订阅源", export_data
            
        except Exception as e:
            logger.error(f"导出Inoreader订阅源失败: {e}")
            return False, f"导出失败: {e}", []
    
    def _extract_rss_url(self, subscription: Subscription) -> Optional[str]:
        """
        从订阅源中提取RSS URL
        
        Args:
            subscription: 订阅源对象
            
        Returns:
            RSS URL或None
        """
        # Inoreader的订阅源ID通常是feed/开头的URL
        if hasattr(subscription, 'id') and subscription.id:
            if subscription.id.startswith('feed/'):
                # 移除feed/前缀
                url = subscription.id[5:]
                # 验证URL格式
                try:
                    parsed = urlparse(url)
                    if parsed.scheme and parsed.netloc:
                        return url
                except:
                    pass
        
        # 尝试从其他属性获取URL
        if hasattr(subscription, 'url') and subscription.url:
            return subscription.url
        
        if hasattr(subscription, 'htmlUrl') and subscription.htmlUrl:
            # 有时候需要从网站URL推导RSS URL
            return self._guess_rss_url_from_html(subscription.htmlUrl)
        
        return None
    
    def _guess_rss_url_from_html(self, html_url: str) -> Optional[str]:
        """
        从网站URL推导可能的RSS URL
        
        Args:
            html_url: 网站URL
            
        Returns:
            可能的RSS URL
        """
        # 常见的RSS URL模式
        common_patterns = [
            "/rss",
            "/rss.xml",
            "/feed",
            "/feed.xml",
            "/feeds",
            "/atom.xml",
            "/index.xml"
        ]
        
        try:
            parsed = urlparse(html_url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            # 尝试常见模式
            for pattern in common_patterns:
                potential_url = base_url + pattern
                return potential_url  # 返回第一个可能的URL，让后续验证
                
        except:
            pass
        
        return html_url  # 如果无法推导，返回原URL
    
    def _determine_category(self, subscription: Subscription) -> str:
        """
        确定订阅源的分类

        Args:
            subscription: 订阅源对象

        Returns:
            分类名称
        """
        # 检查是否有分类信息
        if hasattr(subscription, 'categories') and subscription.categories:
            # 取第一个分类
            category_obj = subscription.categories[0]

            # 从SubscriptionCategory对象获取分类信息
            # 优先使用label，如果没有则使用id
            category_str = getattr(category_obj, 'label', None) or getattr(category_obj, 'id', '')

            # 移除可能的前缀
            if category_str and category_str.startswith('user/'):
                parts = category_str.split('/')
                if len(parts) >= 3:
                    return parts[-1]  # 取最后一部分作为分类名

            return category_str if category_str else "默认"
        
        # 根据标题推测分类
        title_lower = subscription.title.lower()
        
        if any(keyword in title_lower for keyword in ['tech', '科技', 'technology', '技术']):
            return "科技"
        elif any(keyword in title_lower for keyword in ['news', '新闻', 'daily']):
            return "新闻"
        elif any(keyword in title_lower for keyword in ['blog', '博客', 'personal']):
            return "博客"
        elif any(keyword in title_lower for keyword in ['finance', '财经', 'money', '金融']):
            return "财经"
        else:
            return "从Inoreader导入"
    
    def save_export_to_file(self, export_data: List[Dict[str, Any]], filename: str) -> Tuple[bool, str]:
        """
        将导出数据保存到文件
        
        Args:
            export_data: 导出的数据
            filename: 文件名
            
        Returns:
            (是否成功, 消息)
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_time": datetime.now().isoformat(),
                    "source": "Inoreader",
                    "count": len(export_data),
                    "subscriptions": export_data
                }, f, ensure_ascii=False, indent=2)
            
            return True, f"导出数据已保存到 {filename}"
            
        except Exception as e:
            logger.error(f"保存导出文件失败: {e}")
            return False, f"保存失败: {e}"
    
    def load_export_from_file(self, filename: str) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        从文件加载导出数据
        
        Args:
            filename: 文件名
            
        Returns:
            (是否成功, 消息, 订阅源列表)
        """
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'subscriptions' not in data:
                return False, "文件格式不正确", []
            
            subscriptions = data['subscriptions']
            return True, f"成功加载 {len(subscriptions)} 个订阅源", subscriptions
            
        except Exception as e:
            logger.error(f"加载导出文件失败: {e}")
            return False, f"加载失败: {e}", []
    
    def get_import_preview(self, export_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取导入预览信息
        
        Args:
            export_data: 导出的数据
            
        Returns:
            预览信息
        """
        total_count = len(export_data)
        existing_count = 0
        new_count = 0
        categories = set()
        
        for item in export_data:
            url = item.get('url', '')
            category = item.get('category', '默认')
            categories.add(category)
            
            # 检查是否已存在
            if self.custom_rss_service.subscription_manager.get_feed_by_url(url):
                existing_count += 1
            else:
                new_count += 1
        
        return {
            "total_count": total_count,
            "existing_count": existing_count,
            "new_count": new_count,
            "categories": sorted(list(categories)),
            "will_add": new_count,
            "will_skip": existing_count
        }

    def batch_import_to_custom_rss(self, export_data: List[Dict[str, Any]],
                                  progress_callback=None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        批量导入订阅源到自定义RSS

        Args:
            export_data: 导出的数据
            progress_callback: 进度回调函数 callback(current, total, message)

        Returns:
            (是否成功, 消息, 详细结果)
        """
        try:
            logger.info(f"开始批量导入 {len(export_data)} 个订阅源...")

            results = {
                "total": len(export_data),
                "success": 0,
                "skipped": 0,
                "failed": 0,
                "success_items": [],
                "skipped_items": [],
                "failed_items": []
            }

            for i, item in enumerate(export_data):
                if progress_callback:
                    progress_callback(i + 1, len(export_data), f"处理: {item.get('title', 'Unknown')}")

                url = item.get('url', '')
                title = item.get('title', 'Unknown')
                category = item.get('category', '从Inoreader导入')

                if not url:
                    results["failed"] += 1
                    results["failed_items"].append({
                        "title": title,
                        "reason": "缺少URL"
                    })
                    continue

                # 检查是否已存在
                existing_feed = self.custom_rss_service.subscription_manager.get_feed_by_url(url)
                if existing_feed:
                    results["skipped"] += 1
                    results["skipped_items"].append({
                        "title": title,
                        "url": url,
                        "reason": "已存在"
                    })
                    continue

                # 验证URL有效性
                url_valid, url_error = self._validate_rss_url(url)
                if not url_valid:
                    results["failed"] += 1
                    results["failed_items"].append({
                        "title": title,
                        "url": url,
                        "reason": f"URL验证失败: {url_error}"
                    })
                    logger.warning(f"URL验证失败: {title} - {url_error}")
                    continue

                # 尝试添加订阅源
                success, message = self.custom_rss_service.add_subscription(url, category)

                if success:
                    results["success"] += 1
                    results["success_items"].append({
                        "title": title,
                        "url": url,
                        "category": category
                    })
                    logger.info(f"成功添加: {title}")
                else:
                    results["failed"] += 1
                    results["failed_items"].append({
                        "title": title,
                        "url": url,
                        "reason": message
                    })
                    logger.warning(f"添加失败: {title} - {message}")

            # 生成总结消息
            summary = f"导入完成: 成功 {results['success']} 个, 跳过 {results['skipped']} 个, 失败 {results['failed']} 个"

            logger.info(summary)
            return True, summary, results

        except Exception as e:
            logger.error(f"批量导入失败: {e}")
            return False, f"批量导入失败: {e}", {}

    def validate_export_data(self, export_data: List[Dict[str, Any]]) -> Tuple[bool, str, List[str]]:
        """
        验证导出数据的有效性

        Args:
            export_data: 导出的数据

        Returns:
            (是否有效, 消息, 错误列表)
        """
        errors = []

        if not export_data:
            return False, "导出数据为空", ["数据为空"]

        for i, item in enumerate(export_data):
            item_errors = []

            # 检查必需字段
            if not item.get('title'):
                item_errors.append("缺少标题")

            if not item.get('url'):
                item_errors.append("缺少URL")
            else:
                # 验证URL格式
                try:
                    parsed = urlparse(item['url'])
                    if not parsed.scheme or not parsed.netloc:
                        item_errors.append("URL格式无效")
                except:
                    item_errors.append("URL解析失败")

            if item_errors:
                errors.append(f"第 {i+1} 项 ({item.get('title', 'Unknown')}): {', '.join(item_errors)}")

        if errors:
            return False, f"发现 {len(errors)} 个错误", errors
        else:
            return True, "数据验证通过", []

    def _validate_rss_url(self, url: str) -> Tuple[bool, str]:
        """
        验证RSS URL的有效性

        Args:
            url: RSS URL

        Returns:
            (是否有效, 错误信息)
        """
        try:
            # 基本URL格式验证
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return False, "URL格式无效"

            # 检查协议
            if parsed.scheme not in ['http', 'https']:
                return False, "仅支持HTTP和HTTPS协议"

            # 使用RSS服务验证
            is_valid, error_msg = self.custom_rss_service.rss_service.validate_rss_url(url)
            return is_valid, error_msg

        except Exception as e:
            return False, f"验证过程出错: {e}"

    def deduplicate_export_data(self, export_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        去重导出数据

        Args:
            export_data: 原始导出数据

        Returns:
            去重后的数据
        """
        seen_urls = set()
        deduplicated = []

        for item in export_data:
            url = item.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(item)
            else:
                logger.info(f"跳过重复URL: {url} ({item.get('title', 'Unknown')})")

        logger.info(f"去重完成: 原始 {len(export_data)} 个，去重后 {len(deduplicated)} 个")
        return deduplicated

    def normalize_urls(self, export_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        标准化URL格式

        Args:
            export_data: 导出数据

        Returns:
            标准化后的数据
        """
        for item in export_data:
            url = item.get('url', '')
            if url:
                # 移除URL末尾的斜杠
                url = url.rstrip('/')

                # 标准化协议（优先使用HTTPS）
                if url.startswith('http://'):
                    https_url = url.replace('http://', 'https://', 1)
                    # 简单检查HTTPS是否可用（这里只是替换，实际验证在后续步骤）
                    item['url'] = https_url

                item['url'] = url

        return export_data
