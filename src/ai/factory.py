"""
AI客户端工厂模块
"""
from ..config.filter_config import AIFilterConfig


def create_ai_client(config: AIFilterConfig):
    """AI客户端工厂函数"""
    # 获取Agent配置
    agent_config = None
    try:
        from ..config.agent_config import agent_config_manager
        agent_config = agent_config_manager.get_current_config()
    except ImportError:
        pass
    
    # 根据Agent配置选择客户端类型
    if agent_config and agent_config.api_config.provider == "siliconflow":
        from .siliconflow_client import SiliconFlowClient
        return SiliconFlowClient(config)
    elif agent_config and agent_config.api_config.provider == "volcengine":
        from .volcengine_client import VolcengineClient
        return VolcengineClient(config)
    else:
        from .client import AIClient
        return AIClient(config)
