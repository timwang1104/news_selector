"""
MCP (Model Context Protocol) 客户端实现
提供结构化的AI分析输出
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from ..models.news import NewsArticle
from ..filters.base import AIEvaluation
from .exceptions import AIClientError

logger = logging.getLogger(__name__)


class StructuredAIEvaluation(BaseModel):
    """结构化AI评估模型"""
    relevance_score: int = Field(ge=0, le=10, description="政策相关性评分(0-10)")
    innovation_impact: int = Field(ge=0, le=10, description="创新影响评分(0-10)")
    practicality: int = Field(ge=0, le=10, description="实用性评分(0-10)")
    total_score: int = Field(ge=0, le=30, description="总分(0-30)")
    reasoning: str = Field(description="详细评估理由")
    confidence: float = Field(ge=0, le=1, description="置信度(0-1)")
    
    # 扩展字段
    summary: Optional[str] = Field(default="", description="文章摘要")
    key_insights: List[str] = Field(default_factory=list, description="关键洞察")
    highlights: List[str] = Field(default_factory=list, description="推荐亮点")
    tags: List[str] = Field(default_factory=list, description="相关标签")
    detailed_analysis: Dict[str, str] = Field(default_factory=dict, description="详细分析")
    recommendation_reason: Optional[str] = Field(default="", description="推荐理由")
    risk_assessment: Optional[str] = Field(default="", description="风险评估")
    implementation_suggestions: List[str] = Field(default_factory=list, description="实施建议")


class MCPClient:
    """MCP客户端，提供结构化AI分析"""
    
    def __init__(self, config):
        self.config = config
        self.mcp_server_url = getattr(config, 'mcp_server_url', None)
        self.api_key = getattr(config, 'api_key', None)
        
    def evaluate_article(self, article: NewsArticle) -> AIEvaluation:
        """使用MCP进行结构化文章评估"""
        try:
            # 构建结构化提示
            structured_prompt = self._build_structured_prompt(article)

            # 调用MCP服务
            mcp_response = self._call_mcp_service(structured_prompt)

            # 解析结构化响应
            structured_eval = self._parse_structured_response(mcp_response)

            # 转换为AIEvaluation对象
            return self._convert_to_ai_evaluation(structured_eval)

        except Exception as e:
            logger.error(f"MCP evaluation failed: {e}")
            return self._fallback_evaluation(article)

    def evaluate_article_with_raw_response(self, article: NewsArticle) -> tuple[AIEvaluation, str]:
        """使用MCP进行结构化文章评估并返回原始响应"""
        try:
            # 构建结构化提示
            structured_prompt = self._build_structured_prompt(article)

            # 调用MCP服务
            mcp_response = self._call_mcp_service(structured_prompt)

            # 解析结构化响应
            structured_eval = self._parse_structured_response(mcp_response)

            # 转换为AIEvaluation对象
            evaluation = self._convert_to_ai_evaluation(structured_eval)

            # 格式化原始响应用于显示
            raw_response = json.dumps(mcp_response, ensure_ascii=False, indent=2)

            return evaluation, raw_response

        except Exception as e:
            logger.error(f"MCP evaluation failed: {e}")
            fallback_eval = self._fallback_evaluation(article)
            fallback_response = f"MCP服务异常，使用降级评估策略。错误信息: {str(e)}"
            return fallback_eval, fallback_response
    
    def _build_structured_prompt(self, article: NewsArticle) -> Dict[str, Any]:
        """构建结构化提示"""
        return {
            "system_prompt": """你是上海市科委的专业顾问，需要评估科技新闻文章的价值。
请严格按照JSON Schema格式返回评估结果。""",
            
            "user_prompt": f"""请评估以下文章：
标题：{article.title}
摘要：{article.summary}
内容：{article.content[:2000] if article.content else '无内容'}

评估维度：
1. 政策相关性(0-10)：与上海科技政策的相关程度
2. 创新影响(0-10)：对科技创新的推动作用  
3. 实用性(0-10)：可操作性和实际应用价值

