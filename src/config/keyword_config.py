"""
关键词配置管理
"""
import os
import json
from pathlib import Path
from typing import Dict, List


class KeywordConfigManager:
    """关键词配置管理器"""
    
    def __init__(self, config_file: str = "config/keywords.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self._keywords_data = {}
        self.load_keywords()
    
    def load_keywords(self):
        """加载关键词配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._keywords_data = json.load(f)
                print(f"已加载自定义关键词配置: {len(self._keywords_data)} 个分类")
            except Exception as e:
                print(f"加载关键词配置失败: {e}")
                self._load_default_keywords()
        else:
            self._load_default_keywords()
    
    def _load_default_keywords(self):
        """加载默认关键词"""
        try:
            from .default_keywords import INTERNATIONAL_TECH_KEYWORDS
            # 转换格式：从 {category: {keywords: [...], weight: ...}} 到 {category: [...]}
            self._keywords_data = {}
            for category, data in INTERNATIONAL_TECH_KEYWORDS.items():
                self._keywords_data[category] = data.get("keywords", [])
            self.save_keywords()
            print("已加载默认关键词配置")
        except ImportError as e:
            print(f"导入默认关键词失败: {e}")
            # 提供一个最小的默认配置
            self._keywords_data = {
                "artificial_intelligence": ["AI", "artificial intelligence", "machine learning"],
                "technology": ["technology", "innovation", "research"]
            }
            self.save_keywords()
            print("已加载最小默认关键词配置")
    
    def save_keywords(self):
        """保存关键词配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._keywords_data, f, ensure_ascii=False, indent=2)
            print(f"关键词配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"保存关键词配置失败: {e}")
    
    def get_keywords(self) -> Dict[str, List[str]]:
        """获取关键词数据"""
        return self._keywords_data.copy()
    
    def update_keywords(self, keywords_data: Dict[str, List[str]]):
        """更新关键词数据"""
        self._keywords_data = keywords_data.copy()
        self.save_keywords()
    
    def get_category_keywords(self, category: str) -> List[str]:
        """获取指定分类的关键词"""
        return self._keywords_data.get(category, [])
    
    def add_category(self, category: str, keywords: List[str]):
        """添加分类"""
        self._keywords_data[category] = keywords
        self.save_keywords()
    
    def remove_category(self, category: str):
        """删除分类"""
        if category in self._keywords_data:
            del self._keywords_data[category]
            self.save_keywords()
    
    def get_all_keywords(self) -> List[str]:
        """获取所有关键词的扁平列表"""
        all_keywords = []
        for keywords in self._keywords_data.values():
            all_keywords.extend(keywords)
        return all_keywords
    
    def get_statistics(self) -> Dict[str, int]:
        """获取关键词统计信息"""
        total_categories = len(self._keywords_data)
        total_keywords = sum(len(keywords) for keywords in self._keywords_data.values())
        
        category_stats = {}
        for category, keywords in self._keywords_data.items():
            category_stats[category] = len(keywords)
        
        return {
            'total_categories': total_categories,
            'total_keywords': total_keywords,
            'category_stats': category_stats
        }
    
    def reset_to_default(self):
        """重置为默认关键词"""
        self._load_default_keywords()
    
    def export_keywords(self, file_path: str):
        """导出关键词到文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self._keywords_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"导出关键词失败: {e}")
            return False
    
    def import_keywords(self, file_path: str, merge: bool = True):
        """从文件导入关键词"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if not isinstance(imported_data, dict):
                raise ValueError("文件格式不正确")
            
            if merge:
                # 合并模式：更新现有数据
                self._keywords_data.update(imported_data)
            else:
                # 替换模式：完全替换
                self._keywords_data = imported_data
            
            self.save_keywords()
            return True
        except Exception as e:
            print(f"导入关键词失败: {e}")
            return False


# 全局关键词配置管理器实例
keyword_config_manager = KeywordConfigManager()
