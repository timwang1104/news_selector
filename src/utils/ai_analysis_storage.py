"""
AI分析结果存储管理器
用于保存和管理AI筛选过程中的分析结果，包括原始响应、评估结果等
"""
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

from ..models.news import NewsArticle
from ..filters.base import AIEvaluation, AIFilterResult
from ..config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class AIAnalysisRecord:
    """AI分析记录"""
    article_id: str
    article_title: str
    article_url: str
    evaluation: AIEvaluation
    raw_response: str
    ai_model: str
    processing_time: float
    created_at: str
    cached: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'article_id': self.article_id,
            'article_title': self.article_title,
            'article_url': self.article_url,
            'evaluation': {
                'relevance_score': self.evaluation.relevance_score,
                'innovation_impact': self.evaluation.innovation_impact,
                'practicality': self.evaluation.practicality,
                'total_score': self.evaluation.total_score,
                'confidence': self.evaluation.confidence,
                'reasoning': self.evaluation.reasoning,
                'key_insights': self.evaluation.key_insights,
                'highlights': self.evaluation.highlights,
                'tags': self.evaluation.tags,
                'detailed_analysis': self.evaluation.detailed_analysis,
                'implementation_suggestions': self.evaluation.implementation_suggestions
            },
            'raw_response': self.raw_response,
            'ai_model': self.ai_model,
            'processing_time': self.processing_time,
            'created_at': self.created_at,
            'cached': self.cached
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIAnalysisRecord':
        """从字典创建"""
        eval_data = data['evaluation']
        evaluation = AIEvaluation(
            relevance_score=eval_data['relevance_score'],
            innovation_impact=eval_data['innovation_impact'],
            practicality=eval_data['practicality'],
            total_score=eval_data['total_score'],
            confidence=eval_data['confidence'],
            reasoning=eval_data.get('reasoning', ''),
            key_insights=eval_data.get('key_insights', []),
            highlights=eval_data.get('highlights', []),
            tags=eval_data.get('tags', []),
            detailed_analysis=eval_data.get('detailed_analysis', {}),
            implementation_suggestions=eval_data.get('implementation_suggestions', [])
        )
        
        return cls(
            article_id=data['article_id'],
            article_title=data['article_title'],
            article_url=data['article_url'],
            evaluation=evaluation,
            raw_response=data['raw_response'],
            ai_model=data['ai_model'],
            processing_time=data['processing_time'],
            created_at=data['created_at'],
            cached=data.get('cached', False)
        )


