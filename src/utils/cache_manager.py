"""
缓存管理器 - 用于API响应结果的本地缓存
"""
import os
import json
import hashlib
import time
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
from pathlib import Path

from ..config.settings import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """API响应缓存管理器"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or settings.app.cache_dir) / "api_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 缓存配置
        self.enabled = settings.app.cache_enabled
        self.expire_hours = settings.app.cache_expire_hours
        self.max_size_mb = settings.app.max_cache_size_mb
        
        # 缓存索引文件
        self.index_file = self.cache_dir / "cache_index.json"
        self.cache_index = self._load_cache_index()
        
        # 定期清理过期缓存
        self._cleanup_expired_cache()
    
    def _load_cache_index(self) -> Dict[str, Dict[str, Any]]:
        """加载缓存索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载缓存索引失败: {e}")
        return {}
    
    def _save_cache_index(self):
        """保存缓存索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存缓存索引失败: {e}")
    
    def _generate_cache_key(self, endpoint: str, params: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        # 创建唯一的缓存键
        key_data = {
            'endpoint': endpoint,
            'params': params or {}
        }
        
        # 对参数进行排序以确保一致性
        if params:
            key_data['params'] = dict(sorted(params.items()))
        
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _get_cache_file_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.json"
    
    def _is_cache_valid(self, cache_info: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if not cache_info:
            return False
        
        # 检查过期时间
        created_time = datetime.fromisoformat(cache_info['created_at'])
        expire_time = created_time + timedelta(hours=self.expire_hours)
        
        return datetime.now() < expire_time
    
    def get(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Any]:
        """获取缓存数据"""
        if not self.enabled:
            return None
        
        cache_key = self._generate_cache_key(endpoint, params)
        cache_info = self.cache_index.get(cache_key)
        
        if not cache_info or not self._is_cache_valid(cache_info):
            return None
        
        cache_file = self._get_cache_file_path(cache_key)
        if not cache_file.exists():
            # 缓存文件不存在，清理索引
            self.cache_index.pop(cache_key, None)
            self._save_cache_index()
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            
            # 更新访问时间
            cache_info['last_accessed'] = datetime.now().isoformat()
            self._save_cache_index()
            
            logger.debug(f"缓存命中: {endpoint}")
            return cached_data['data']
            
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")
            return None
    
    def set(self, endpoint: str, data: Any, params: Dict[str, Any] = None):
        """设置缓存数据"""
        if not self.enabled:
            return
        
        cache_key = self._generate_cache_key(endpoint, params)
        cache_file = self._get_cache_file_path(cache_key)
        
        try:
            # 保存缓存数据
            cache_data = {
                'data': data,
                'endpoint': endpoint,
                'params': params,
                'created_at': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 更新缓存索引
            self.cache_index[cache_key] = {
                'endpoint': endpoint,
                'params': params,
                'created_at': cache_data['created_at'],
                'last_accessed': cache_data['created_at'],
                'file_size': cache_file.stat().st_size
            }
            
            self._save_cache_index()
            logger.debug(f"缓存已保存: {endpoint}")
            
            # 检查缓存大小限制
            self._check_cache_size_limit()
            
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
    
    def invalidate(self, endpoint: str, params: Dict[str, Any] = None):
        """使特定缓存失效"""
        cache_key = self._generate_cache_key(endpoint, params)
        
        # 删除缓存文件
        cache_file = self._get_cache_file_path(cache_key)
        if cache_file.exists():
            cache_file.unlink()
        
        # 从索引中移除
        self.cache_index.pop(cache_key, None)
        self._save_cache_index()
        
        logger.debug(f"缓存已失效: {endpoint}")
    
    def clear_all(self):
        """清空所有缓存"""
        try:
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.json"):
                if cache_file.name != "cache_index.json":
                    cache_file.unlink()
            
            # 清空索引
            self.cache_index.clear()
            self._save_cache_index()
            
            logger.info("所有缓存已清空")
            
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
    
    def _cleanup_expired_cache(self):
        """清理过期的缓存"""
        expired_keys = []
        
        for cache_key, cache_info in self.cache_index.items():
            if not self._is_cache_valid(cache_info):
                expired_keys.append(cache_key)
        
        for cache_key in expired_keys:
            cache_file = self._get_cache_file_path(cache_key)
            if cache_file.exists():
                cache_file.unlink()
            self.cache_index.pop(cache_key, None)
        
        if expired_keys:
            self._save_cache_index()
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def _check_cache_size_limit(self):
        """检查缓存大小限制"""
        total_size = sum(info.get('file_size', 0) for info in self.cache_index.values())
        max_size_bytes = self.max_size_mb * 1024 * 1024
        
        if total_size > max_size_bytes:
            # 按最后访问时间排序，删除最旧的缓存
            sorted_items = sorted(
                self.cache_index.items(),
                key=lambda x: x[1].get('last_accessed', ''),
                reverse=False
            )
            
            removed_count = 0
            for cache_key, cache_info in sorted_items:
                cache_file = self._get_cache_file_path(cache_key)
                if cache_file.exists():
                    cache_file.unlink()
                
                total_size -= cache_info.get('file_size', 0)
                self.cache_index.pop(cache_key, None)
                removed_count += 1
                
                if total_size <= max_size_bytes * 0.8:  # 保留20%的空间
                    break
            
            if removed_count > 0:
                self._save_cache_index()
                logger.info(f"缓存大小超限，清理了 {removed_count} 个旧缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_files = len(self.cache_index)
        total_size = sum(info.get('file_size', 0) for info in self.cache_index.values())
        
        # 计算有效缓存数量
        valid_count = sum(1 for info in self.cache_index.values() if self._is_cache_valid(info))
        
        return {
            'enabled': self.enabled,
            'total_files': total_files,
            'valid_files': valid_count,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'max_size_mb': self.max_size_mb,
            'expire_hours': self.expire_hours,
            'cache_dir': str(self.cache_dir)
        }


# 全局缓存管理器实例
cache_manager = CacheManager()
