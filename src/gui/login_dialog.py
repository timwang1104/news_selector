"""
登录对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser

from ..api.auth import InoreaderAuth


class LoginDialog:
    """登录对话框"""
    
    def __init__(self, parent, auth: InoreaderAuth):
        self.parent = parent
        self.auth = auth
        self.result = False
        
        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("用户登录")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_window()
        
        # 创建界面
        self.create_widgets()
        
        # 等待对话框关闭
        self.dialog.wait_window()
    
    def center_window(self):
        """居中显示窗口"""
        self.dialog.update_idletasks()
        
        # 获取窗口尺寸
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        
        # 获取屏幕尺寸
        screen_width = self.dialog.winfo_screenwidth()
        screen_height = self.dialog.winfo_screenheight()
        
        # 计算居中位置
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题
        title_label = ttk.Label(main_frame, text="Inoreader 登录", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明文本
        info_text = """请按照以下步骤完成登录:

1. 点击"开始登录"按钮
2. 应用会启动本地服务器并打开浏览器
3. 在浏览器中完成Inoreader账号登录
4. 授权应用访问您的账号
5. 认证成功后会自动返回应用
6. 等待登录完成"""
        
        info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(pady=(0, 20), anchor=tk.W)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 20))

        self.start_login_btn = ttk.Button(button_frame, text="开始登录", command=self.start_login_process)
        self.start_login_btn.pack(side=tk.LEFT)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="请点击'开始登录'开始认证流程", foreground="blue")
        self.status_label.pack(pady=(0, 20))

        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 20))

        # 底部按钮
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        ttk.Button(bottom_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
    
    def start_login_process(self):
        """开始登录流程"""
        # 禁用按钮，显示进度
        self.start_login_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="正在启动认证流程...", foreground="blue")

        def login_process():
            try:
                # 使用完整的认证流程
                success = self.auth.start_auth_flow()

                if success:
                    self.dialog.after(0, self.login_success)
                else:
                    error_msg = "登录失败，可能的原因：\n"
                    error_msg += "1. 重定向URI配置不正确\n"
                    error_msg += "2. 端口8080被占用\n"
                    error_msg += "3. 网络连接问题\n\n"
                    error_msg += "请运行 debug_login.py 进行诊断"
                    self.dialog.after(0, lambda: self.show_error(error_msg))

            except OSError as e:
                if "Address already in use" in str(e):
                    error_msg = "端口8080被占用！\n\n"
                    error_msg += "请关闭占用端口8080的程序，\n"
                    error_msg += "或在Inoreader中配置其他端口。"
                    self.dialog.after(0, lambda: self.show_error(error_msg))
                else:
                    self.dialog.after(0, lambda: self.show_error(f"网络错误: {e}"))
            except Exception as e:
                self.dialog.after(0, lambda: self.show_error(f"登录过程中出错: {e}"))

        # 在后台线程中处理登录
        threading.Thread(target=login_process, daemon=True).start()
    
    def login_success(self):
        """登录成功"""
        self.progress.stop()
        self.status_label.config(text="登录成功！", foreground="green")
        self.result = True

        # 延迟关闭对话框
        self.dialog.after(1000, self.dialog.destroy)

    def show_error(self, message):
        """显示错误信息"""
        self.progress.stop()
        self.status_label.config(text=message, foreground="red")
        self.start_login_btn.config(state=tk.NORMAL)
        messagebox.showerror("错误", message)
    
    def cancel(self):
        """取消登录"""
        self.result = False
        self.dialog.destroy()
