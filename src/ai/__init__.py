"""
AI模块 - 提供AI服务的客户端封装和相关功能
"""

from .client import AIClient
from .cache import AIResultCache
from .prompts import EVALUATION_PROMPT_TEMPLATE, BATCH_EVALUATION_PROMPT

__all__ = [
    'AIClient',
    'AIResultCache', 
    'EVALUATION_PROMPT_TEMPLATE',
    'BATCH_EVALUATION_PROMPT'
]
