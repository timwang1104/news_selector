#!/usr/bin/env python3
"""
火山引擎依赖安装脚本
"""
import subprocess
import sys
import os

def check_package_installed(package_name):
    """检查包是否已安装"""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def install_package(package_name):
    """安装包"""
    try:
        print(f"正在安装 {package_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 火山引擎依赖安装工具")
    print("=" * 50)
    
    # 需要安装的包
    packages = [
        ("httpx", "httpx>=0.24.0"),
        ("volcenginesdkarkruntime", "volcengine-python-sdk>=1.1.0")
    ]
    
    all_installed = True
    
    for import_name, pip_name in packages:
        print(f"\n检查 {import_name}...")
        
        if check_package_installed(import_name):
            print(f"✅ {import_name} 已安装")
        else:
            print(f"❌ {import_name} 未安装")
            if install_package(pip_name):
                # 重新检查
                if check_package_installed(import_name):
                    print(f"✅ {import_name} 验证成功")
                else:
                    print(f"❌ {import_name} 验证失败")
                    all_installed = False
            else:
                all_installed = False
    
    print("\n" + "=" * 50)
    
    if all_installed:
        print("🎉 所有依赖安装完成！")
        print("\n接下来您可以:")
        print("1. 运行配置检查: python scripts/check_volcengine_config.py")
        print("2. 配置API密钥: python scripts/fix_volcengine_config.py")
        print("3. 开始使用火山引擎AI筛选")
    else:
        print("❌ 部分依赖安装失败")
        print("\n请尝试手动安装:")
        print("pip install volcenginesdkarkruntime httpx")
        print("\n或者安装完整的requirements.txt:")
        print("pip install -r requirements.txt")

if __name__ == "__main__":
    main()
