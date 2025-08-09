"""
筛选结果缓存管理器
用于保存和恢复筛选结果，实现应用重启后的状态恢复
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import asdict

from ..models.news import NewsArticle
from ..filters.base import FilterChainResult, CombinedFilterResult, AIFilterResult, KeywordFilterResult, AIEvaluation

logger = logging.getLogger(__name__)


class FilterResultCache:
    """筛选结果缓存管理器"""
    
    def __init__(self, cache_dir: str = "cache", expire_hours: int = 24):
        """
        初始化筛选结果缓存
        
        Args:
            cache_dir: 缓存目录
            expire_hours: 缓存过期时间（小时）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "filter_results.json"
        self.expire_hours = expire_hours
        
        logger.info(f"筛选结果缓存初始化: {self.cache_file}")
    
    def save_filter_result(self, 
                          filtered_articles: List[NewsArticle], 
                          filter_result: Optional[FilterChainResult] = None,
                          session_id: str = "default") -> bool:
        """
        保存筛选结果
        
        Args:
            filtered_articles: 筛选后的文章列表
            filter_result: 完整的筛选结果对象
            session_id: 会话ID，用于区分不同的筛选会话
            
        Returns:
            是否保存成功
        """
        try:
            # 准备缓存数据
            cache_data = {
                "session_id": session_id,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "filtered_articles": [self._serialize_article(article) for article in filtered_articles],
                "filter_result": self._serialize_filter_result(filter_result) if filter_result else None,
                "article_count": len(filtered_articles),
                "metadata": {
                    "version": "1.0",
                    "app_name": "news_selector"
                }
            }
            
            # 保存到文件
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"筛选结果已保存: {len(filtered_articles)}篇文章, 会话ID: {session_id}")
            print(f"💾 筛选结果已保存到缓存: {len(filtered_articles)}篇文章")
            return True
            
        except Exception as e:
            logger.error(f"保存筛选结果失败: {e}")
            print(f"❌ 保存筛选结果失败: {e}")
            return False
    
    def load_filter_result(self, session_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        加载筛选结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            筛选结果数据，如果不存在或过期则返回None
        """
        try:
            if not self.cache_file.exists():
                logger.debug("筛选结果缓存文件不存在")
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # 检查会话ID
            if cache_data.get("session_id") != session_id:
                logger.debug(f"会话ID不匹配: 期望{session_id}, 实际{cache_data.get('session_id')}")
                return None
            
            # 检查是否过期
            saved_at = datetime.fromisoformat(cache_data["saved_at"])
            now = datetime.now(timezone.utc)
            age_hours = (now - saved_at).total_seconds() / 3600
            
            if age_hours > self.expire_hours:
                logger.info(f"筛选结果缓存已过期: {age_hours:.1f}小时 > {self.expire_hours}小时")
                self.clear_cache()
                return None
            
            # 反序列化文章列表
            filtered_articles = [
                self._deserialize_article(article_data) 
                for article_data in cache_data.get("filtered_articles", [])
            ]
            
            # 反序列化筛选结果
            filter_result = None
            if cache_data.get("filter_result"):
                filter_result = self._deserialize_filter_result(cache_data["filter_result"])
            
            logger.info(f"筛选结果已加载: {len(filtered_articles)}篇文章, 缓存时间: {age_hours:.1f}小时前")
            print(f"📂 从缓存加载筛选结果: {len(filtered_articles)}篇文章 (缓存时间: {age_hours:.1f}小时前)")
            
            return {
                "filtered_articles": filtered_articles,
                "filter_result": filter_result,
                "saved_at": saved_at,
                "age_hours": age_hours,
                "article_count": len(filtered_articles)
            }
            
        except Exception as e:
            logger.error(f"加载筛选结果失败: {e}")
            print(f"❌ 加载筛选结果失败: {e}")
            return None
    
    def has_cached_result(self, session_id: str = "default") -> bool:
        """
        检查是否有缓存的筛选结果
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否有有效的缓存结果
        """
        return self.load_filter_result(session_id) is not None
    
    def clear_cache(self, session_id: Optional[str] = None) -> bool:
        """
        清除缓存
        
        Args:
            session_id: 会话ID，如果为None则清除所有缓存
            
        Returns:
            是否清除成功
        """
        try:
            if session_id is None:
                # 清除所有缓存
                if self.cache_file.exists():
                    self.cache_file.unlink()
                    logger.info("所有筛选结果缓存已清除")
                    print("🗑️ 筛选结果缓存已清除")
                return True
            else:
                # 清除特定会话的缓存（当前实现中等同于清除所有）
                return self.clear_cache()
                
        except Exception as e:
            logger.error(f"清除筛选结果缓存失败: {e}")
            print(f"❌ 清除筛选结果缓存失败: {e}")
            return False
    
    def get_cache_info(self) -> Optional[Dict[str, Any]]:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        try:
            if not self.cache_file.exists():
                return None
            
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            saved_at = datetime.fromisoformat(cache_data["saved_at"])
            now = datetime.now(timezone.utc)
            age_hours = (now - saved_at).total_seconds() / 3600
            
            return {
                "session_id": cache_data.get("session_id"),
                "saved_at": saved_at,
                "age_hours": age_hours,
                "article_count": cache_data.get("article_count", 0),
                "is_expired": age_hours > self.expire_hours,
                "file_size": self.cache_file.stat().st_size,
                "file_path": str(self.cache_file)
            }
            
        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return None
    
    def _serialize_article(self, article: NewsArticle) -> Dict[str, Any]:
        """序列化文章对象"""
        return {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "url": article.url,
            "published": article.published.isoformat() if article.published else None,
            "updated": article.updated.isoformat() if article.updated else None,
            "feed_title": getattr(article, 'feed_title', None),
            "is_read": getattr(article, 'is_read', False),
            "is_starred": getattr(article, 'is_starred', False),
            "tags": getattr(article, 'tags', [])
        }
    
    def _deserialize_article(self, data: Dict[str, Any]) -> NewsArticle:
        """反序列化文章对象"""
        article = NewsArticle(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            content=data["content"],
            url=data["url"],
            published=datetime.fromisoformat(data["published"]) if data.get("published") else None,
            updated=datetime.fromisoformat(data["updated"]) if data.get("updated") else None
        )
        
        # 设置额外属性
        if data.get("feed_title"):
            article.feed_title = data["feed_title"]
        if data.get("is_read") is not None:
            article.is_read = data["is_read"]
        if data.get("is_starred") is not None:
            article.is_starred = data["is_starred"]
        if data.get("tags"):
            article.tags = data["tags"]
        
        return article
    
    def _serialize_filter_result(self, filter_result: FilterChainResult) -> Dict[str, Any]:
        """序列化筛选结果对象（简化版）"""
        try:
            return {
                "total_articles": filter_result.total_articles,
                "final_selected_count": filter_result.final_selected_count,
                "processing_start_time": filter_result.processing_start_time.isoformat() if filter_result.processing_start_time else None,
                "processing_end_time": filter_result.processing_end_time.isoformat() if filter_result.processing_end_time else None,
                "total_processing_time": filter_result.total_processing_time,
                "keyword_filtered_count": getattr(filter_result, 'keyword_filtered_count', 0),
                "ai_filtered_count": getattr(filter_result, 'ai_filtered_count', 0),
                # 注意：不序列化selected_articles，因为它们已经在filtered_articles中
                "has_selected_articles": bool(filter_result.selected_articles)
            }
        except Exception as e:
            logger.warning(f"序列化筛选结果失败: {e}")
            return {}
    
    def _deserialize_filter_result(self, data: Dict[str, Any]) -> Optional[FilterChainResult]:
        """反序列化筛选结果对象（简化版）"""
        try:
            # 创建一个简化的FilterChainResult对象
            # 注意：这里不包含selected_articles，因为它们会从filtered_articles重建
            filter_result = FilterChainResult(
                total_articles=data.get("total_articles", 0),
                processing_start_time=datetime.fromisoformat(data["processing_start_time"]) if data.get("processing_start_time") else datetime.now()
            )
            
            filter_result.final_selected_count = data.get("final_selected_count", 0)
            filter_result.processing_end_time = datetime.fromisoformat(data["processing_end_time"]) if data.get("processing_end_time") else datetime.now()
            filter_result.total_processing_time = data.get("total_processing_time", 0.0)
            filter_result.keyword_filtered_count = data.get("keyword_filtered_count", 0)
            filter_result.ai_filtered_count = data.get("ai_filtered_count", 0)
            
            return filter_result
            
        except Exception as e:
            logger.warning(f"反序列化筛选结果失败: {e}")
            return None


# 全局筛选结果缓存实例
_filter_result_cache = None


def get_filter_result_cache() -> FilterResultCache:
    """获取全局筛选结果缓存实例"""
    global _filter_result_cache
    if _filter_result_cache is None:
        # 使用项目统一的缓存目录配置
        from ..config.settings import Settings
        settings = Settings()
        cache_dir = settings.app.cache_dir
        _filter_result_cache = FilterResultCache(cache_dir=cache_dir)
    return _filter_result_cache
