"""
翻译服务 - 支持多种翻译API
"""
import logging
import hashlib
import json
import time
from typing import Dict, Optional, Any
from pathlib import Path
import requests

logger = logging.getLogger(__name__)


class TranslationCache:
    """翻译缓存"""
    
    def __init__(self, cache_file: str = "translation_cache.json"):
        self.cache_file = Path(cache_file)
        self.cache = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """加载缓存"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"加载翻译缓存失败: {e}")
        return {}
    
    def _save_cache(self):
        """保存缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存翻译缓存失败: {e}")
    
    def get(self, text: str, target_lang: str) -> Optional[str]:
        """获取缓存的翻译"""
        key = self._make_key(text, target_lang)
        return self.cache.get(key)
    
    def set(self, text: str, target_lang: str, translation: str):
        """设置缓存"""
        key = self._make_key(text, target_lang)
        self.cache[key] = translation
        self._save_cache()
    
    def _make_key(self, text: str, target_lang: str) -> str:
        """生成缓存键"""
        content = f"{text}:{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()


class BaseTranslator:
    """翻译器基类"""
    
    def __init__(self, cache_enabled: bool = True):
        self.cache_enabled = cache_enabled
        self.cache = TranslationCache() if cache_enabled else None
    
    def translate(self, text: str, target_lang: str = "zh", source_lang: str = "auto") -> str:
        """
        翻译文本
        
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
            cached = self.cache.get(text, target_lang)
            if cached:
                logger.debug(f"使用缓存翻译: {text[:50]}...")
                return cached
        
        # 执行翻译
        try:
            result = self._do_translate(text, target_lang, source_lang)
            
            # 保存到缓存
            if self.cache_enabled and self.cache and result:
                self.cache.set(text, target_lang, result)
            
            return result
            
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            return f"[翻译失败] {text}"
    
    def _do_translate(self, text: str, target_lang: str, source_lang: str) -> str:
        """执行实际翻译 - 子类实现"""
        raise NotImplementedError


class BaiduTranslator(BaseTranslator):
    """百度翻译"""
    
    def __init__(self, app_id: str, secret_key: str, **kwargs):
        super().__init__(**kwargs)
        self.app_id = app_id
        self.secret_key = secret_key
        self.api_url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    
    def _do_translate(self, text: str, target_lang: str, source_lang: str) -> str:
        """百度翻译实现"""
        # 语言代码映射
        lang_map = {
            "zh": "zh",
            "en": "en",
            "auto": "auto"
        }
        
        from_lang = lang_map.get(source_lang, "auto")
        to_lang = lang_map.get(target_lang, "zh")
        
        # 生成签名
        salt = str(int(time.time()))
        sign_str = f"{self.app_id}{text}{salt}{self.secret_key}"
        sign = hashlib.md5(sign_str.encode()).hexdigest()
        
        # 请求参数
        params = {
            'q': text,
            'from': from_lang,
            'to': to_lang,
            'appid': self.app_id,
            'salt': salt,
            'sign': sign
        }
        
        # 发送请求
        response = requests.get(self.api_url, params=params, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if 'error_code' in result:
            raise Exception(f"百度翻译API错误: {result.get('error_msg', '未知错误')}")
        
        if 'trans_result' in result and result['trans_result']:
            return result['trans_result'][0]['dst']
        
        raise Exception("翻译结果为空")


class MockTranslator(BaseTranslator):
    """模拟翻译器 - 用于测试"""
    
    def _do_translate(self, text: str, target_lang: str, source_lang: str) -> str:
        """模拟翻译"""
        if target_lang == "zh":
            return f"[中文翻译] {text}"
        elif target_lang == "en":
            return f"[English Translation] {text}"
        else:
            return text


class TranslationService:
    """翻译服务"""
    
    def __init__(self, translator: BaseTranslator = None):
        """
        初始化翻译服务
        
        Args:
            translator: 翻译器实例，如果为None则使用模拟翻译器
        """
        self.translator = translator or MockTranslator()
    
    def translate_to_chinese(self, text: str) -> str:
        """翻译为中文"""
        if not text:
            return ""
        
        # 简单的中文检测
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        if chinese_chars / max(len(text), 1) > 0.3:
            # 已经是中文
            return text
        
        return self.translator.translate(text, target_lang="zh")
    
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
        
        return self.translator.translate(text, target_lang="en")
    
    def detect_and_translate(self, text: str, target_lang: str) -> Dict[str, Any]:
        """
        检测语言并翻译
        
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
                "detected_lang": "unknown",
                "target_lang": target_lang
            }
        
        # 简单的语言检测
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        english_chars = len([c for c in text if c.isalpha()])
        total_chars = len(text.replace(' ', ''))
        
        if total_chars == 0:
            detected_lang = "unknown"
        elif chinese_chars / total_chars > 0.3:
            detected_lang = "zh"
        elif english_chars / total_chars > 0.5:
            detected_lang = "en"
        else:
            detected_lang = "mixed"
        
        # 如果检测语言与目标语言相同，不需要翻译
        if detected_lang == target_lang:
            translated = text
        else:
            translated = self.translator.translate(text, target_lang=target_lang)
        
        return {
            "original": text,
            "translated": translated,
            "detected_lang": detected_lang,
            "target_lang": target_lang,
            "needs_translation": detected_lang != target_lang
        }


# 全局翻译服务实例
_translation_service = None


def get_translation_service() -> TranslationService:
    """获取翻译服务实例"""
    global _translation_service
    if _translation_service is None:
        # 尝试从环境变量获取百度翻译配置
        import os
        baidu_app_id = os.getenv("BAIDU_TRANSLATE_APP_ID")
        baidu_secret = os.getenv("BAIDU_TRANSLATE_SECRET")
        
        if baidu_app_id and baidu_secret:
            translator = BaiduTranslator(baidu_app_id, baidu_secret)
            logger.info("使用百度翻译服务")
        else:
            translator = MockTranslator()
            logger.info("使用模拟翻译服务")
        
        _translation_service = TranslationService(translator)
    
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
