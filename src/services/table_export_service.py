"""
表格导出服务 - 整合MCP Agent和表格导出器
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..filters.base import CombinedFilterResult
from ..agents.table_export_agent import TableExportAgent
from ..exporters.table_exporter import TableExporter
from ..services.translation_service import get_translation_service, set_translation_service, TranslationService

logger = logging.getLogger(__name__)


class TableExportService:
    """表格导出服务"""
    
    def __init__(self, 
                 enable_translation: bool = True,
                 translation_config: Optional[Dict[str, str]] = None):
        """
        初始化表格导出服务
        
        Args:
            enable_translation: 是否启用翻译功能
            translation_config: 翻译配置 
                {"provider": "youdao|baidu", "app_id": "xxx", "secret_key": "xxx"}
        """
        self.enable_translation = enable_translation
        
        # 配置翻译服务
        if enable_translation:
            # 使用AI大模型翻译服务
            translation_service = TranslationService()
            set_translation_service(translation_service)
            logger.info("已配置AI大模型翻译服务")
        
        # 初始化组件
        self.agent = TableExportAgent(enable_translation=enable_translation)
        self.exporter = TableExporter()
        
        logger.info(f"表格导出服务初始化完成，翻译功能: {'启用' if enable_translation else '禁用'}")
    
    async def export_articles(self, 
                            results: List[CombinedFilterResult],
                            output_format: str = "console",
                            output_path: Optional[str] = None,
                            **export_options) -> Dict[str, Any]:
        """
        导出文章到表格
        
        Args:
            results: 筛选结果列表
            output_format: 输出格式 (console, csv, excel, html, json等)
            output_path: 输出文件路径
            **export_options: 导出选项
            
        Returns:
            导出结果信息
        """
        if not results:
            return {
                "success": False,
                "message": "没有文章可导出",
                "exported_count": 0
            }
        
        try:
            logger.info(f"开始处理 {len(results)} 篇文章...")
            
            # 使用AI Agent处理文章数据
            start_time = datetime.now()
            table_data = await self.agent.process_articles(results)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if not table_data:
                return {
                    "success": False,
                    "message": "文章处理失败，没有生成表格数据",
                    "exported_count": 0
                }
            
            logger.info(f"文章处理完成，耗时 {processing_time:.2f} 秒")
            
            # 导出表格
            export_result = self.exporter.export(
                data=table_data,
                format_type=output_format,
                output_path=output_path,
                **export_options
            )
            
            return {
                "success": True,
                "message": export_result,
                "exported_count": len(table_data),
                "processing_time": processing_time,
                "output_format": output_format,
                "output_path": output_path,
                "table_data": table_data if export_options.get("include_data", False) else None
            }
            
        except Exception as e:
            logger.error(f"导出失败: {e}")
            return {
                "success": False,
                "message": f"导出失败: {str(e)}",
                "exported_count": 0,
                "error": str(e)
            }
    
    def export_articles_sync(self, 
                           results: List[CombinedFilterResult],
                           output_format: str = "console",
                           output_path: Optional[str] = None,
                           **export_options) -> Dict[str, Any]:
        """
        同步版本的文章导出
        
        Args:
            results: 筛选结果列表
            output_format: 输出格式
            output_path: 输出文件路径
            **export_options: 导出选项
            
        Returns:
            导出结果信息
        """
        return asyncio.run(self.export_articles(
            results, output_format, output_path, **export_options
        ))
    
    def get_supported_formats(self) -> List[str]:
        """获取支持的导出格式"""
        return self.exporter.get_supported_formats()
    
    def preview_table_structure(self, results: List[CombinedFilterResult], 
                              sample_size: int = 3) -> Dict[str, Any]:
        """
        预览表格结构
        
        Args:
            results: 筛选结果列表
            sample_size: 样本数量
            
        Returns:
            表格结构预览
        """
        if not results:
            return {"headers": [], "sample_data": [], "total_count": 0}
        
        # 取样本数据
        sample_results = results[:sample_size]
        
        try:
            # 同步处理样本数据
            sample_data = asyncio.run(self.agent.process_articles(sample_results))
            
            headers = list(sample_data[0].keys()) if sample_data else []
            
            return {
                "headers": headers,
                "sample_data": sample_data,
                "total_count": len(results),
                "sample_size": len(sample_data)
            }
            
        except Exception as e:
            logger.error(f"预览失败: {e}")
            return {
                "headers": [],
                "sample_data": [],
                "total_count": len(results),
                "error": str(e)
            }
    
    def export_with_template(self, 
                           results: List[CombinedFilterResult],
                           template_name: str = "default",
                           output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        使用模板导出
        
        Args:
            results: 筛选结果列表
            template_name: 模板名称
            output_path: 输出路径
            
        Returns:
            导出结果
        """
        templates = {
            "default": {
                "format": "excel",
                "options": {
                    "title": "新闻筛选结果",
                    "include_summary": True
                }
            },
            "simple": {
                "format": "csv",
                "options": {
                    "encoding": "utf-8-sig"
                }
            },
            "report": {
                "format": "html",
                "options": {
                    "title": "新闻筛选报告",
                    "include_statistics": True
                }
            }
        }
        
        template = templates.get(template_name, templates["default"])
        
        return self.export_articles_sync(
            results=results,
            output_format=template["format"],
            output_path=output_path,
            **template["options"]
        )
    
    def batch_export(self, 
                    results: List[CombinedFilterResult],
                    formats: List[str],
                    output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        批量导出多种格式
        
        Args:
            results: 筛选结果列表
            formats: 导出格式列表
            output_dir: 输出目录
            
        Returns:
            批量导出结果
        """
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        batch_results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for format_type in formats:
            try:
                if output_dir:
                    if format_type == "excel":
                        output_path = output_dir / f"news_export_{timestamp}.xlsx"
                    elif format_type == "csv":
                        output_path = output_dir / f"news_export_{timestamp}.csv"
                    elif format_type == "html":
                        output_path = output_dir / f"news_export_{timestamp}.html"
                    elif format_type == "json":
                        output_path = output_dir / f"news_export_{timestamp}.json"
                    else:
                        output_path = None
                else:
                    output_path = None
                
                result = self.export_articles_sync(
                    results=results,
                    output_format=format_type,
                    output_path=str(output_path) if output_path else None
                )
                
                batch_results[format_type] = result
                
            except Exception as e:
                logger.error(f"格式 {format_type} 导出失败: {e}")
                batch_results[format_type] = {
                    "success": False,
                    "message": f"导出失败: {str(e)}",
                    "error": str(e)
                }
        
        # 统计结果
        successful_exports = sum(1 for r in batch_results.values() if r.get("success", False))
        
        return {
            "total_formats": len(formats),
            "successful_exports": successful_exports,
            "failed_exports": len(formats) - successful_exports,
            "results": batch_results,
            "output_directory": str(output_dir) if output_dir else None
        }


# 全局服务实例
_table_export_service = None


def get_table_export_service(enable_translation: bool = True,
                           translation_config: Optional[Dict[str, str]] = None) -> TableExportService:
    """
    获取表格导出服务实例
    
    Args:
        enable_translation: 是否启用翻译
        translation_config: 翻译配置
        
    Returns:
        表格导出服务实例
    """
    global _table_export_service
    if _table_export_service is None:
        _table_export_service = TableExportService(
            enable_translation=enable_translation,
            translation_config=translation_config
        )
    return _table_export_service


# 便捷函数
def export_articles_to_table(results: List[CombinedFilterResult],
                           output_format: str = "console",
                           output_path: Optional[str] = None,
                           enable_translation: bool = True,
                           **options) -> Dict[str, Any]:
    """
    导出文章到表格的便捷函数
    
    Args:
        results: 筛选结果列表
        output_format: 输出格式
        output_path: 输出路径
        enable_translation: 是否启用翻译
        **options: 其他选项
        
    Returns:
        导出结果
    """
    service = get_table_export_service(enable_translation=enable_translation)
    return service.export_articles_sync(results, output_format, output_path, **options)


if __name__ == "__main__":
    # 测试代码
    print("表格导出服务测试")
    
    service = get_table_export_service(enable_translation=False)
    print(f"支持的格式: {service.get_supported_formats()}")
    
    # 这里可以添加更多测试代码
