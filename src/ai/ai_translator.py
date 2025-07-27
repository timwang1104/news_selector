"""AI翻译服务 - 基于大模型的翻译实现"""
import logging
import hashlib
import json
from typing import Dict, Optional, Any, List
from pathlib import Path
from .client import AIClient
from .factory import create_ai_client
from ..config.filter_config import AIFilterConfig
from .exceptions import AIClientError

logger = logging.getLogger(__name__)


class AITranslationCache:
    """AI翻译缓存"""
    
    def __init__(self, cache_file: str = "ai_translation_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载AI翻译缓存失败: {e}")
        return {}
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存AI翻译缓存失败: {e}")
    
    def get(self, text: str, target_lang: str, model_name: str = "") -> Optional[str]:
        """获取缓存的翻译"""
        key = self._make_key(text, target_lang, model_name)
        return self.cache.get(key)
    
    def set(self, text: str, target_lang: str, translation: str, model_name: str = ""):
        """设置缓存"""
        key = self._make_key(text, target_lang, model_name)
        self.cache[key] = translation
        self._save_cache()
    
    def _make_key(self, text: str, target_lang: str, model_name: str = "") -> str:
        """生成缓存键"""
        content = f"{text}:{target_lang}:{model_name}"
        return hashlib.md5(content.encode()).hexdigest()


