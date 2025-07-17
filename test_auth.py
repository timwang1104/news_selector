#!/usr/bin/env python3
"""
测试认证流程的简单脚本
"""

from src.api.auth import InoreaderAuth

def test_auth():
    """测试认证流程"""
    auth = InoreaderAuth()
    
    print("=== 新闻订阅工具认证测试 ===")
    print()
    
    if auth.is_authenticated():
        print("✅ 您已经登录")
        print("如果需要重新登录，请先运行: python main.py logout")
        return
    
    print("🔐 开始登录流程...")
    print()
    print("注意事项:")
    print("1. 应用会启动本地服务器监听认证回调")
    print("2. 浏览器将自动打开Inoreader登录页面")
    print("3. 完成登录和授权后会自动返回应用")
    print("4. 整个过程是自动的，无需手动复制任何内容")
    print()
    
    if auth.start_auth_flow():
        print("✅ 登录成功！")
        print("现在您可以使用以下命令:")
        print("  python main.py news      # 获取最新新闻")
        print("  python main.py feeds     # 查看订阅源")
        print("  python gui.py            # 启动图形界面")
    else:
        print("❌ 登录失败")
        print("请检查:")
        print("1. 网络连接是否正常")
        print("2. 是否完成了浏览器中的授权步骤")
        print("3. 防火墙是否阻止了本地服务器")
        print("4. 是否在5分钟内完成了认证")

if __name__ == '__main__':
    test_auth()
