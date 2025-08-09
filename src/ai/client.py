"""
AI客户端封装
"""
import json
import time
import logging
import requests
from typing import List, Optional, Dict, Any, Tuple
from ..models.news import NewsArticle
from ..config.filter_config import AIFilterConfig
from ..filters.base import AIEvaluation
from .prompts import EVALUATION_PROMPT_TEMPLATE, BATCH_EVALUATION_PROMPT, FALLBACK_REASONING
from .exceptions import AIClientError

logger = logging.getLogger(__name__)


class AIClient:
    """AI服务客户端"""

    def __init__(self, config: AIFilterConfig):
        self.config = config
        self.agent_config = self._get_agent_config()
        self.session = self._create_session()

    def _get_agent_config(self):
        """获取Agent配置（延迟导入避免循环依赖）"""
        try:
            from ..config.agent_config import agent_config_manager
            return agent_config_manager.get_current_config()
        except ImportError:
            return None

    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()

        # 优先使用Agent配置的API密钥
        api_key = self.config.api_key
        if self.agent_config and self.agent_config.api_config:
            api_key = self.agent_config.api_config.api_key or api_key

        session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        })

        # 配置代理设置（如果有Agent配置）
        if self.agent_config and self.agent_config.api_config:
            api_config = self.agent_config.api_config

            # 设置代理
            if api_config.proxy:
                session.proxies = {
                    'http': api_config.proxy,
                    'https': api_config.proxy
                }

            # 设置SSL验证
            session.verify = api_config.verify_ssl

            # 设置自定义请求头
            if api_config.headers:
                session.headers.update(api_config.headers)

        return session
    
    def evaluate_article(self, article: NewsArticle) -> AIEvaluation:
        """评估单篇文章"""
        article_title = article.title[:50] + "..." if len(article.title) > 50 else article.title
        logger.debug(f"开始评估文章: {article_title}")

        try:
            logger.debug(f"构建评估提示词...")
            prompt = self._build_evaluation_prompt(article)

            logger.debug(f"调用AI API进行评估...")
            response = self._call_ai_api(prompt)

            logger.debug(f"解析AI响应...")
            evaluation = self._parse_response(response)

            logger.info(f"文章评估完成: {article_title} - 评分: {evaluation.total_score}/30")
            return evaluation

        except Exception as e:
            logger.error(f"AI evaluation failed for article {article.id}: {e}")
            logger.warning(f"使用降级评估策略: {article_title}")
            return self._fallback_evaluation(article)

    def evaluate_article_with_raw_response(self, article: NewsArticle) -> Tuple[AIEvaluation, str]:
        """评估单篇文章并返回原始响应"""
        article_title = article.title[:50] + "..." if len(article.title) > 50 else article.title
        logger.debug(f"开始评估文章（含原始响应）: {article_title}")

        try:
            logger.debug(f"构建评估提示词...")
            prompt = self._build_evaluation_prompt(article)

            logger.debug(f"调用AI API进行评估...")
            raw_response = self._call_ai_api(prompt)

            logger.debug(f"解析AI响应...")
            evaluation = self._parse_response(raw_response)

            logger.info(f"文章评估完成: {article_title} - 评分: {evaluation.total_score}/30")
            return evaluation, raw_response

        except Exception as e:
            logger.error(f"AI evaluation failed for article {article.id}: {e}")
            logger.warning(f"使用降级评估策略: {article_title}")
            fallback_eval = self._fallback_evaluation(article)
            fallback_response = f"AI服务异常，使用降级评估策略。错误信息: {str(e)}"
            return fallback_eval, fallback_response
    
    def batch_evaluate(self, articles: List[NewsArticle]) -> List[AIEvaluation]:
        """批量评估文章"""
        if not articles:
            return []
        
        # 如果文章数量较少，使用单篇评估
        if len(articles) <= 3:
            return [self.evaluate_article(article) for article in articles]
        
        try:
            prompt = self._build_batch_prompt(articles)
            response = self._call_ai_api(prompt)
            return self._parse_batch_response(response, articles)
        except Exception as e:
            logger.error(f"Batch AI evaluation failed: {e}")
            # 降级到单篇评估
            return [self._fallback_evaluation(article) for article in articles]
    
    def _build_evaluation_prompt(self, article: NewsArticle) -> str:
        """构建单篇评估提示词"""
        # 优先使用Agent配置的提示词
        if self.agent_config and self.agent_config.prompt_config.evaluation_prompt:
            template = self.agent_config.prompt_config.evaluation_prompt
        else:
            template = EVALUATION_PROMPT_TEMPLATE

        return template.format(
            title=article.title or "无标题",
            summary=article.summary or "无摘要",
            content_preview=self._get_content_preview(article)
        )
    
    def _build_batch_prompt(self, articles: List[NewsArticle]) -> str:
        """构建批量评估提示词"""
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
            template = BATCH_EVALUATION_PROMPT

        return template.format(
            articles_info="\n".join(articles_info)
        )
    
    def _get_content_preview(self, article: NewsArticle, max_length: int = 500) -> str:
        """获取文章内容预览"""
        if not article.content:
            return "无内容"
        
        content = article.content.strip()
        if len(content) <= max_length:
            return content
        
        return content[:max_length] + "..."
    
    def _call_ai_api(self, prompt: str) -> str:
        """调用AI API"""
        # 优先使用Agent配置的API设置
        if self.agent_config and self.agent_config.api_config:
            api_config = self.agent_config.api_config
            api_key = api_config.api_key
            base_url = api_config.base_url
            model_name = api_config.model_name
            temperature = api_config.temperature
            max_tokens = api_config.max_tokens
            timeout = api_config.timeout
        else:
            api_key = self.config.api_key
            base_url = self.config.base_url
            model_name = self.config.model_name
            temperature = self.config.temperature
            max_tokens = self.config.max_tokens
            timeout = self.config.timeout

        if not api_key:
            raise AIClientError("AI API key not configured")

        # 构建请求数据
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

        data = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        # 确定API URL
        if base_url:
            url = f"{base_url.rstrip('/')}/chat/completions"
        else:
            url = "https://api.openai.com/v1/chat/completions"
        
        # 发起请求（带重试）
        logger.debug(f"发起AI API请求到: {url}")
        logger.debug(f"使用模型: {model_name}, 温度: {temperature}, 最大令牌: {max_tokens}")

        for attempt in range(self.config.retry_times):
            try:
                logger.debug(f"API请求尝试 {attempt + 1}/{self.config.retry_times}")
                start_time = time.time()

                response = self.session.post(
                    url,
                    json=data,
                    timeout=timeout
                )
                response.raise_for_status()

                api_time = time.time() - start_time
                logger.debug(f"API请求成功，耗时: {api_time:.2f}秒")

                result = response.json()
                response_content = result['choices'][0]['message']['content']
                logger.debug(f"收到AI响应，长度: {len(response_content)} 字符")

                return response_content

            except requests.RequestException as e:
                api_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.warning(f"AI API请求失败 (尝试 {attempt + 1}/{self.config.retry_times}): {e} (耗时: {api_time:.2f}秒)")

                if attempt < self.config.retry_times - 1:
                    logger.debug(f"等待 {self.config.retry_delay} 秒后重试...")
                    time.sleep(self.config.retry_delay)
                else:
                    logger.error(f"AI API请求在 {self.config.retry_times} 次尝试后全部失败")
                    raise AIClientError(f"AI API request failed after {self.config.retry_times} attempts: {e}")
    
    def _parse_response(self, response: str) -> AIEvaluation:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            response = response.strip()
            
            # 查找JSON开始和结束位置
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response[start_idx:end_idx]
            data = json.loads(json_str)
            
            # 验证必需字段
            required_fields = ['relevance_score', 'innovation_impact', 'practicality', 'total_score', 'reasoning', 'confidence']
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            return AIEvaluation(
                relevance_score=int(data['relevance_score']),
                innovation_impact=int(data['innovation_impact']),
                practicality=int(data['practicality']),
                total_score=int(data['total_score']),
                reasoning=str(data['reasoning']),
                confidence=float(data['confidence']),
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
            logger.error(f"Failed to parse AI response: {e}")
            logger.debug(f"Raw response: {response}")
            raise AIClientError(f"Invalid AI response format: {e}")
    
    def _parse_batch_response(self, response: str, articles: List[NewsArticle]) -> List[AIEvaluation]:
        """解析批量AI响应"""
        try:
            # 提取JSON数组
            response = response.strip()
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON array found in response")
            
            json_str = response[start_idx:end_idx]
            data_list = json.loads(json_str)
            
            if len(data_list) != len(articles):
                logger.warning(f"Response count ({len(data_list)}) doesn't match article count ({len(articles)})")
            
            evaluations = []
            for i, data in enumerate(data_list):
                if i >= len(articles):
                    break
                
                evaluation = AIEvaluation(
                    relevance_score=int(data['relevance_score']),
                    innovation_impact=int(data['innovation_impact']),
                    practicality=int(data['practicality']),
                    total_score=int(data['total_score']),
                    reasoning=str(data['reasoning']),
                    confidence=float(data['confidence']),
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
                evaluations.append(evaluation)
            
            # 如果响应数量不足，用降级评估补充
            while len(evaluations) < len(articles):
                evaluations.append(self._fallback_evaluation(articles[len(evaluations)]))
            
            return evaluations
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse batch AI response: {e}")
            raise AIClientError(f"Invalid batch AI response format: {e}")
    
    def _fallback_evaluation(self, article: NewsArticle, base_score: int = 15) -> AIEvaluation:
        """降级评估（当AI服务不可用时）"""
        article_title = article.title if article else "未知文章"
        return AIEvaluation(
            relevance_score=int(base_score * 0.4),
            innovation_impact=int(base_score * 0.3),
            practicality=int(base_score * 0.3),
            total_score=base_score,
            reasoning=FALLBACK_REASONING,
            confidence=0.5,
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
