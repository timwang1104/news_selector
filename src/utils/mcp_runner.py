"""MCP运行工具 - 用于调用MCP服务器"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def run_mcp_tool(server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
    """
    运行MCP工具
    
    Args:
        server_name: MCP服务器名称
        tool_name: 工具名称
        args: 工具参数
        
    Returns:
        工具执行结果
    """
    try:
        # 这里应该调用实际的MCP客户端
        # 由于我们没有具体的MCP客户端实现，这里提供一个接口
        
        # 检查是否有可用的MCP客户端
        mcp_client = get_mcp_client()
        if mcp_client is None:
            raise ImportError("MCP客户端不可用")
        
        # 调用MCP工具
        result = mcp_client.call_tool(server_name, tool_name, args)
        
        logger.info(f"MCP工具调用成功: {server_name}.{tool_name}")
        return result
        
    except Exception as e:
        logger.error(f"MCP工具调用失败: {server_name}.{tool_name}, 错误: {e}")
        raise


def get_mcp_client():
    """
    获取MCP客户端实例
    
    Returns:
        MCP客户端实例或None
    """
    try:
        # 尝试导入并创建MCP客户端
        # 这里需要根据实际的MCP客户端库进行实现
        
        # 示例：如果使用mcp库
        # from mcp import Client
        # return Client()
        
        # 示例：如果使用自定义的MCP客户端
        from ..ai.mcp_client import get_global_mcp_client
        return get_global_mcp_client()
        
    except ImportError:
        logger.warning("MCP客户端库不可用")
        return None
    except Exception as e:
        logger.error(f"创建MCP客户端失败: {e}")
        return None


class MCPToolRunner:
    """
    MCP工具运行器类
    """
    
    def __init__(self, client=None):
        self.client = client or get_mcp_client()
    
    def run(self, server_name: str, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        运行MCP工具
        
        Args:
            server_name: MCP服务器名称
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        if self.client is None:
            raise RuntimeError("MCP客户端不可用")
        
        return self.client.call_tool(server_name, tool_name, args)
    
    def is_available(self) -> bool:
        """
        检查MCP客户端是否可用
        
        Returns:
            是否可用
        """
        return self.client is not None


# 全局MCP工具运行器实例
_mcp_runner = None


def get_mcp_runner() -> MCPToolRunner:
    """
    获取全局MCP工具运行器实例
    
    Returns:
        MCP工具运行器实例
    """
    global _mcp_runner
    if _mcp_runner is None:
        _mcp_runner = MCPToolRunner()
    return _mcp_runner


def set_mcp_runner(runner: MCPToolRunner):
    """
    设置全局MCP工具运行器实例
    
    Args:
        runner: MCP工具运行器实例
    """
    global _mcp_runner
    _mcp_runner = runner