"""
表格导出AI Agent - 使用MCP工具处理文章数据并生成表格
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from ..filters.base import CombinedFilterResult
from ..mcp.table_export_server import table_export_server
from ..services.translation_service import get_translation_service

logger = logging.getLogger(__name__)


class TableExportAgent:
    """表格导出AI Agent"""
    
    def __init__(self, enable_translation: bool = True):
        """
        初始化表格导出Agent

        Args:
            enable_translation: 是否启用翻译功能
        """
        self.enable_translation = enable_translation
        self.mcp_server = table_export_server
        self.translation_service = get_translation_service() if enable_translation else None

        # 启动MCP服务器
        self.mcp_server.start()
        
        # AI Agent的系统提示词
        self.system_prompt = """
你是一个专业的文章数据处理专家，负责将筛选后的新闻文章转换为结构化的表格数据。

你的任务是：
1. 分析文章数据，提取关键信息
2. 智能判断文章的语言类型
3. 识别发布单位和报告类型
4. 处理和清理文章内容
5. 生成标准化的表格行数据

你有以下工具可以使用：
- extract_article_fields: 提取文章基础字段
- detect_language: 检测文本语言
- extract_publisher: 提取发布单位
- determine_report_type: 判断报告类型
- format_publish_time: 格式化发布时间
- clean_content: 清理文章内容
- create_table_row: 创建表格行数据

处理原则：
1. 优先使用现有数据，避免不必要的推测
2. 对于语言检测，要准确判断中英文
3. 发布单位要尽可能准确，使用多种方法验证
4. 报告类型要基于内容特征进行合理分类
5. 内容清理要保持原意，去除无关信息

