"""
火山引擎AI客户端适配器
使用官方SDK volcenginesdkarkruntime
"""
import json
import logging
import os
from typing import List, Optional
from ..models.news import NewsArticle
from ..filters.base import AIEvaluation
from ..config.filter_config import AIFilterConfig
from .exceptions import AIClientError

logger = logging.getLogger(__name__)

try:
    import httpx
    from volcenginesdkarkruntime import Ark
    VOLCENGINE_SDK_AVAILABLE = True
except ImportError:
    VOLCENGINE_SDK_AVAILABLE = False
    logger.warning("volcenginesdkarkruntime not installed. Please install it with: pip install volcenginesdkarkruntime")


class VolcengineClient:
    """火山引擎AI客户端，使用官方SDK"""

    def __init__(self, config: AIFilterConfig):
        self.config = config
        self.provider = "volcengine"
        self.agent_config = self._get_agent_config()
        self.client = self._create_ark_client()

    def _get_agent_config(self):
        """获取Agent配置（延迟导入避免循环依赖）"""
        try:
            from ..config.agent_config import agent_config_manager
            return agent_config_manager.get_current_config()
        except ImportError:
            return None

    def _create_ark_client(self):
        """创建火山引擎Ark客户端"""
        if not VOLCENGINE_SDK_AVAILABLE:
            raise AIClientError(
                "volcenginesdkarkruntime SDK not available. "
                "Please install it with: pip install volcenginesdkarkruntime"
            )

        # 获取API配置
        if self.agent_config and self.agent_config.api_config:
            api_config = self.agent_config.api_config
            api_key = api_config.api_key
            timeout = api_config.timeout
        else:
            api_key = self.config.api_key
            timeout = self.config.timeout

        # 检查API密钥
        if not api_key:
            logger.warning("No API key provided for Volcengine client. Will use fallback mode.")
            return None

        # 设置环境变量（SDK会自动读取）
        os.environ['ARK_API_KEY'] = api_key

        # 创建Ark客户端
        try:
            client = Ark(
                api_key=api_key,
                timeout=httpx.Timeout(timeout=timeout)
            )
            return client
        except Exception as e:
            logger.error(f"Failed to create Ark client: {e}")
            logger.warning("Will use fallback mode due to client initialization failure")
            return None

    def evaluate_article(self, article: NewsArticle) -> AIEvaluation:
        """评估单篇文章"""
        try:
            prompt = self._build_evaluation_prompt(article)
            response = self._call_volcengine_api(prompt)
            return self._parse_ai_response(response)
        except Exception as e:
            logger.error(f"AI evaluation failed for article {article.id}: {e}")
            return self._fallback_evaluation(article)

    def evaluate_articles_batch(self, articles: List[NewsArticle]) -> List[Optional[AIEvaluation]]:
        """批量评估文章"""
        try:
            prompt = self._build_batch_evaluation_prompt(articles)
            response = self._call_volcengine_api(prompt)
            return self._parse_batch_ai_response(response, len(articles))
        except Exception as e:
            logger.error(f"Batch AI evaluation failed: {e}")
            # 返回降级评估结果
            return [self._fallback_evaluation(article) for article in articles]

    def _call_volcengine_api(self, prompt: str) -> str:
        """调用火山引擎API，使用官方SDK"""
        # 检查客户端是否可用
        if not self.client:
            raise AIClientError("Volcengine client not available. Please check API key configuration.")

        # 获取配置
        if self.agent_config and self.agent_config.api_config:
            api_config = self.agent_config.api_config
            model_name = api_config.model_name
            temperature = api_config.temperature
            max_tokens = api_config.max_tokens
        else:
            model_name = self.config.model_name
            temperature = self.config.temperature
            max_tokens = self.config.max_tokens

        # 构建消息
        messages = []

        # 添加系统提示词（如果有）
        if (self.agent_config and
            self.agent_config.prompt_config and
            self.agent_config.prompt_config.system_prompt):
            messages.append({
                "role": "system",
                "content": self.agent_config.prompt_config.system_prompt
            })

        messages.append({
            "role": "user",
            "content": prompt
        })

        # 重试机制
        for attempt in range(self.config.retry_times):
            try:
                logger.debug(f"Calling Volcengine API (attempt {attempt + 1})")
                logger.debug(f"Model/Endpoint: {model_name}")

                # 调用API
                completion = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                # 提取响应内容
                if completion.choices and len(completion.choices) > 0:
                    message = completion.choices[0].message

                    # 优先使用reasoning_content，如果没有则使用content
                    content = getattr(message, 'reasoning_content', None) or message.content

                    if content:
                        logger.debug(f"API call successful, response length: {len(content)}")
                        return content
                    else:
                        raise AIClientError("Empty response from Volcengine API")
                else:
                    raise AIClientError("No choices in Volcengine API response")

            except Exception as e:
                logger.warning(f"Volcengine API request failed (attempt {attempt + 1}): {e}")

                if attempt < self.config.retry_times - 1:
                    import time
                    time.sleep(self.config.retry_delay)
                else:
                    raise AIClientError(f"Volcengine API request failed after {self.config.retry_times} attempts: {e}")

    def _fallback_evaluation(self, article: NewsArticle, base_score: int = 15) -> AIEvaluation:
        """降级评估（当AI服务不可用时）"""
        article_title = article.title if article else "未知文章"
        return AIEvaluation(
            relevance_score=int(base_score * 0.4),
            innovation_impact=int(base_score * 0.3),
            practicality=int(base_score * 0.3),
            total_score=base_score,
            reasoning="AI服务暂时不可用，使用默认评分",
            confidence=0.3,
            summary=f"AI服务不可用，无法生成{article_title}的摘要",
            key_insights=["AI服务暂时不可用", "建议稍后重试"],
            highlights=["需要人工审核"],
            tags=["待分析", "AI服务异常"],
            detailed_analysis={
                "政策相关性": "AI服务不可用，无法分析",
                "创新影响": "AI服务不可用，无法分析",
                "实用性": "AI服务不可用，无法分析"
            },
            recommendation_reason="AI服务异常，建议人工审核或稍后重试",
            risk_assessment="AI服务不可用，评估结果可能不准确，建议谨慎使用",
            implementation_suggestions=["等待AI服务恢复", "进行人工审核", "稍后重新评估"]
        )

    def _extract_scores_from_text(self, text: str) -> AIEvaluation:
        """从文本中提取评分（备用解析方法）"""
        import re

        # 尝试提取数字
        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 3:
            try:
                relevance = min(int(numbers[0]), 10)
                innovation = min(int(numbers[1]), 10)
                practicality = min(int(numbers[2]), 10)
                total = relevance + innovation + practicality

                return AIEvaluation(
                    relevance_score=relevance,
                    innovation_impact=innovation,
                    practicality=practicality,
                    total_score=total,
                    reasoning="从响应文本中提取的评分",
                    confidence=0.5,
                    summary="AI服务异常，无法生成摘要",
                    key_insights=["AI服务暂时不可用"],
                    highlights=["需要人工审核"],
                    tags=["待分析"],
                    detailed_analysis={"状态": "AI服务异常，建议人工审核"},
                    recommendation_reason="AI服务异常，建议人工审核",
                    risk_assessment="AI服务不可用，评估结果可能不准确",
                    implementation_suggestions=["等待AI服务恢复后重新评估"]
                )
            except (ValueError, IndexError):
                pass

        # 如果无法提取，返回默认评分
        return self._fallback_evaluation(None)
    
    def _build_evaluation_prompt(self, article: NewsArticle) -> str:
        """构建火山引擎优化的评估提示词"""
        # 优先使用Agent配置的提示词
        if self.agent_config and self.agent_config.prompt_config.evaluation_prompt:
            template = self.agent_config.prompt_config.evaluation_prompt
        else:
            # 火山引擎优化的默认提示词（增强版）
            template = """
你是上海市科委的专业顾问，请深度分析以下科技新闻文章对上海科技发展的相关性和价值。

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

除了评分，还需要提供以下AI智能分析：
- 文章核心内容摘要
- 关键信息和技术要点提取
- 推荐亮点和价值点
- 相关技术标签
- 各维度详细分析
- 推荐理由
- 风险评估
- 实施建议

请严格按照以下JSON格式返回评估结果，不要包含其他内容：
{{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由>",
    "confidence": <置信度，0-1之间的小数>,
    "summary": "<文章核心内容摘要，100字以内>",
    "key_insights": ["<关键信息1>", "<关键信息2>", "<关键信息3>"],
    "highlights": ["<推荐亮点1>", "<推荐亮点2>"],
    "tags": ["<技术标签1>", "<技术标签2>", "<技术标签3>"],
    "detailed_analysis": {{
        "政策相关性": "<详细分析>",
        "创新影响": "<详细分析>",
        "实用性": "<详细分析>"
    }},
    "recommendation_reason": "<为什么推荐这篇文章的核心理由>",
    "risk_assessment": "<潜在风险或注意事项>",
    "implementation_suggestions": ["<实施建议1>", "<实施建议2>"]
}}
"""
        
        return template.format(
            title=article.title,
            summary=article.summary or "无摘要",
            content_preview=article.content[:500] if article.content else "无内容预览"
        )
    
    def _build_batch_evaluation_prompt(self, articles: List[NewsArticle]) -> str:
        """构建火山引擎优化的批量评估提示词"""
        # 优先使用Agent配置的批量提示词
        if (self.agent_config and 
            self.agent_config.prompt_config and 
            self.agent_config.prompt_config.batch_evaluation_prompt):
            template = self.agent_config.prompt_config.batch_evaluation_prompt
        else:
            # 火山引擎优化的默认批量提示词（增强版）
            template = """
你是上海市科委的专业顾问，请深度分析以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，包含评分和AI智能分析，返回JSON数组格式的结果。

请严格按照以下JSON数组格式返回结果，不要包含其他内容：
[
    {{
        "article_index": 0,
        "relevance_score": <分数>,
        "innovation_impact": <分数>,
        "practicality": <分数>,
        "total_score": <总分>,
        "reasoning": "<评估理由>",
        "confidence": <置信度>,
        "summary": "<文章摘要>",
        "key_insights": ["<关键信息1>", "<关键信息2>"],
        "highlights": ["<亮点1>", "<亮点2>"],
        "tags": ["<标签1>", "<标签2>"],
        "detailed_analysis": {{"政策相关性": "<分析>", "创新影响": "<分析>", "实用性": "<分析>"}},
        "recommendation_reason": "<推荐理由>",
        "risk_assessment": "<风险评估>",
        "implementation_suggestions": ["<建议1>", "<建议2>"]
    }},
    ...
]

注意：请确保返回的是有效的JSON数组格式，不要包含markdown代码块标记。
"""
        
        # 构建文章信息列表
        articles_info = []
        for i, article in enumerate(articles):
            article_info = f"""
文章 {i}:
标题: {article.title}
摘要: {article.summary or "无摘要"}
内容预览: {article.content[:300] if article.content else "无内容预览"}
"""
            articles_info.append(article_info)
        
        return template.format(
            articles_info="\n".join(articles_info)
        )
    
    def _parse_ai_response(self, response_text: str) -> AIEvaluation:
        """解析火山引擎的AI响应，增强JSON解析"""
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
                confidence=float(data.get('confidence', 0.8)),
                # AI AGENT增强信息（向后兼容）
                summary=data.get('summary', ''),
                key_insights=data.get('key_insights', []),
                highlights=data.get('highlights', []),
                tags=data.get('tags', []),
                detailed_analysis=data.get('detailed_analysis', {}),
                recommendation_reason=data.get('recommendation_reason', ''),
                risk_assessment=data.get('risk_assessment', ''),
                implementation_suggestions=data.get('implementation_suggestions', [])
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Volcengine AI response: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 尝试从响应中提取数字
            try:
                return self._extract_scores_from_text(response_text)
            except Exception:
                # 返回默认评估
                return AIEvaluation(
                    relevance_score=5,
                    innovation_impact=5,
                    practicality=5,
                    total_score=15,
                    reasoning="AI响应解析失败，使用默认评分",
                    confidence=0.3
                )
    
    def _clean_response_text(self, text: str) -> str:
        """清理火山引擎响应文本，移除markdown标记和多余内容"""
        # 移除markdown代码块标记
        text = text.replace('```json', '').replace('```', '')
        
        # 移除可能的前后缀说明文字
        lines = text.strip().split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                in_json = True
            if in_json:
                json_lines.append(line)
            if line.endswith('}') or line.endswith(']'):
                break
        
        return '\n'.join(json_lines)
    
    def _parse_batch_ai_response(self, response_text: str, article_count: int) -> List[Optional[AIEvaluation]]:
        """解析火山引擎的批量AI响应"""
        try:
            # 清理响应文本
            cleaned_text = self._clean_response_text(response_text)
            
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
                            confidence=float(data.get('confidence', 0.8)),
                            # AI AGENT增强信息（向后兼容）
                            summary=data.get('summary', ''),
                            key_insights=data.get('key_insights', []),
                            highlights=data.get('highlights', []),
                            tags=data.get('tags', []),
                            detailed_analysis=data.get('detailed_analysis', {}),
                            recommendation_reason=data.get('recommendation_reason', ''),
                            risk_assessment=data.get('risk_assessment', ''),
                            implementation_suggestions=data.get('implementation_suggestions', [])
                        )
                        break
                
                results.append(evaluation)
            
            return results
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse Volcengine batch AI response: {e}")
            logger.error(f"Response text: {response_text}")
            
            # 返回空结果
            return [None] * article_count
