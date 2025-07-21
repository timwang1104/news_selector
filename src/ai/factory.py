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
        if agent_config:
            print(f"🔧 使用Agent配置: {agent_config.config_name}, provider={agent_config.api_config.provider}")
    except ImportError as e:
        print(f"⚠️  无法加载Agent配置: {e}")
    except Exception as e:
        print(f"❌ Agent配置加载失败: {e}")

    # 根据Agent配置选择客户端类型
    try:
        if agent_config and agent_config.api_config.provider == "siliconflow":
            print(f"🚀 创建SiliconFlow客户端")
            from .siliconflow_client import SiliconFlowClient
            return SiliconFlowClient(config)
        elif agent_config and agent_config.api_config.provider == "volcengine":
            print(f"🚀 创建Volcengine客户端")
            from .volcengine_client import VolcengineClient
            return VolcengineClient(config)
        else:
            print(f"🚀 创建默认AI客户端")
            from .client import AIClient
            return AIClient(config)
    except Exception as e:
        print(f"❌ AI客户端创建失败: {e}")
        raise
