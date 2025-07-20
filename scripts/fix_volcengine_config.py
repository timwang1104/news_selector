#!/usr/bin/env python3
"""
火山引擎配置修复脚本
帮助用户正确配置火山引擎API
"""
import os
import sys
import json
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_user_input():
    """获取用户输入的配置信息"""
    print("请提供以下火山引擎配置信息:")
    print("(可以从火山引擎控制台获取)")
    print()
    
    # 获取API密钥
    while True:
        api_key = input("1. API密钥 (以sk-开头): ").strip()
        if not api_key:
            print("   API密钥不能为空")
            continue
        if not api_key.startswith('sk-'):
            confirm = input(f"   API密钥格式可能不正确: {api_key[:20]}...\n   是否继续? (y/n): ")
            if confirm.lower() != 'y':
                continue
        break
    
    # 获取Endpoint ID
    while True:
        endpoint_id = input("2. Endpoint ID (以ep-开头): ").strip()
        if not endpoint_id:
            print("   Endpoint ID不能为空")
            continue
        if not endpoint_id.startswith('ep-'):
            confirm = input(f"   Endpoint ID格式可能不正确: {endpoint_id}\n   是否继续? (y/n): ")
            if confirm.lower() != 'y':
                continue
        break
    
    # 获取Base URL (可选)
    base_url = input("3. Base URL (默认: https://ark.cn-beijing.volces.com/api/v3): ").strip()
    if not base_url:
        base_url = "https://ark.cn-beijing.volces.com/api/v3"
    
    return {
        'api_key': api_key,
        'endpoint_id': endpoint_id,
        'base_url': base_url
    }

def update_config_file(config_info):
    """更新配置文件"""
    config_path = "config/agents/火山引擎.json"
    
    try:
        # 读取现有配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            # 创建新配置
            config = {
                "config_name": "火山引擎",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "api_config": {},
                "prompt_config": {},
                "is_active": True,
                "is_default": False
            }
        
        # 更新API配置
        config["api_config"].update({
            "api_key": config_info['api_key'],
            "base_url": config_info['base_url'],
            "model_name": config_info['endpoint_id'],
            "provider": "volcengine"
        })
        
        config["updated_at"] = datetime.now().isoformat()
        
        # 保存配置
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 配置已保存到: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return False

def test_configuration(config_info):
    """测试配置是否有效"""
    print("\n正在测试配置...")
    
    import requests
    
    url = f"{config_info['base_url'].rstrip('/')}/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config_info["api_key"]}'
    }
    
    data = {
        "model": config_info['endpoint_id'],
        "messages": [
            {
                "role": "user",
                "content": "你好，请简单回复确认连接正常"
            }
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print("✅ 配置测试成功!")
            print(f"   模型响应: {content}")
            return True
        else:
            print(f"❌ 配置测试失败 ({response.status_code})")
            print(f"   错误信息: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 配置测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🔧 火山引擎配置修复工具")
    print("=" * 50)
    print()
    
    print("此工具将帮助您正确配置火山引擎API。")
    print("请确保您已经:")
    print("1. 在火山引擎控制台开通了豆包大模型服务")
    print("2. 创建了推理接入点(Endpoint)")
    print("3. 获取了有效的API密钥")
    print()
    
    # 获取用户输入
    config_info = get_user_input()
    print()
    
    # 显示配置摘要
    print("配置摘要:")
    print(f"  API密钥: {config_info['api_key'][:10]}...")
    print(f"  Endpoint ID: {config_info['endpoint_id']}")
    print(f"  Base URL: {config_info['base_url']}")
    print()
    
    # 确认保存
    confirm = input("是否保存此配置? (y/n): ")
    if confirm.lower() != 'y':
        print("配置已取消")
        return
    
    # 更新配置文件
    if update_config_file(config_info):
        print()
        
        # 测试配置
        test_confirm = input("是否测试配置? (y/n): ")
        if test_confirm.lower() == 'y':
            if test_configuration(config_info):
                print("\n🎉 火山引擎配置完成并测试通过!")
                print("\n接下来您可以:")
                print("1. 在GUI中选择'火山引擎'配置")
                print("2. 使用命令行进行AI筛选")
                print("3. 运行 python scripts/check_volcengine_config.py 再次验证")
            else:
                print("\n⚠️  配置已保存但测试失败")
                print("请检查API密钥和Endpoint ID是否正确")
        else:
            print("\n✅ 配置已保存")
            print("您可以稍后运行 python scripts/check_volcengine_config.py 进行测试")

if __name__ == "__main__":
    main()