class AITranslatorService:
    """基于AI大模型的翻译服务"""
    
    def __init__(self, config: AIFilterConfig = None, cache_enabled: bool = True):
        self.config = config or self._get_default_config()
        self.cache_enabled = cache_enabled
        self.cache = AITranslationCache() if cache_enabled else None
        self.ai_client = create_ai_client(self.config)
        
        logger.info(f"已初始化AI翻译服务，使用模型: {self.config.model_name}")
    
    def _get_default_config(self) -> AIFilterConfig:
        """获取默认AI配置"""
        try:
            from ..config.agent_config import agent_config_manager
            agent_config = agent_config_manager.get_current_config()
            if agent_config and agent_config.api_config:
                # 从Agent配置创建AIFilterConfig
                return AIFilterConfig(
                    api_key=agent_config.api_config.api_key,
                    base_url=agent_config.api_config.base_url,
                    model_name=agent_config.api_config.model_name,
                    temperature=0.1,  # 翻译任务使用较低温度
                    max_tokens=2000,
                    timeout=30,
                    retry_times=3,
                    retry_delay=1
                )
        except Exception as e:
            logger.warning(f"无法获取Agent配置: {e}")
        
        # 返回默认配置
        return AIFilterConfig(
            api_key="",
            base_url="https://api.openai.com/v1",
            model_name="gpt-3.5-turbo",
            temperature=0.1,
            max_tokens=2000,
            timeout=30,
            retry_times=3,
            retry_delay=1
        )
    
    def translate(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """翻译文本
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言 (zh=中文, en=英文)
            source_lang: 源语言 (auto=自动检测)
            
        Returns:
            翻译结果
        """
        if not text or not text.strip():
            return text
        
        # 检查缓存
        if self.cache_enabled and self.cache:
            cached = self.cache.get(text, target_lang, self.config.model_name)
            if cached:
                logger.debug(f"使用AI翻译缓存: {text[:50]}...")
                return cached
        
        # 执行AI翻译
        try:
            prompt = self._build_translation_prompt(text, target_lang, source_lang)
            response = self.ai_client._call_ai_api(prompt)
            
            # 解析翻译结果
            result = self._parse_translation_response(response, text)
            
            # 保存到缓存
            if self.cache_enabled and self.cache:
                self.cache.set(text, target_lang, result, self.config.model_name)
            
            logger.debug(f"AI翻译成功: {text[:30]}... -> {result[:30]}...")
            return result
            
        except Exception as e:
            logger.error(f"AI翻译失败: {e}")
            return f"[AI翻译失败] {text}"
    
    def _build_translation_prompt(self, text: str, target_lang: str, source_lang: str) -> str:
        """构建翻译提示词"""
        lang_names = {
            "zh": "中文",
            "en": "英文",
            "auto": "自动检测"
        }
        
        target_name = lang_names.get(target_lang, target_lang)
        source_name = lang_names.get(source_lang, source_lang)
        
        prompt = f"""你是一个专业的翻译专家，特别擅长科技新闻和政策文档的翻译。

请将以下文本翻译成{target_name}：

原文：
{text}

翻译要求：
1. 保持原文的准确性和完整性
2. 使用专业、流畅的表达
3. 保留专业术语的准确性
4. 适合科技新闻的语言风格
5. 只返回翻译结果，不要包含任何解释或说明

翻译结果："""
        
        return prompt
    
    def _parse_translation_response(self, response: str, original_text: str) -> str:
        """解析翻译响应"""
        if not response:
            return f"[翻译失败] {original_text}"
        
        # 清理响应内容
        result = response.strip()
        
        # 移除可能的前缀
        prefixes_to_remove = [
            "翻译结果：",
            "翻译：",
            "Translation:",
            "Result:"
        ]
        
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
                break
        
        # 验证翻译结果
        if not result or result == original_text:
            logger.warning(f"翻译结果无效: {response[:100]}...")
            return f"[翻译异常] {original_text}"
        
        return result
    
    def translate_to_chinese(self, text: str) -> str:
        """翻译为中文"""
        if not text:
            return ""
        
        # 简单的中文检测
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        if chinese_chars / max(len(text), 1) > 0.3:
            # 已经是中文
            return text
        
        return self.translate(text, target_lang="zh")
    
    def translate_to_english(self, text: str) -> str:
        """翻译为英文"""
        if not text:
            return ""
        
        # 简单的英文检测
        english_chars = len([c for c in text if c.isalpha()])
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        
        if english_chars > chinese_chars and english_chars / max(len(text), 1) > 0.5:
            # 已经是英文
            return text
        
        return self.translate(text, target_lang="en")
    
    def detect_and_translate(self, text: str, target_lang: str) -> Dict[str, Any]:
        """检测语言并翻译
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言
            
        Returns:
            包含原文、译文、检测语言等信息的字典
        """
        if not text:
            return {
                "original": "",
                "translated": "",
                "detected_language": "unknown",
                "target_language": target_lang,
                "confidence": 0.0
            }
        
        # 简单的语言检测
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len([c for c in text if c.isalpha()])
        total_chars = len(text)
        
        if chinese_chars / max(total_chars, 1) > 0.3:
            detected_lang = "zh"
            confidence = chinese_chars / max(total_chars, 1)
        elif english_chars / max(total_chars, 1) > 0.5:
            detected_lang = "en"
            confidence = english_chars / max(total_chars, 1)
        else:
            detected_lang = "unknown"
            confidence = 0.5
        
        # 如果检测到的语言与目标语言相同，直接返回
        if detected_lang == target_lang:
            translated = text
        else:
            translated = self.translate(text, target_lang)
        
        return {
            "original": text,
            "translated": translated,
            "detected_language": detected_lang,
            "target_language": target_lang,
            "confidence": confidence
        }
    
    def batch_translate(self, texts: List[str], target_lang: str = "zh") -> List[str]:
        """批量翻译
        
        Args:
            texts: 要翻译的文本列表
            target_lang: 目标语言
            
        Returns:
            翻译结果列表
        """
        if not texts:
            return []
        
        results = []
        for text in texts:
            try:
                result = self.translate(text, target_lang)
                results.append(result)
            except Exception as e:
                logger.error(f"批量翻译失败: {e}")
                results.append(f"[翻译失败] {text}")
        
        return results


class MockAITranslator:
    """模拟AI翻译器 - 用于测试和降级"""
    
    def translate(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """模拟AI翻译"""
        if not text:
            return text
            
        if target_lang == "zh":
            return f"[AI中文翻译] {text}"
        elif target_lang == "en":
            return f"[AI English Translation] {text}"
        else:
            return text
    
    def translate_to_chinese(self, text: str) -> str:
        return self.translate(text, "zh")
    
    def translate_to_english(self, text: str) -> str:
        return self.translate(text, "en")
    
    def detect_and_translate(self, text: str, target_lang: str) -> Dict[str, Any]:
        return {
            "original": text,
            "translated": self.translate(text, target_lang),
            "detected_language": "auto",
            "target_language": target_lang,
            "confidence": 0.5
        }
    
    def batch_translate(self, texts: List[str], target_lang: str = "zh") -> List[str]:
        return [self.translate(text, target_lang) for text in texts]