#!/usr/bin/env python3
"""
清理重复的硅基流动配置脚本
"""
import os
from pathlib import Path
from src.config.agent_config import agent_config_manager


def cleanup_duplicate_configs():
    """清理重复的硅基流动配置"""
    print("🧹 清理重复的硅基流动配置...")
    
    try:
        # 获取当前配置列表
        config_list = agent_config_manager.get_config_list()
        print(f"当前配置列表: {config_list}")
        
        # 查找需要清理的配置
        configs_to_remove = []
        
        # 查找旧的硅基流动配置
        for config_name in config_list:
            if config_name in ["硅基流动-Qwen2.5", "硅基流动-Kimi"]:
                configs_to_remove.append(config_name)
        
        if configs_to_remove:
            print(f"找到需要清理的配置: {configs_to_remove}")
            
            # 备份当前配置名称
            current_config_name = agent_config_manager.current_config_name
            
            # 删除重复配置
            for config_name in configs_to_remove:
                try:
                    agent_config_manager.delete_config(config_name)
                    print(f"✅ 已删除配置: {config_name}")
                except Exception as e:
                    print(f"❌ 删除配置 {config_name} 失败: {e}")
            
            # 确保有硅基流动统一配置
            updated_list = agent_config_manager.get_config_list()
            if "硅基流动" not in updated_list:
                print("🔧 创建统一的硅基流动配置...")
                agent_config_manager.create_siliconflow_preset()
                print("✅ 已创建统一的硅基流动配置")
            
            # 如果当前配置被删除了，切换到合适的配置
            if current_config_name in configs_to_remove:
                if "硅基流动" in agent_config_manager.get_config_list():
                    agent_config_manager.set_current_config("硅基流动")
                    print("✅ 已切换到统一的硅基流动配置")
                elif "默认配置" in agent_config_manager.get_config_list():
                    agent_config_manager.set_current_config("默认配置")
                    print("✅ 已切换到默认配置")
        else:
            print("✅ 没有找到需要清理的重复配置")
        
        # 显示清理后的配置列表
        final_list = agent_config_manager.get_config_list()
        print(f"清理后的配置列表: {final_list}")
        
        # 显示当前配置
        current_config = agent_config_manager.get_current_config()
        if current_config:
            print(f"当前配置: {current_config.config_name}")
        
        print("✅ 配置清理完成")
        
    except Exception as e:
        print(f"❌ 配置清理失败: {e}")


def cleanup_config_files():
    """清理配置文件"""
    print("📁 清理配置文件...")
    
    try:
        config_dir = Path("config/agents")
        if not config_dir.exists():
            print("⚠️  配置目录不存在")
            return
        
        # 查找需要删除的配置文件
        files_to_remove = []
        for config_file in config_dir.glob("*.json"):
            if config_file.stem in ["硅基流动-Qwen2.5", "硅基流动-Kimi"]:
                files_to_remove.append(config_file)
        
        if files_to_remove:
            print(f"找到需要删除的配置文件: {[f.name for f in files_to_remove]}")
            
            for config_file in files_to_remove:
                try:
                    config_file.unlink()
                    print(f"✅ 已删除文件: {config_file.name}")
                except Exception as e:
                    print(f"❌ 删除文件 {config_file.name} 失败: {e}")
        else:
            print("✅ 没有找到需要删除的配置文件")
        
        print("✅ 配置文件清理完成")
        
    except Exception as e:
        print(f"❌ 配置文件清理失败: {e}")


def verify_unified_config():
    """验证统一配置"""
    print("🔍 验证统一配置...")
    
    try:
        # 检查硅基流动配置
        config = agent_config_manager.load_config("硅基流动")
        if config:
            print("✅ 找到统一的硅基流动配置")
            print(f"   配置名称: {config.config_name}")
            print(f"   API名称: {config.api_config.name}")
            print(f"   描述: {config.api_config.description}")
            print(f"   默认模型: {config.api_config.model_name}")
            print(f"   Max Tokens: {config.api_config.max_tokens}")
            print(f"   Timeout: {config.api_config.timeout}")
            print(f"   提示词名称: {config.prompt_config.name}")
            print(f"   提示词描述: {config.prompt_config.description}")
        else:
            print("❌ 未找到统一的硅基流动配置")
        
        # 检查配置列表
        config_list = agent_config_manager.get_config_list()
        print(f"最终配置列表: {config_list}")
        
        # 检查是否还有重复配置
        duplicate_configs = [name for name in config_list if name in ["硅基流动-Qwen2.5", "硅基流动-Kimi"]]
        if duplicate_configs:
            print(f"⚠️  仍存在重复配置: {duplicate_configs}")
        else:
            print("✅ 没有重复配置")
        
        print("✅ 配置验证完成")
        
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")


def show_usage_guide():
    """显示使用指南"""
    print("📋 统一硅基流动配置使用指南:")
    print("-" * 50)
    print("1. 配置名称: '硅基流动'")
    print("2. 支持的模型:")
    print("   - Qwen/Qwen2.5-72B-Instruct (默认)")
    print("   - moonshotai/Kimi-K2-Instruct")
    print("   - deepseek-ai/DeepSeek-V2.5")
    print("   - meta-llama/Meta-Llama-3.1-70B-Instruct")
    print("   - 其他硅基流动支持的模型")
    print()
    print("3. GUI使用方法:")
    print("   - 选择服务提供商: siliconflow")
    print("   - 在模型下拉菜单中选择具体模型")
    print("   - 或使用快速选择按钮切换常用模型")
    print("   - 点击'加载硅基流动预设'快速配置")
    print()
    print("4. 快速模型切换:")
    print("   - Qwen2.5-72B: 平衡性能，适合通用任务")
    print("   - Kimi: 长文档分析，中文优化")
    print("   - DeepSeek: 推理能力强")
    print("   - Llama3.1-70B: 英文内容优秀")


def main():
    """主函数"""
    print("🎯 硅基流动配置统一化")
    print("=" * 60)
    
    # 清理重复配置
    cleanup_duplicate_configs()
    print()
    
    # 清理配置文件
    cleanup_config_files()
    print()
    
    # 验证统一配置
    verify_unified_config()
    print()
    
    # 显示使用指南
    show_usage_guide()
    print()
    
    print("✅ 硅基流动配置统一化完成！")
    print("\n💡 下一步:")
    print("- 重新启动GUI应用")
    print("- 在AI Agent配置中查看统一的'硅基流动'配置")
    print("- 使用快速模型选择按钮切换不同模型")
    print("- 根据任务需求选择最适合的模型")


if __name__ == "__main__":
    main()
