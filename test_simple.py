#!/usr/bin/env python3
"""
简单测试脚本
"""

from src.api.auth import InoreaderAuth

def test_basic():
    """测试基本功能"""
    print("=== 基本功能测试 ===")
    
    try:
        auth = InoreaderAuth()
        print("✅ 认证模块初始化成功")
        
        if auth.is_authenticated():
            print("✅ 用户已登录")
        else:
            print("ℹ️  用户未登录")
        
        # 测试URL生成
        test_url = auth.get_auth_url("http://localhost:8080")
        print(f"✅ 认证URL生成成功: {test_url[:50]}...")
        
        print("\n所有基本功能正常！")
        print("如需测试完整登录流程，请运行: python test_auth.py")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_basic()