请提供详细的评估理由和0-1的置信度。""",
            
            "response_format": {
                "type": "json_object",
                "schema": StructuredAIEvaluation.model_json_schema()
            },
            
            "function_call": {
                "name": "submit_evaluation",
                "description": "提交文章评估结果",
                "parameters": StructuredAIEvaluation.model_json_schema()
            }
        }
    
    def _call_mcp_service(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP服务"""
        if not self.mcp_server_url:
            # 如果没有MCP服务，使用模拟的结构化调用
            return self._simulate_structured_call(prompt_data)
        
        # 实际MCP调用实现
        import requests
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else ""
        }
        
        payload = {
            "method": "tools/call",
            "params": {
                "name": "structured_ai_analysis",
                "arguments": prompt_data
            }
        }
        
        response = requests.post(
            f"{self.mcp_server_url}/mcp",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            raise AIClientError(f"MCP service error: {response.status_code}")
        
        return response.json()
    
    def _simulate_structured_call(self, prompt_data: Dict[str, Any]) -> Dict[str, Any]:
        """模拟结构化调用（用于测试）"""
        # 这里可以调用现有的AI客户端，但强制要求结构化输出
        from .volcengine_client import VolcengineClient
        
        volcengine_client = VolcengineClient(self.config)
        
        # 修改提示词，强调JSON格式
        enhanced_prompt = f"""{prompt_data['system_prompt']}

{prompt_data['user_prompt']}

重要：你必须返回严格的JSON格式，不要包含任何其他文字。JSON结构如下：
{json.dumps(StructuredAIEvaluation.model_json_schema(), indent=2, ensure_ascii=False)}

示例输出：
{{
    "relevance_score": 7,
    "innovation_impact": 8,
    "practicality": 6,
    "total_score": 21,
    "reasoning": "详细的评估理由...",
    "confidence": 0.85,
    "summary": "文章摘要...",
    "key_insights": ["洞察1", "洞察2"],
    "highlights": ["亮点1", "亮点2"],
    "tags": ["标签1", "标签2"],
    "detailed_analysis": {{"维度1": "分析1", "维度2": "分析2"}},
    "recommendation_reason": "推荐理由...",
    "risk_assessment": "风险评估...",
    "implementation_suggestions": ["建议1", "建议2"]
}}

请只返回JSON，不要包含任何解释文字："""
        
        # 调用现有客户端
        raw_response = volcengine_client._call_volcengine_api(enhanced_prompt)
        
        return {"content": raw_response}
    
    def _parse_structured_response(self, mcp_response: Dict[str, Any]) -> StructuredAIEvaluation:
        """解析结构化响应"""
        try:
            # 从MCP响应中提取内容
            content = mcp_response.get("content", "")
            
            # 清理和解析JSON
            cleaned_content = self._extract_json_from_response(content)
            data = json.loads(cleaned_content)
            
            # 验证和创建结构化对象
            return StructuredAIEvaluation(**data)
            
        except Exception as e:
            logger.error(f"Failed to parse structured response: {e}")
            logger.error(f"Response content: {mcp_response}")
            raise AIClientError(f"Structured response parsing failed: {e}")
    
    def _extract_json_from_response(self, content: str) -> str:
        """从响应中提取JSON"""
        import re
        
        # 移除markdown标记
        content = content.replace('```json', '').replace('```', '')
        
        # 查找JSON对象
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                # 验证JSON有效性
                json.loads(match)
                return match.strip()
            except:
                continue
        
        # 如果没找到完整JSON，尝试修复
        brace_count = 0
        start_pos = content.find('{')
        if start_pos == -1:
            raise ValueError("No JSON object found in response")
        
        for i, char in enumerate(content[start_pos:], start_pos):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    return content[start_pos:i+1]
        
        raise ValueError("Incomplete JSON object in response")
    
    def _convert_to_ai_evaluation(self, structured_eval: StructuredAIEvaluation) -> AIEvaluation:
        """转换为AIEvaluation对象"""
        return AIEvaluation(
            relevance_score=structured_eval.relevance_score,
            innovation_impact=structured_eval.innovation_impact,
            practicality=structured_eval.practicality,
            total_score=structured_eval.total_score,
            reasoning=structured_eval.reasoning,
            confidence=structured_eval.confidence,
            summary=structured_eval.summary,
            key_insights=structured_eval.key_insights,
            highlights=structured_eval.highlights,
            tags=structured_eval.tags,
            detailed_analysis=structured_eval.detailed_analysis,
            recommendation_reason=structured_eval.recommendation_reason,
            risk_assessment=structured_eval.risk_assessment,
            implementation_suggestions=structured_eval.implementation_suggestions
        )
    
    def _fallback_evaluation(self, article: NewsArticle) -> AIEvaluation:
        """降级评估"""
        return AIEvaluation(
            relevance_score=5,
            innovation_impact=5,
            practicality=5,
            total_score=15,
            reasoning="MCP服务不可用，使用默认评分",
            confidence=0.3,
            summary="MCP服务异常，无法生成摘要",
            key_insights=["MCP服务暂时不可用"],
            highlights=["需要人工审核"],
            tags=["MCP异常"],
            detailed_analysis={"状态": "MCP服务异常"},
            recommendation_reason="MCP服务异常，建议人工审核",
            risk_assessment="MCP服务不可用，评估结果可能不准确",
            implementation_suggestions=["等待MCP服务恢复", "进行人工审核"]
        )


class GlobalMCPClient:
    """
    全局MCP客户端，用于调用各种MCP服务
    """
    
    def __init__(self):
        self.servers = {}
        self.default_timeout = 30
    
    def register_server(self, name: str, url: str, api_key: str = None):
        """
        注册MCP服务器
        
        Args:
            name: 服务器名称
            url: 服务器URL
            api_key: API密钥（可选）
        """
        self.servers[name] = {
            "url": url,
            "api_key": api_key
        }
        logger.info(f"已注册MCP服务器: {name}")
    
    def call_tool(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        调用MCP工具
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        if server_name not in self.servers:
            raise ValueError(f"未注册的MCP服务器: {server_name}")
        
        server_info = self.servers[server_name]
        
        # 如果是本地MCP服务器（如AiryLark），直接调用
        if server_name == "airylark":
            return self._call_local_mcp(tool_name, args)
        
        # 远程MCP服务器调用
        return self._call_remote_mcp(server_info, tool_name, args)
    
    def _call_local_mcp(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        调用本地MCP服务（如AiryLark）
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        # 这里应该调用实际的AiryLark MCP客户端
        # 由于我们没有具体的实现，这里提供一个模拟
        
        if tool_name == "translate":
            text = args.get("text", "")
            target_lang = args.get("target_language", "zh")
            
            # 模拟翻译结果
            if target_lang == "zh":
                return {"translated_text": f"[AiryLark中文翻译] {text}"}
            elif target_lang == "en":
                return {"translated_text": f"[AiryLark English Translation] {text}"}
            else:
                return {"translated_text": text}
        
        raise ValueError(f"不支持的工具: {tool_name}")
    
    def _call_remote_mcp(self, server_info: Dict[str, Any], tool_name: str, args: Dict[str, Any]) -> Any:
        """
        调用远程MCP服务
        
        Args:
            server_info: 服务器信息
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        import requests
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if server_info.get("api_key"):
            headers["Authorization"] = f"Bearer {server_info['api_key']}"
        
        payload = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        response = requests.post(
            f"{server_info['url']}/mcp",
            headers=headers,
            json=payload,
            timeout=self.default_timeout
        )
        
        if response.status_code != 200:
            raise Exception(f"MCP服务调用失败: {response.status_code}")
        
        return response.json()
    
    def is_server_available(self, server_name: str) -> bool:
        """
        检查MCP服务器是否可用
        
        Args:
            server_name: 服务器名称
            
        Returns:
            是否可用
        """
        return server_name in self.servers


# 全局MCP客户端实例
_global_mcp_client = None


def get_global_mcp_client() -> GlobalMCPClient:
    """
    获取全局MCP客户端实例
    
    Returns:
        全局MCP客户端实例
    """
    global _global_mcp_client
    if _global_mcp_client is None:
        _global_mcp_client = GlobalMCPClient()
        # 注册默认的AiryLark服务器
        _global_mcp_client.register_server("airylark", "local://airylark")
    return _global_mcp_client


def set_global_mcp_client(client: GlobalMCPClient):
    """
    设置全局MCP客户端实例
    
    Args:
        client: MCP客户端实例
    """
    global _global_mcp_client
    _global_mcp_client = client
