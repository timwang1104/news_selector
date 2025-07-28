"""
Moonshot AI客户端适配器
"""
import json
import logging
from typing import List, Optional
from ..models.news import NewsArticle
from ..filters.base import AIEvaluation
from .client import AIClient
from .exceptions import AIClientError

logger = logging.getLogger(__name__)


class MoonshotClient(AIClient):
    """Moonshot AI客户端，继承自基础AI客户端"""
    
    def __init__(self, config):
        super().__init__(config)
        self.provider = "moonshot"
    
    def _build_evaluation_prompt(self, article: NewsArticle) -> str:
        """构建Moonshot优化的评估提示词"""
        # 优先使用Agent配置的提示词
        if self.agent_config and self.agent_config.prompt_config.evaluation_prompt:
            template = self.agent_config.prompt_config.evaluation_prompt
        else:
            # Moonshot优化的默认提示词
            template = """
你是上海市科委的专业顾问，请评估以下科技新闻文章对上海科技发展的相关性和价值。

文章信息：
标题：{title}
摘要：{summary}
内容预览：{content_preview}

请从以下三个维度进行评估（每个维度0-10分）：

1. 政策相关性 (0-10分)：评估文章内容与上海科技政策、产业发展规划的相关程度
2. 创新影响 (0-10分)：评估文章所述技术或事件对科技创新的推动作用
3. 实用性 (0-10分)：评估文章内容的可操作性和对实际工作的指导价值

评估要求：
- 重点关注与上海科技发展相关的内容
- 如果文章主要涉及中国国内企业的商业活动、融资、人事变动等，给予0分
- 如果文章主要涉及中国公司（如华为、中兴、阿里巴巴、腾讯、百度等）的活动、产品或声明，给予0分
- 如果文章主要涉及中国政府、政策或官方声明，给予0分
- 如果文章主要涉及中国大学、高校或教育机构（如清华大学、北京大学、中国科学院大学等）的活动、研究或声明，给予0分
- 完全过滤与中国公司、中国政府、中国大学相关的新闻
- 考虑文章的时效性和权威性
- 评估理由要具体明确，避免泛泛而谈
- 总分为三个维度分数之和（最高30分）
- 充分利用长上下文能力进行深度分析

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
            logger.error(f"Moonshot AI evaluation failed for article {article.id}: {e}")
            fallback_eval = self._fallback_evaluation(article)
            fallback_response = f"Moonshot AI服务异常，使用降级评估策略。错误信息: {str(e)}"
            return fallback_eval, fallback_response

    def _get_content_preview(self, article: NewsArticle, max_length: int = 1000) -> str:
        """获取文章内容预览，Moonshot支持更长的上下文"""
        content = article.content or ""
        if len(content) <= max_length:
            return content
        
        # 对于Moonshot，可以提供更长的内容预览
        return content[:max_length] + "..."

    def _build_batch_prompt(self, articles: List[NewsArticle]) -> str:
        """构建批量评估提示词"""
        # 优先使用Agent配置的批量提示词
        if (self.agent_config and 
            self.agent_config.prompt_config.batch_evaluation_prompt):
            template = self.agent_config.prompt_config.batch_evaluation_prompt
        else:
            # Moonshot优化的默认批量提示词
            template = """
你是上海市科委的专业顾问，请批量评估以下科技新闻文章对上海科技发展的相关性和价值。

评估要求：
- 如果文章主要涉及中国国内企业的商业活动、融资、人事变动等，给予0分
- 如果文章主要涉及中国公司（如华为、中兴、阿里巴巴、腾讯、百度等）的活动、产品或声明，给予0分
- 如果文章主要涉及中国政府、政策或官方声明，给予0分
- 如果文章主要涉及中国大学、高校或教育机构（如清华大学、北京大学、中国科学院大学等）的活动、研究或声明，给予0分
- 完全过滤与中国公司、中国政府、中国大学相关的新闻

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
评估维度和格式要求与单篇评估相同。

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

        # 构建文章信息
        articles_info = []
        for i, article in enumerate(articles):
            article_info = f"""
文章 {i}:
标题: {article.title or '无标题'}
摘要: {article.summary or '无摘要'}
内容预览: {self._get_content_preview(article, 800)}  # 为批量处理适当减少长度
"""
            articles_info.append(article_info.strip())
        
        return template.format(articles_info="\n".join(articles_info))

    def _parse_batch_response(self, response_text: str, articles: List[NewsArticle]) -> List[AIEvaluation]:
        """解析Moonshot批量AI响应"""
        try:
            # 清理响应文本
            response_text = response_text.strip()
            
            # 移除可能的markdown代码块标记
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # 解析JSON数组
            data_list = json.loads(response_text)
            
            if not isinstance(data_list, list):
                raise ValueError("Response is not a JSON array")
            
            article_count = len(articles)
            
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
            logger.error(f"Failed to parse Moonshot batch AI response: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 返回空结果
            return [None] * len(articles)

    def get_provider_info(self) -> dict:
        """获取Moonshot服务商信息"""
        return {
            "name": "Moonshot AI",
            "description": "Moonshot AI平台，提供Kimi大模型服务，支持超长上下文",
            "website": "https://www.moonshot.cn/",
            "api_docs": "https://platform.moonshot.cn/docs",
            "supported_models": [
                "moonshot-v1-8k",
                "moonshot-v1-32k",
                "moonshot-v1-128k"
            ],
            "features": [
                "兼容OpenAI API",
                "超长上下文支持",
                "中文优化",
                "高质量推理"
            ]
        }

    def _call_ai_api(self, prompt: str) -> str:
        """调用Moonshot AI API"""
        try:
            # 使用父类的API调用方法，但可以添加Moonshot特定的优化
            return super()._call_ai_api(prompt)
        except Exception as e:
            logger.error(f"Moonshot API call failed: {e}")
            raise AIClientError(f"Moonshot API调用失败: {str(e)}")

    def _parse_ai_response(self, response_text: str) -> AIEvaluation:
        """解析Moonshot AI响应"""
        try:
            # 清理响应文本
            response_text = response_text.strip()
            
            # 移除可能的markdown代码块标记
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            response_text = response_text.strip()
            
            # 解析JSON
            data = json.loads(response_text)
            
            return AIEvaluation(
                relevance_score=int(data['relevance_score']),
                innovation_impact=int(data['innovation_impact']),
                practicality=int(data['practicality']),
                total_score=int(data['total_score']),
                reasoning=data.get('reasoning', ''),
                confidence=float(data.get('confidence', 0.8))
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Moonshot AI response: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 使用父类的解析方法作为降级
            return super()._parse_ai_response(response_text)
