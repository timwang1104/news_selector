"""翻译服务 - 基于AI大模型的翻译实现"""
import logging
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)


# AI翻译服务导入
try:
    from ..ai.ai_translator import AITranslatorService, MockAITranslator
    from ..ai.summary_agent import get_summary_agent
except ImportError:
    AITranslatorService = None
    MockAITranslator = None


# 原有的翻译器类已被AI翻译服务替代


class TranslationService:
    """AI翻译服务"""
    
    def __init__(self, translator=None):
        """
        初始化翻译服务
        
        Args:
            translator: 翻译器实例，如果为None则自动选择AI翻译器
        """
        if translator is None:
            try:
                if AITranslatorService is not None:
                    self.translator = AITranslatorService()
                    logger.info("使用AI大模型翻译服务")
                else:
                    self.translator = MockAITranslator()
                    logger.warning("AI翻译服务不可用，使用模拟翻译器")
            except Exception as e:
                logger.error(f"初始化AI翻译服务失败: {e}")
                if MockAITranslator is not None:
                    self.translator = MockAITranslator()
                    logger.warning("使用模拟AI翻译器")
                else:
                    raise ImportError("无法初始化任何翻译服务")
        else:
            self.translator = translator
    
    def translate_to_chinese(self, text: str) -> str:
        """翻译为中文"""
        return self.translator.translate_to_chinese(text)
    
    def translate_to_english(self, text: str) -> str:
        """翻译为英文"""
        return self.translator.translate_to_english(text)
    
    def generate_chinese_summary(self, title: str, content: str, original_summary: str = "") -> str:
        """生成高质量的中文摘要
        
        Args:
            title: 文章标题
            content: 文章内容
            original_summary: 原始摘要（可选）
            
        Returns:
            生成的中文摘要
        """
        try:
            summary_agent = get_summary_agent()
            return summary_agent.generate_chinese_summary(title, content, original_summary)
        except Exception as e:
            logger.error(f"摘要生成失败: {e}")
            # 降级到翻译
            if original_summary:
                return self.translate_to_chinese(original_summary)
            else:
                return f"基于标题: {title}"
    
    def enhance_summary(self, existing_summary: str, title: str, content: str = "") -> str:
        """增强现有摘要质量
        
        Args:
            existing_summary: 现有摘要
            title: 文章标题
            content: 文章内容（可选）
            
        Returns:
            增强后的摘要
        """
        try:
            summary_agent = get_summary_agent()
            return summary_agent.enhance_existing_summary(existing_summary, title, content)
        except Exception as e:
            logger.error(f"摘要增强失败: {e}")
            return existing_summary
    
    def detect_and_translate(self, text: str, target_lang: str) -> Dict[str, Any]:
        """
        检测语言并翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            
        Returns:
            包含原文、译文、检测语言等信息的字典
        """
        return self.translator.detect_and_translate(text, target_lang)


# 全局翻译服务实例
_translation_service = None


def get_translation_service() -> TranslationService:
    """获取翻译服务实例"""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def set_translation_service(service: TranslationService):
    """设置翻译服务实例"""
    global _translation_service
    _translation_service = service


if __name__ == "__main__":
    # 测试翻译服务
    service = get_translation_service()
    
    # 测试中文翻译
    chinese_result = service.translate_to_chinese("Artificial Intelligence Technology Report")
    print(f"英文->中文: {chinese_result}")
    
    # 测试英文翻译
    english_result = service.translate_to_english("人工智能技术发展报告")
    print(f"中文->英文: {english_result}")
    
    # 测试检测和翻译
    detect_result = service.detect_and_translate("AI技术发展很快", "en")
    print(f"检测和翻译: {detect_result}")
