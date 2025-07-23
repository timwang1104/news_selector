"""
硅基流动AI客户端适配器
"""
import json
import logging
from typing import List, Optional
from ..models.news import NewsArticle
from ..filters.base import AIEvaluation
from .client import AIClient
from .exceptions import AIClientError

logger = logging.getLogger(__name__)


class SiliconFlowClient(AIClient):
    """硅基流动AI客户端，继承自基础AI客户端"""
    
    def __init__(self, config):
        super().__init__(config)
        self.provider = "siliconflow"
    
    def _build_evaluation_prompt(self, article: NewsArticle) -> str:
        """构建硅基流动优化的评估提示词"""
        # 优先使用Agent配置的提示词
        if self.agent_config and self.agent_config.prompt_config.evaluation_prompt:
            template = self.agent_config.prompt_config.evaluation_prompt
        else:
            # 硅基流动优化的默认提示词
            template = """
你是上海市科委的专业顾问，请评估以下科技新闻文章对上海科技发展的相关性和价值。

文章信息：
标题：{title}
摘要：{summary}
内容预览：{content_preview}

请从以下三个维度进行评估（每个维度0-10分）：

1. 政策相关性 (0-10分)
   - 与上海科技政策的相关程度
   - 对政策制定和执行的参考价值

2. 创新影响 (0-10分)
   - 对科技创新的推动作用
   - 技术前沿性和突破性

3. 实用性 (0-10分)
   - 可操作性和可实施性
   - 对实际工作的指导意义

请严格按照以下JSON格式返回评估结果，不要包含其他内容：
{{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由>",
    "confidence": <置信度，0-1之间的小数>
}}

注意：请确保返回的是有效的JSON格式，不要包含markdown代码块标记。
"""
        
        return template.format(
            title=article.title or "无标题",
            summary=article.summary or "无摘要",
            content_preview=self._get_content_preview(article)
        )

    def evaluate_article_with_raw_response(self, article: NewsArticle) -> tuple[AIEvaluation, str]:
        """评估单篇文章并返回原始响应"""
        try:
            prompt = self._build_evaluation_prompt(article)
            raw_response = self._call_ai_api(prompt)
            evaluation = self._parse_ai_response(raw_response)
            return evaluation, raw_response
        except Exception as e:
            logger.error(f"SiliconFlow AI evaluation failed for article {article.id}: {e}")
            fallback_eval = self._fallback_evaluation(article)
            fallback_response = f"硅基流动AI服务异常，使用降级评估策略。错误信息: {str(e)}"
            return fallback_eval, fallback_response
    
    def _build_batch_prompt(self, articles: List[NewsArticle]) -> str:
        """构建硅基流动优化的批量评估提示词"""
        articles_info = []
        for i, article in enumerate(articles):
            article_info = f"""
文章 {i}:
标题: {article.title or "无标题"}
摘要: {article.summary or "无摘要"}
内容预览: {self._get_content_preview(article)}
"""
            articles_info.append(article_info)
        
        # 优先使用Agent配置的批量提示词
        if self.agent_config and self.agent_config.prompt_config.batch_evaluation_prompt:
            template = self.agent_config.prompt_config.batch_evaluation_prompt
        else:
            # 硅基流动优化的默认批量提示词
            template = """
你是上海市科委的专业顾问，请批量评估以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。

请严格按照以下JSON数组格式返回结果，不要包含其他内容：
[
    {{
        "article_index": 0,
        "relevance_score": <分数>,
        "innovation_impact": <分数>,
        "practicality": <分数>,
        "total_score": <总分>,
        "reasoning": "<评估理由>",
        "confidence": <置信度>
    }},
    ...
]

注意：请确保返回的是有效的JSON数组格式，不要包含markdown代码块标记。
"""
        
        return template.format(
            articles_info="\n".join(articles_info)
        )
    
    def _parse_ai_response(self, response_text: str) -> AIEvaluation:
        """解析硅基流动的AI响应，增强JSON解析"""
        try:
            # 清理响应文本
            cleaned_text = self._clean_response_text(response_text)
            
            # 解析JSON
            data = json.loads(cleaned_text)
            
            # 验证必需字段
            required_fields = ['relevance_score', 'innovation_impact', 'practicality', 'total_score']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return AIEvaluation(
                relevance_score=int(data['relevance_score']),
                innovation_impact=int(data['innovation_impact']),
                practicality=int(data['practicality']),
                total_score=int(data['total_score']),
                reasoning=data.get('reasoning', ''),
                confidence=float(data.get('confidence', 0.8))
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SiliconFlow AI response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 尝试从文本中提取分数
            return self._extract_scores_from_text(response_text)
            
        except (ValueError, KeyError) as e:
            logger.error(f"Invalid SiliconFlow AI response format: {e}")
            raise AIClientError(f"Invalid AI response format: {e}")
    
    def _clean_response_text(self, text: str) -> str:
        """清理响应文本，移除markdown标记等"""
        # 移除markdown代码块标记
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        
        if text.endswith('```'):
            text = text[:-3]
        
        # 移除前后空白
        text = text.strip()
        
        # 查找JSON对象的开始和结束
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx + 1]
        
        return text
    
    def _extract_scores_from_text(self, text: str) -> AIEvaluation:
        """从文本中提取分数（降级方案）"""
        import re
        
        # 尝试提取数字分数
        relevance_match = re.search(r'政策相关性[：:]\s*(\d+)', text)
        innovation_match = re.search(r'创新影响[：:]\s*(\d+)', text)
        practicality_match = re.search(r'实用性[：:]\s*(\d+)', text)
        
        relevance_score = int(relevance_match.group(1)) if relevance_match else 5
        innovation_impact = int(innovation_match.group(1)) if innovation_match else 5
        practicality = int(practicality_match.group(1)) if practicality_match else 5
        
        total_score = relevance_score + innovation_impact + practicality
        
        return AIEvaluation(
            relevance_score=relevance_score,
            innovation_impact=innovation_impact,
            practicality=practicality,
            total_score=total_score,
            reasoning="从文本中提取的分数（AI响应格式异常）",
            confidence=0.6
        )
    
    def _parse_batch_response(self, response_text: str, article_count: int) -> List[Optional[AIEvaluation]]:
        """解析硅基流动的批量响应"""
        try:
            # 清理响应文本
            cleaned_text = self._clean_batch_response_text(response_text)
            
            # 解析JSON数组
            data_list = json.loads(cleaned_text)
            
            if not isinstance(data_list, list):
                raise ValueError("Response is not a JSON array")
            
            results = []
            for i in range(article_count):
                # 查找对应的评估结果
                evaluation = None
                for data in data_list:
                    if data.get('article_index') == i:
                        evaluation = AIEvaluation(
                            relevance_score=int(data['relevance_score']),
                            innovation_impact=int(data['innovation_impact']),
                            practicality=int(data['practicality']),
                            total_score=int(data['total_score']),
                            reasoning=data.get('reasoning', ''),
                            confidence=float(data.get('confidence', 0.8))
                        )
                        break
                
                results.append(evaluation)
            
            return results
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse SiliconFlow batch AI response: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 返回空结果
            return [None] * article_count
    
    def _clean_batch_response_text(self, text: str) -> str:
        """清理批量响应文本"""
        text = text.strip()
        
        # 移除markdown标记
        if text.startswith('```json'):
            text = text[7:]
        elif text.startswith('```'):
            text = text[3:]
        
        if text.endswith('```'):
            text = text[:-3]
        
        text = text.strip()
        
        # 查找JSON数组的开始和结束
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            text = text[start_idx:end_idx + 1]
        
        return text
    
    def get_provider_info(self) -> dict:
        """获取硅基流动服务商信息"""
        return {
            "name": "硅基流动 (SiliconFlow)",
            "description": "高效能、低成本的多品类AI模型服务",
            "website": "https://siliconflow.cn/",
            "api_docs": "https://docs.siliconflow.cn/",
            "supported_models": [
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2.5-32B-Instruct",
                "Qwen/Qwen2.5-14B-Instruct",
                "deepseek-ai/DeepSeek-V2.5",
                "meta-llama/Meta-Llama-3.1-70B-Instruct",
                "moonshotai/Kimi-K2-Instruct"
            ],
            "features": [
                "兼容OpenAI API",
                "多种开源模型",
                "高性能推理",
                "成本优化"
            ]
        }