请按照以下步骤处理每篇文章：
1. 提取基础字段
2. 检测标题和摘要的语言
3. 确定发布单位
4. 判断报告类型
5. 格式化时间和清理内容
6. 生成最终的表格行数据
"""
    
    async def process_articles(self, results: List[CombinedFilterResult]) -> List[Dict[str, Any]]:
        """
        处理文章列表，生成表格数据
        
        Args:
            results: 筛选结果列表
            
        Returns:
            表格行数据列表
        """
        table_rows = []
        
        for i, result in enumerate(results):
            try:
                logger.info(f"处理第 {i+1}/{len(results)} 篇文章: {result.article.title[:50]}...")
                
                # 转换为字典格式
                article_data = self._convert_result_to_dict(result)
                
                # 使用AI Agent处理
                processed_row = await self._process_single_article(article_data)
                
                if processed_row and "error" not in processed_row:
                    table_rows.append(processed_row)
                else:
                    logger.warning(f"文章处理失败: {processed_row.get('error', '未知错误')}")
                    
            except Exception as e:
                logger.error(f"处理文章时发生错误: {e}")
                continue
        
        logger.info(f"成功处理 {len(table_rows)} 篇文章")
        return table_rows
    
    async def _process_single_article(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理单篇文章
        
        Args:
            article_data: 文章数据字典
            
        Returns:
            处理后的表格行数据
        """
        try:
            # 步骤1: 提取基础字段
            fields = await self.mcp_server.server.call_tool(
                "extract_article_fields", 
                {"article_data": article_data}
            )
            
            if "error" in fields:
                return fields
            
            # 步骤2: 检测语言
            title_lang = await self.mcp_server.server.call_tool(
                "detect_language",
                {"text": fields["original_title"]}
            )
            
            summary_lang = await self.mcp_server.server.call_tool(
                "detect_language", 
                {"text": fields["summary"]}
            )
            
            # 步骤3: 处理标题（根据语言决定中英文版本）
            chinese_title, english_title = await self._process_titles(
                fields["original_title"], title_lang
            )
            
            # 步骤4: 处理摘要
            chinese_summary = await self._process_summary(
                fields["summary"], summary_lang
            )
            
            # 步骤5: 提取发布单位
            publisher_info = await self.mcp_server.server.call_tool(
                "extract_publisher",
                {"article_data": article_data}
            )
            
            # 步骤6: 判断报告类型
            report_type_info = await self.mcp_server.server.call_tool(
                "determine_report_type",
                {"article_data": article_data}
            )
            
            # 步骤7: 格式化发布时间
            time_info = await self.mcp_server.server.call_tool(
                "format_publish_time",
                {"timestamp": fields["published"]}
            )
            
            # 步骤8: 清理内容
            content_info = await self.mcp_server.server.call_tool(
                "clean_content",
                {"content": fields["content"], "max_length": 5000}
            )
            
            # 步骤9: 组装处理后的字段
            # 步骤9: 提取AI评估理由
            ai_reasoning_result = await self.mcp_server.server.call_tool(
                "extract_ai_reasoning",
                {"article_data": article_data}
            )

            processed_fields = {
                "chinese_title": chinese_title,
                "english_title": english_title,
                "chinese_summary": chinese_summary,
                "publisher": publisher_info.get("publisher", "未知来源"),
                "publish_time": time_info.get("formatted_time", "未知时间"),
                "content": content_info.get("cleaned_content", "无内容"),
                "report_type": report_type_info.get("report_type", "其他"),
                "url": fields["url"],
                "final_score": fields["final_score"],
                "tags": self._format_tags(fields["tags"]),
                "ai_reasoning": ai_reasoning_result.get("ai_reasoning", "无AI评估理由")
            }

            # 步骤10: 创建表格行
            table_row = await self.mcp_server.server.call_tool(
                "create_table_row",
                {"processed_fields": processed_fields}
            )
            
            return table_row
            
        except Exception as e:
            logger.error(f"单篇文章处理失败: {e}")
            return {"error": str(e)}
    
    async def _process_titles(self, original_title: str, lang_info: Dict[str, Any]) -> tuple:
        """
        处理标题，生成中英文版本

        Args:
            original_title: 原始标题
            lang_info: 语言检测信息

        Returns:
            (中文标题, 英文标题)
        """
        language = lang_info.get("language", "unknown")

        if language == "chinese":
            chinese_title = original_title
            if self.enable_translation and self.translation_service:
                english_title = self.translation_service.translate_to_english(original_title)
            else:
                english_title = f"[Chinese] {original_title}"
        elif language == "english":
            english_title = original_title
            if self.enable_translation and self.translation_service:
                chinese_title = self.translation_service.translate_to_chinese(original_title)
            else:
                chinese_title = f"[英文] {original_title}"
        else:
            # 混合语言或未知语言
            chinese_title = original_title
            english_title = original_title

        return chinese_title, english_title
    
    async def _process_summary(self, original_summary: str, lang_info: Dict[str, Any]) -> str:
        """
        处理摘要，生成中文版本

        Args:
            original_summary: 原始摘要
            lang_info: 语言检测信息

        Returns:
            中文摘要
        """
        if not original_summary:
            return "无摘要"

        language = lang_info.get("language", "unknown")

        if language == "chinese":
            return original_summary
        elif language == "english" and self.enable_translation and self.translation_service:
            return self.translation_service.translate_to_chinese(original_summary)
        else:
            return f"[原文摘要] {original_summary[:200]}..."
    
    def _convert_result_to_dict(self, result: CombinedFilterResult) -> Dict[str, Any]:
        """
        将筛选结果转换为字典格式
        
        Args:
            result: 筛选结果
            
        Returns:
            字典格式的文章数据
        """
        article = result.article
        
        # 提取AI评估理由
        ai_reasoning = ""
        if result.ai_result and hasattr(result.ai_result, 'reasoning'):
            ai_reasoning = result.ai_result.reasoning
        elif result.ai_result and hasattr(result.ai_result, 'evaluation') and hasattr(result.ai_result.evaluation, 'reasoning'):
            ai_reasoning = result.ai_result.evaluation.reasoning
        elif result.ai_result and hasattr(result.ai_result, 'reason'):
            ai_reasoning = result.ai_result.reason

        return {
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "url": article.url,
            "published": article.published.isoformat() if article.published else "",
            "feed_title": article.feed_title,
            "author": {
                "name": article.author.name if article.author else "",
                "email": article.author.email if article.author else ""
            },
            "final_score": result.final_score,
            "ai_reasoning": ai_reasoning,
            "tags": [
                {
                    "name": tag.name,
                    "score": tag.score,
                    "confidence": tag.confidence,
                    "source": tag.source
                }
                for tag in (result.tags or [])
            ]
        }
    
    def _format_tags(self, tags: List[Dict[str, Any]]) -> str:
        """
        格式化标签列表
        
        Args:
            tags: 标签列表
            
        Returns:
            格式化的标签字符串
        """
        if not tags:
            return ""
        
        tag_names = [tag.get("name", "") for tag in tags]
        return ", ".join(filter(None, tag_names))


# 使用示例
async def export_articles_to_table(results: List[CombinedFilterResult]) -> List[Dict[str, Any]]:
    """
    导出文章到表格格式
    
    Args:
        results: 筛选结果列表
        
    Returns:
        表格数据列表
    """
    agent = TableExportAgent(enable_translation=True)
    return await agent.process_articles(results)


if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        """测试Agent功能"""
        # 这里可以添加测试代码
        print("表格导出Agent测试")
    
    asyncio.run(test_agent())
