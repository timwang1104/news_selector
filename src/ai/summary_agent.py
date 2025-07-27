"""AI摘要生成服务 - 专门用于生成高质量的中文摘要"""
import logging
from typing import Dict, Any, Optional
from .factory import create_ai_client
from ..config.agent_config import agent_config_manager

logger = logging.getLogger(__name__)


class AISummaryAgent:
    """AI摘要生成代理
    
    专门用于生成高质量的中文摘要，相比简单翻译，提供更好的摘要质量
    """
    
    def __init__(self, config_name: str = "default"):
        """
        初始化摘要生成代理
        
        Args:
            config_name: Agent配置名称
        """
        self.config_name = config_name
        self.ai_client = None
        self.config = None
        self._initialize_client()
    
    def _initialize_client(self):
        """初始化AI客户端"""
        try:
            # 获取Agent配置，参考翻译agent的逻辑
            config = self._get_default_config()
            
            # 使用工厂函数创建AI客户端
            self.ai_client = create_ai_client(config)
            logger.info(f"摘要生成代理初始化成功，使用模型: {config.model_name}")
                
        except Exception as e:
            logger.error(f"摘要生成代理初始化失败: {e}")
            self.ai_client = None
    
    def _get_default_config(self):
        """获取默认AI配置，参考翻译agent的实现"""
        try:
            from ..config.agent_config import agent_config_manager
            agent_config = agent_config_manager.get_current_config()
            if agent_config and agent_config.api_config:
                # 从Agent配置创建AIFilterConfig
                from ..config.filter_config import AIFilterConfig
                return AIFilterConfig(
                    api_key=agent_config.api_config.api_key,
                    base_url=agent_config.api_config.base_url,
                    model_name=agent_config.api_config.model_name,
                    temperature=0.3,  # 摘要任务使用适中温度
                    max_tokens=2000,
                    timeout=30,
                    retry_times=3,
                    retry_delay=1
                )
        except Exception as e:
            logger.warning(f"无法获取Agent配置: {e}")
        
        # 返回默认配置
        from ..config.filter_config import AIFilterConfig
        return AIFilterConfig(
            api_key="",
            base_url="https://api.openai.com/v1",
            model_name="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=2000,
            timeout=30,
            retry_times=3,
            retry_delay=1
        )
    
    def generate_chinese_summary(self, title: str, content: str, original_summary: str = "") -> str:
        """生成中文摘要
        
        Args:
            title: 文章标题
            content: 文章内容
            original_summary: 原始摘要（可选）
            
        Returns:
            生成的中文摘要
        """
        if not self.ai_client:
            logger.error("AI客户端未初始化")
            return self._fallback_summary(title, content, original_summary)
        
        try:
            prompt = self._build_summary_prompt(title, content, original_summary)
            response = self.ai_client._call_ai_api(prompt)
            
            # 解析和清理摘要结果
            summary = self._parse_summary_response(response)
            
            logger.debug(f"摘要生成成功: {title[:30]}... -> {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            return self._fallback_summary(title, content, original_summary)
    
    def _build_summary_prompt(self, title: str, content: str, original_summary: str = "") -> str:
        """构建摘要生成提示词"""
        prompt = """你是一个专业的新闻摘要生成专家，特别擅长科技新闻和政策文档的摘要写作。

请根据以下文章信息，生成一个高质量的中文摘要：

文章标题：
{title}

文章内容：
{content}
""".format(title=title, content=content[:3000])  # 限制内容长度避免token过多
        
        if original_summary:
            prompt += f"\n原始摘要（参考）：\n{original_summary}\n"
        
        prompt += """\n摘要要求：
1. 用中文撰写，语言流畅自然
2. 长度控制在100-200字之间
3. 准确概括文章核心内容和要点
4. 突出关键信息和亮点
5. 适合科技新闻的专业表达
6. 避免冗余和无关信息
7. 保持客观中性的语调
8. 只返回摘要内容，不要包含任何解释或说明

中文摘要："""
        
        return prompt
    
    def _parse_summary_response(self, response: str) -> str:
        """解析摘要响应"""
        if not response:
            return "摘要生成失败"
        
        # 清理响应内容
        summary = response.strip()
        
        # 移除可能的前缀
        prefixes_to_remove = [
            "中文摘要：",
            "摘要：",
            "Summary:",
            "概要：",
            "内容摘要："
        ]
        
        for prefix in prefixes_to_remove:
            if summary.startswith(prefix):
                summary = summary[len(prefix):].strip()
                break
        
        # 移除可能的引号
        if summary.startswith('"') and summary.endswith('"'):
            summary = summary[1:-1].strip()
        
        # 验证摘要长度和质量
        if len(summary) < 20:
            logger.warning(f"生成的摘要过短: {summary}")
            return f"摘要生成异常: {summary}"
        
        if len(summary) > 500:
            logger.warning(f"生成的摘要过长，进行截断: {len(summary)}字符")
            summary = summary[:300] + "..."
        
        return summary
    
    def _fallback_summary(self, title: str, content: str, original_summary: str = "") -> str:
        """降级摘要生成"""
        if original_summary:
            # 如果有原始摘要，尝试简单处理
            if self._is_chinese(original_summary):
                return original_summary
            else:
                # 如果原始摘要是英文，返回标记
                return f"[原文摘要] {original_summary[:150]}..."
        
        # 如果没有原始摘要，从标题和内容生成简单摘要
        if content:
            # 取内容前200字符作为摘要
            simple_summary = content[:200].strip()
            if simple_summary:
                return f"{simple_summary}..."
        
        # 最后降级到标题
        return f"基于标题: {title}"
    
    def _is_chinese(self, text: str) -> bool:
        """判断文本是否主要是中文"""
        if not text:
            return False
        
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        total_chars = len(text.replace(' ', ''))
        
        return chinese_chars / max(total_chars, 1) > 0.3
    
    def enhance_existing_summary(self, existing_summary: str, title: str, content: str = "") -> str:
        """增强现有摘要
        
        Args:
            existing_summary: 现有摘要
            title: 文章标题
            content: 文章内容（可选）
            
        Returns:
            增强后的摘要
        """
        if not self.ai_client:
            return existing_summary
        
        try:
            prompt = self._build_enhancement_prompt(existing_summary, title, content)
            response = self.ai_client._call_ai_api(prompt)
            
            enhanced_summary = self._parse_summary_response(response)
            
            # 如果增强失败，返回原摘要
            if "摘要生成失败" in enhanced_summary or "摘要生成异常" in enhanced_summary:
                return existing_summary
            
            return enhanced_summary
            
        except Exception as e:
            logger.error(f"摘要增强失败: {e}")
            return existing_summary
    
    def _build_enhancement_prompt(self, existing_summary: str, title: str, content: str = "") -> str:
        """构建摘要增强提示词"""
        prompt = f"""你是一个专业的新闻摘要优化专家。请优化以下摘要，使其更加准确、流畅和专业。

文章标题：
{title}

现有摘要：
{existing_summary}
"""
        
        if content:
            prompt += f"\n文章内容（参考）：\n{content[:1000]}\n"
        
        prompt += """\n优化要求：
1. 保持摘要的核心信息不变
2. 改善语言表达，使其更加流畅自然
3. 确保专业术语的准确性
4. 长度控制在100-200字之间
5. 适合科技新闻的表达风格
6. 只返回优化后的摘要，不要解释

优化后的摘要："""
        
        return prompt


class MockSummaryAgent:
    """模拟摘要生成代理 - 用于测试和降级"""
    
    def generate_chinese_summary(self, title: str, content: str, original_summary: str = "") -> str:
        """生成模拟中文摘要"""
        if original_summary:
            return f"[模拟摘要] {original_summary[:100]}..."
        elif content:
            return f"[模拟摘要] 基于内容: {content[:100]}..."
        else:
            return f"[模拟摘要] 基于标题: {title}"
    
    def enhance_existing_summary(self, existing_summary: str, title: str, content: str = "") -> str:
        """模拟摘要增强"""
        return f"[增强摘要] {existing_summary}"


# 全局摘要代理实例
_summary_agent = None


def get_summary_agent(config_name: str = "default") -> AISummaryAgent:
    """获取摘要生成代理实例
    
    Args:
        config_name: Agent配置名称
        
    Returns:
        摘要生成代理实例
    """
    global _summary_agent
    
    if _summary_agent is None:
        try:
            _summary_agent = AISummaryAgent(config_name)
        except Exception as e:
            logger.error(f"创建摘要代理失败: {e}")
            _summary_agent = MockSummaryAgent()
    
    return _summary_agent