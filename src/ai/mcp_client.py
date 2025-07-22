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
