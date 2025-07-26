"""
MCP服务器 - 表格导出功能
提供文章字段处理、翻译、格式化等工具供AI Agent使用
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# 简化的MCP服务器实现（如果没有标准MCP库）
class MCPTool:
    """MCP工具基类"""
    def __init__(self, name: str, description: str, handler: Callable):
        self.name = name
        self.description = description
        self.handler = handler


class MCPServer:
    """简化的MCP服务器实现"""
    def __init__(self, name: str):
        self.name = name
        self.tools = {}
        self.resources = {}

    def tool(self, name: str, description: str = ""):
        """工具装饰器"""
        def decorator(func):
            self.tools[name] = MCPTool(name, description, func)
            return func
        return decorator

    def resource(self, name: str):
        """资源装饰器"""
        def decorator(func):
            self.resources[name] = func
            return func
        return decorator

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if tool_name not in self.tools:
            return {"error": f"Tool {tool_name} not found"}

        try:
            tool = self.tools[tool_name]
            if asyncio.iscoroutinefunction(tool.handler):
                return await tool.handler(**params)
            else:
                return tool.handler(**params)
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return {"error": str(e)}

    async def get_resource(self, resource_name: str) -> str:
        """获取资源"""
        if resource_name not in self.resources:
            return f"Resource {resource_name} not found"

        try:
            resource_func = self.resources[resource_name]
            if asyncio.iscoroutinefunction(resource_func):
                return await resource_func()
            else:
                return resource_func()
        except Exception as e:
            logger.error(f"Resource {resource_name} access failed: {e}")
            return f"Error: {str(e)}"


class TableExportMCPServer:
    """表格导出MCP服务器"""

    def __init__(self):
        self.server = MCPServer("table-export-server")
        self.setup_tools()
        self.setup_resources()
        
        # 配置数据
        self.publisher_mapping = {
            'arxiv.org': 'arXiv',
            'nature.com': 'Nature Publishing Group',
            'science.org': 'American Association for the Advancement of Science',
            'ieee.org': 'Institute of Electrical and Electronics Engineers',
            'acm.org': 'Association for Computing Machinery',
            'mit.edu': 'Massachusetts Institute of Technology',
            'stanford.edu': 'Stanford University',
            'gov.cn': '中国政府网',
            'xinhuanet.com': '新华网',
            'people.com.cn': '人民网'
        }
        
        self.report_type_patterns = {
            '学术论文': [r'arxiv\.org', r'doi\.org', r'paper', r'journal', r'conference'],
            '政策文件': [r'gov\.', r'policy', r'regulation', r'guideline', r'政策', r'规定'],
            '技术白皮书': [r'whitepaper', r'technical.*report', r'白皮书', r'技术报告'],
            '新闻报道': [r'news', r'报道', r'新闻', r'announcement'],
            '研究报告': [r'research.*report', r'study', r'analysis', r'研究报告', r'分析报告'],
            '产业报告': [r'industry.*report', r'market.*analysis', r'产业报告', r'市场分析']
        }
    
    def setup_tools(self):
        """设置MCP工具"""

        @self.server.tool("extract_article_fields", "从文章数据中提取表格所需的字段")
        def extract_article_fields(article_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            从文章数据中提取表格所需的字段
            
            Args:
                article_data: 包含文章信息的字典
                
            Returns:
                提取的字段数据
            """
            try:
                return {
                    "original_title": article_data.get("title", ""),
                    "summary": article_data.get("summary", ""),
                    "content": article_data.get("content", ""),
                    "url": article_data.get("url", ""),
                    "published": article_data.get("published", ""),
                    "feed_title": article_data.get("feed_title", ""),
                    "author": article_data.get("author", {}),
                    "final_score": article_data.get("final_score", 0),
                    "tags": article_data.get("tags", [])
                }
            except Exception as e:
                logger.error(f"字段提取失败: {e}")
                return {"error": str(e)}
        
        @self.server.tool("detect_language", "检测文本语言")
        def detect_language(text: str) -> Dict[str, Any]:
            """
            检测文本语言

            Args:
                text: 要检测的文本

            Returns:
                语言检测结果
            """
            try:
                chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
                english_chars = len(re.findall(r'[a-zA-Z]', text))
                total_chars = len(text.replace(' ', ''))

                if total_chars == 0:
                    return {"language": "unknown", "confidence": 0}

                chinese_ratio = chinese_chars / total_chars
                english_ratio = english_chars / total_chars

                if chinese_ratio > 0.3:
                    return {"language": "chinese", "confidence": chinese_ratio}
                elif english_ratio > 0.5:
                    return {"language": "english", "confidence": english_ratio}
                else:
                    return {"language": "mixed", "confidence": max(chinese_ratio, english_ratio)}

            except Exception as e:
                logger.error(f"语言检测失败: {e}")
                return {"error": str(e)}
        
        @self.server.tool("extract_publisher", "提取发布单位")
        def extract_publisher(article_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            提取发布单位
            
            Args:
                article_data: 文章数据
                
            Returns:
                发布单位信息
            """
            try:
                # 优先使用feed_title
                if article_data.get("feed_title"):
                    return {
                        "publisher": article_data["feed_title"],
                        "source": "feed_title",
                        "confidence": 0.9
                    }
                
                # 从URL域名推断
                url = article_data.get("url", "")
                if url:
                    domain = urlparse(url).netloc.lower()
                    for key, publisher in self.publisher_mapping.items():
                        if key in domain:
                            return {
                                "publisher": publisher,
                                "source": "domain_mapping",
                                "confidence": 0.8
                            }
                
                # 从内容中提取
                content = article_data.get("content", "")
                publisher = self._extract_publisher_from_content(content)
                if publisher:
                    return {
                        "publisher": publisher,
                        "source": "content_extraction",
                        "confidence": 0.6
                    }
                
                return {
                    "publisher": "未知来源",
                    "source": "default",
                    "confidence": 0.1
                }
                
            except Exception as e:
                logger.error(f"发布单位提取失败: {e}")
                return {"error": str(e)}
        
        @self.server.tool("determine_report_type", "判断报告类型")
        def determine_report_type(article_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            判断报告类型
            
            Args:
                article_data: 文章数据
                
            Returns:
                报告类型信息
            """
            try:
                title = article_data.get("title", "").lower()
                url = article_data.get("url", "").lower()
                content = article_data.get("content", "").lower()
                
                text_to_analyze = f"{title} {content[:500]}"
                
                # 基于模式匹配判断
                for report_type, patterns in self.report_type_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, text_to_analyze) or re.search(pattern, url):
                            return {
                                "report_type": report_type,
                                "matched_pattern": pattern,
                                "confidence": 0.8
                            }
                
                # 基于标签判断
                tags = article_data.get("tags", [])
                if tags:
                    primary_tag = max(tags, key=lambda t: t.get("score", 0))
                    tag_name = primary_tag.get("name", "").lower()
                    
                    if "policy" in tag_name or "regulation" in tag_name:
                        return {"report_type": "政策文件", "source": "tag", "confidence": 0.7}
                    elif "research" in tag_name or "academic" in tag_name:
                        return {"report_type": "研究报告", "source": "tag", "confidence": 0.7}
                
                return {
                    "report_type": "其他",
                    "source": "default",
                    "confidence": 0.3
                }
                
            except Exception as e:
                logger.error(f"报告类型判断失败: {e}")
                return {"error": str(e)}
        
        @self.server.tool("format_publish_time", "格式化发布时间")
        def format_publish_time(timestamp: str) -> Dict[str, Any]:
            """
            格式化发布时间
            
            Args:
                timestamp: 时间戳字符串
                
            Returns:
                格式化的时间信息
            """
            try:
                if not timestamp:
                    return {"formatted_time": "未知时间", "iso_format": ""}
                
                # 尝试解析时间戳
                if isinstance(timestamp, str):
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    except:
                        dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                else:
                    dt = timestamp
                
                return {
                    "formatted_time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "iso_format": dt.isoformat(),
                    "date_only": dt.strftime("%Y-%m-%d"),
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day
                }
                
            except Exception as e:
                logger.error(f"时间格式化失败: {e}")
                return {"error": str(e)}
        
        @self.server.tool("clean_content", "清理文章内容")
        def clean_content(content: str, max_length: int = 5000) -> Dict[str, Any]:
            """
            清理文章内容
            
            Args:
                content: 原始内容
                max_length: 最大长度
                
            Returns:
                清理后的内容
            """
            try:
                if not content:
                    return {"cleaned_content": "无内容", "length": 0}
                
                # 移除HTML标签
                content = re.sub(r'<[^>]+>', '', content)
                
                # 规范化空白字符
                content = re.sub(r'\s+', ' ', content)
                
                # 移除特殊字符
                content = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[\]{}"\'-]', '', content)
                
                # 限制长度
                if len(content) > max_length:
                    content = content[:max_length] + "..."
                
                return {
                    "cleaned_content": content.strip(),
                    "length": len(content),
                    "truncated": len(content) > max_length
                }
                
            except Exception as e:
                logger.error(f"内容清理失败: {e}")
                return {"error": str(e)}

        @self.server.tool("extract_ai_reasoning", "提取AI评估理由")
        def extract_ai_reasoning(article_data: Dict[str, Any]) -> Dict[str, Any]:
            """
            提取AI评估理由

            Args:
                article_data: 文章数据，包含AI评估信息

            Returns:
                包含AI评估理由的字典
            """
            try:
                ai_reasoning = article_data.get("ai_reasoning", "")

                # 如果没有AI评估理由，返回默认值
                if not ai_reasoning:
                    ai_reasoning = "无AI评估理由"

                # 清理和格式化AI评估理由
                if len(ai_reasoning) > 500:
                    ai_reasoning = ai_reasoning[:500] + "..."

                return {
                    "ai_reasoning": ai_reasoning.strip()
                }

            except Exception as e:
                logger.error(f"提取AI评估理由失败: {e}")
                return {
                    "ai_reasoning": f"提取失败: {str(e)}"
                }

        @self.server.tool("create_table_row", "创建表格行数据")
        def create_table_row(processed_fields: Dict[str, Any]) -> Dict[str, Any]:
            """
            创建表格行数据
            
            Args:
                processed_fields: 处理后的字段数据
                
            Returns:
                表格行数据
            """
            try:
                return {
                    "中文标题": processed_fields.get("chinese_title", ""),
                    "英文标题": processed_fields.get("english_title", ""),
                    "中文摘要": processed_fields.get("chinese_summary", ""),
                    "发布单位": processed_fields.get("publisher", ""),
                    "发布时间": processed_fields.get("publish_time", ""),
                    "原文全文": processed_fields.get("content", ""),
                    "报告类型": processed_fields.get("report_type", ""),
                    "链接": processed_fields.get("url", ""),
                    "评分": processed_fields.get("final_score", 0),
                    "标签": processed_fields.get("tags", ""),
                    "AI评估理由": processed_fields.get("ai_reasoning", "")
                }
                
            except Exception as e:
                logger.error(f"表格行创建失败: {e}")
                return {"error": str(e)}
    
    def setup_resources(self):
        """设置MCP资源"""
        
        @self.server.resource("publisher_mapping")
        def get_publisher_mapping() -> str:
            """获取发布单位映射表"""
            return json.dumps(self.publisher_mapping, ensure_ascii=False, indent=2)

        @self.server.resource("report_type_patterns")
        def get_report_type_patterns() -> str:
            """获取报告类型模式"""
            return json.dumps(self.report_type_patterns, ensure_ascii=False, indent=2)
    
    def _extract_publisher_from_content(self, content: str) -> Optional[str]:
        """从内容中提取发布单位"""
        if not content:
            return None
        
        patterns = [
            r'发布[单位机构][:：]\s*([^\n\r]{2,50})',
            r'来源[:：]\s*([^\n\r]{2,50})',
            r'出版[社方][:：]\s*([^\n\r]{2,50})',
            r'Published by[:：]\s*([^\n\r]{2,50})',
            r'Source[:：]\s*([^\n\r]{2,50})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content[:1000])
            if match:
                publisher = match.group(1).strip()
                if 2 < len(publisher) < 50:
                    return publisher
        
        return None
    
    def start(self):
        """启动MCP服务器"""
        logger.info(f"MCP服务器 {self.server.name} 已启动")
        logger.info(f"可用工具: {list(self.server.tools.keys())}")
        logger.info(f"可用资源: {list(self.server.resources.keys())}")

    def stop(self):
        """停止MCP服务器"""
        logger.info(f"MCP服务器 {self.server.name} 已停止")


# MCP服务器实例
table_export_server = TableExportMCPServer()


if __name__ == "__main__":
    def main():
        table_export_server.start()
        print("表格导出MCP服务器已启动")

        # 测试工具调用
        test_data = {
            "title": "AI技术发展报告",
            "summary": "这是一篇关于人工智能技术发展的报告",
            "content": "人工智能技术正在快速发展...",
            "url": "https://example.com/ai-report",
            "published": "2024-01-01T10:00:00",
            "feed_title": "科技日报"
        }

        # 测试语言检测
        import asyncio
        async def test_tools():
            lang_result = await table_export_server.server.call_tool("detect_language", {"text": test_data["title"]})
            print(f"语言检测结果: {lang_result}")

            publisher_result = await table_export_server.server.call_tool("extract_publisher", {"article_data": test_data})
            print(f"发布单位提取结果: {publisher_result}")

        asyncio.run(test_tools())

    main()