class AIAnalysisStorage:
    """AI分析结果存储管理器"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or settings.app.cache_dir) / "ai_analysis"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # 存储配置
        self.enabled = True
        self.expire_days = 30  # 分析结果保存30天
        self.max_records = 1000  # 最大记录数
        
        # 索引文件
        self.index_file = self.storage_dir / "analysis_index.json"
        self.analysis_index = self._load_analysis_index()
        
        # 定期清理过期记录
        self._cleanup_expired_records()
    
    def _load_analysis_index(self) -> Dict[str, Dict[str, Any]]:
        """加载分析索引"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载AI分析索引失败: {e}")
        return {}
    
    def _save_analysis_index(self):
        """保存分析索引"""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存AI分析索引失败: {e}")
    
    def _generate_record_key(self, article: NewsArticle) -> str:
        """生成记录键值"""
        # 使用文章ID和标题生成唯一键
        content = f"{article.id}{article.title}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def _get_record_file_path(self, record_key: str) -> Path:
        """获取记录文件路径"""
        return self.storage_dir / f"{record_key}.json"
    
    def _is_record_valid(self, record_info: Dict[str, Any]) -> bool:
        """检查记录是否有效（未过期）"""
        try:
            created_at = datetime.fromisoformat(record_info['created_at'])
            now = datetime.now(timezone.utc)
            age_days = (now - created_at).days
            return age_days < self.expire_days
        except Exception:
            return False
    
    def save_analysis(self, article: NewsArticle, ai_result: AIFilterResult, raw_response: str = ""):
        """保存AI分析结果"""
        if not self.enabled:
            return
        
        record_key = self._generate_record_key(article)
        record_file = self._get_record_file_path(record_key)
        
        try:
            # 创建分析记录
            record = AIAnalysisRecord(
                article_id=article.id,
                article_title=article.title,
                article_url=article.url or "",
                evaluation=ai_result.evaluation,
                raw_response=raw_response,
                ai_model=ai_result.ai_model,
                processing_time=ai_result.processing_time,
                created_at=datetime.now(timezone.utc).isoformat(),
                cached=ai_result.cached
            )
            
            # 保存记录文件
            with open(record_file, 'w', encoding='utf-8') as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
            
            # 更新索引
            self.analysis_index[record_key] = {
                'article_id': article.id,
                'article_title': article.title,
                'ai_model': ai_result.ai_model,
                'total_score': ai_result.evaluation.total_score,
                'created_at': record.created_at,
                'file_size': record_file.stat().st_size
            }
            
            self._save_analysis_index()
            logger.debug(f"AI分析结果已保存: {article.title[:50]}...")
            
            # 检查记录数量限制
            self._check_records_limit()
            
        except Exception as e:
            logger.error(f"保存AI分析结果失败: {e}")
    
    def get_analysis(self, article: NewsArticle) -> Optional[AIAnalysisRecord]:
        """获取AI分析结果"""
        if not self.enabled:
            return None
        
        record_key = self._generate_record_key(article)
        record_info = self.analysis_index.get(record_key)
        
        if not record_info or not self._is_record_valid(record_info):
            return None
        
        record_file = self._get_record_file_path(record_key)
        if not record_file.exists():
            # 记录文件不存在，清理索引
            self.analysis_index.pop(record_key, None)
            self._save_analysis_index()
            return None
        
        try:
            with open(record_file, 'r', encoding='utf-8') as f:
                record_data = json.load(f)
            
            logger.debug(f"AI分析结果命中: {article.title[:50]}...")
            return AIAnalysisRecord.from_dict(record_data)
            
        except Exception as e:
            logger.error(f"读取AI分析结果失败: {e}")
            return None
    
    def has_analysis(self, article: NewsArticle) -> bool:
        """检查是否存在AI分析结果"""
        record_key = self._generate_record_key(article)
        record_info = self.analysis_index.get(record_key)
        
        if not record_info or not self._is_record_valid(record_info):
            return False
        
        record_file = self._get_record_file_path(record_key)
        return record_file.exists()
    
    def _cleanup_expired_records(self):
        """清理过期记录"""
        try:
            expired_keys = []
            for record_key, record_info in self.analysis_index.items():
                if not self._is_record_valid(record_info):
                    expired_keys.append(record_key)
            
            for key in expired_keys:
                # 删除文件
                record_file = self._get_record_file_path(key)
                if record_file.exists():
                    record_file.unlink()
                
                # 从索引中删除
                self.analysis_index.pop(key, None)
            
            if expired_keys:
                self._save_analysis_index()
                logger.info(f"清理了 {len(expired_keys)} 个过期的AI分析记录")
                
        except Exception as e:
            logger.error(f"清理过期AI分析记录失败: {e}")
    
    def _check_records_limit(self):
        """检查记录数量限制"""
        if len(self.analysis_index) <= self.max_records:
            return
        
        try:
            # 按创建时间排序，删除最旧的记录
            sorted_records = sorted(
                self.analysis_index.items(),
                key=lambda x: x[1]['created_at']
            )
            
            records_to_remove = len(self.analysis_index) - self.max_records
            for i in range(records_to_remove):
                record_key, _ = sorted_records[i]
                
                # 删除文件
                record_file = self._get_record_file_path(record_key)
                if record_file.exists():
                    record_file.unlink()
                
                # 从索引中删除
                self.analysis_index.pop(record_key, None)
            
            self._save_analysis_index()
            logger.info(f"清理了 {records_to_remove} 个旧的AI分析记录以保持数量限制")
            
        except Exception as e:
            logger.error(f"清理旧AI分析记录失败: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        total_records = len(self.analysis_index)
        total_size = sum(info.get('file_size', 0) for info in self.analysis_index.values())
        
        return {
            'total_records': total_records,
            'total_size_mb': total_size / (1024 * 1024),
            'storage_dir': str(self.storage_dir),
            'enabled': self.enabled
        }


# 全局实例
ai_analysis_storage = AIAnalysisStorage()
