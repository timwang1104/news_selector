"""
统一筛选对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox

class FilterDialog:
    """统一筛选对话框"""

    def __init__(self, parent, main_window=None):
        self.parent = parent  # tkinter根窗口
        self.main_window = main_window  # 主窗口对象
        self.result = None
        self.dialog = None

        # 筛选模式变量
        self.filter_mode_var = tk.StringVar(value="batch")  # "batch" 或 "single"
        self.filter_type_var = tk.StringVar(value="chain")
        self.selected_subscription_var = tk.StringVar()

        # 获取订阅源列表
        self.subscriptions = self._get_subscriptions()

    def _get_subscriptions(self):
        """获取订阅源列表"""
        if self.main_window and hasattr(self.main_window, 'current_subscriptions'):
            return self.main_window.current_subscriptions
        return []

    def show(self):
        """显示对话框并返回筛选配置"""
        self.create_dialog()
        self.dialog.wait_window()
        return self.result
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("智能筛选")
        self.dialog.geometry("550x500")
        self.dialog.resizable(True, True)

        # 设置为模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        # 居中显示
        self.center_dialog()

        # 创建界面
        self.create_widgets()
    
    def center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题
        title_label = ttk.Label(main_frame, text="智能筛选", font=("", 14, "bold"))
        title_label.pack(pady=(0, 20))

        # 筛选模式选择
        mode_frame = ttk.LabelFrame(main_frame, text="筛选模式", padding="10")
        mode_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Radiobutton(mode_frame, text="批量筛选", variable=self.filter_mode_var,
                       value="batch").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="单个订阅源筛选", variable=self.filter_mode_var,
                       value="single").pack(anchor=tk.W, pady=(10, 0))

        # 显示当前选中的RSS订阅源
        if (self.main_window and hasattr(self.main_window, 'rss_manager') and
            self.main_window.rss_manager and self.main_window.rss_manager.selected_feed):
            selected_title = self.main_window.rss_manager.selected_feed.title
            if len(selected_title) > 40:
                selected_title = selected_title[:37] + "..."
            info_text = f"当前选中: {selected_title}"
        else:
            info_text = "当前未选中任何RSS订阅源"

        info_label = ttk.Label(mode_frame, text=info_text, foreground="gray", font=("", 9))
        info_label.pack(anchor=tk.W, pady=(5, 0))

        # 筛选类型选择
        filter_frame = ttk.LabelFrame(main_frame, text="筛选类型", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Radiobutton(filter_frame, text="关键词筛选",
                       variable=self.filter_type_var, value="keyword").pack(anchor=tk.W)
        ttk.Radiobutton(filter_frame, text="智能筛选",
                       variable=self.filter_type_var, value="ai").pack(anchor=tk.W)
        ttk.Radiobutton(filter_frame, text="综合筛选（推荐）",
                       variable=self.filter_type_var, value="chain").pack(anchor=tk.W)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        # 左侧按钮
        ttk.Button(button_frame, text="筛选配置",
                  command=self.show_config).pack(side=tk.LEFT)

        # 右侧按钮
        ttk.Button(button_frame, text="取消",
                  command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="确定",
                  command=self.start_filter).pack(side=tk.RIGHT, padx=(0, 10))

        print("筛选对话框按钮已创建")  # 调试信息
    
    def show_config(self):
        """显示筛选配置"""
        try:
            from .filter_config_dialog import FilterConfigDialog
            config_dialog = FilterConfigDialog(self.dialog)
            if config_dialog.result:
                messagebox.showinfo("提示", "配置已更新，下次筛选时生效")
        except Exception as e:
            messagebox.showerror("错误", f"打开配置失败: {e}")

    def start_filter(self):
        """开始筛选"""
        print("确定按钮被点击")  # 调试信息
        mode = self.filter_mode_var.get()
        filter_type = self.filter_type_var.get()

        self.result = {
            "mode": mode,
            "filter_type": filter_type
        }

        # 如果是单个订阅源筛选模式，需要检查是否有选中的RSS订阅源
        if mode == "single":
            if (self.main_window and hasattr(self.main_window, 'rss_manager') and
                self.main_window.rss_manager and self.main_window.rss_manager.selected_feed):
                # 创建一个模拟的subscription对象，用于兼容现有接口
                rss_feed = self.main_window.rss_manager.selected_feed
                subscription = type('Subscription', (), {
                    'id': f"rss_{rss_feed.id}",
                    'title': rss_feed.title
                })()
                self.result["subscription"] = subscription
            else:
                messagebox.showwarning("警告", "请先在RSS管理器中选择要筛选的订阅源")
                return

        print(f"筛选配置: {self.result}")  # 调试信息
        self.dialog.destroy()

    def cancel(self):
        """取消"""
        print("取消按钮被点击")  # 调试信息
        self.result = None
        self.dialog.destroy()
