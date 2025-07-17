"""
GUI应用启动器
"""
import sys
import tkinter as tk
from tkinter import messagebox

from .main_window import MainWindow


def main():
    """启动GUI应用"""
    try:
        # 创建主窗口
        app = MainWindow()
        
        # 运行应用
        app.run()
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保已安装所有必需的依赖包")
        sys.exit(1)
    except Exception as e:
        print(f"应用启动失败: {e}")
        try:
            messagebox.showerror("错误", f"应用启动失败: {e}")
        except:
            pass
        sys.exit(1)


if __name__ == '__main__':
    main()
