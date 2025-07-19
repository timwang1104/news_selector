"""
批量筛选进度对话框
"""
import tkinter as tk
from tkinter import ttk
from typing import Optional

from ..services.batch_filter_service import BatchFilterProgressCallback
from ..filters.base import BatchFilterResult
from ..models.subscription import Subscription


class BatchFilterProgressDialog(BatchFilterProgressCallback):
    """批量筛选进度对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.dialog = None
        self.is_closed = False
        
        # 进度变量
        self.total_subscriptions = 0
        self.current_subscription = 0
        self.total_articles_fetched = 0
        self.total_articles_selected = 0
        
        # 界面组件
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="准备开始...")
        self.current_sub_var = tk.StringVar(value="")
        self.stats_var = tk.StringVar(value="")
        
        # 进度条和标签
        self.progress_bar = None
        self.status_label = None
        self.current_sub_label = None
        self.stats_label = None
        self.log_text = None
        
        # 日志列表
        self.log_messages = []
    
    def show(self):
        """显示进度对话框"""
        if self.is_closed:
            return
            
        self.create_dialog()
        
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("批量筛选进度")
        self.dialog.geometry("600x400")
        self.dialog.resizable(True, True)
        
        # 设置为模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建界面
        self.create_widgets()
        
        # 禁用关闭按钮（防止用户意外关闭）
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close_attempt)
    
    def center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态信息
        status_frame = ttk.LabelFrame(main_frame, text="处理状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 总体状态
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("", 10, "bold"))
        self.status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 当前处理的订阅源
        self.current_sub_label = ttk.Label(status_frame, textvariable=self.current_sub_var, foreground="blue")
        self.current_sub_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 统计信息
        self.stats_label = ttk.Label(status_frame, textvariable=self.stats_var, foreground="gray")
        self.stats_label.pack(anchor=tk.W)
        
        # 进度条
        progress_frame = ttk.LabelFrame(main_frame, text="进度", padding="10")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(anchor=tk.W)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text="处理日志", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建滚动文本框
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_container, height=10, wrap=tk.WORD, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.close_button = ttk.Button(button_frame, text="后台运行", command=self.minimize_dialog, state=tk.NORMAL)
        self.close_button.pack(side=tk.RIGHT)
    
    def add_log_message(self, message: str, level: str = "INFO"):
        """添加日志消息"""
        if self.is_closed or not self.log_text:
            return
            
        try:
            self.log_text.config(state=tk.NORMAL)
            
            # 添加时间戳和级别
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {level}: {message}\n"
            
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)  # 滚动到底部
            self.log_text.config(state=tk.DISABLED)
            
            # 更新界面
            self.dialog.update_idletasks()
            
        except tk.TclError:
            # 对话框可能已经被销毁
            pass
    
    def update_progress(self):
        """更新进度显示"""
        if self.is_closed or not self.progress_bar:
            return
            
        try:
            if self.total_subscriptions > 0:
                progress = (self.current_subscription / self.total_subscriptions) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{progress:.1f}% ({self.current_subscription}/{self.total_subscriptions})")
            
            # 更新统计信息
            stats_text = f"已获取文章: {self.total_articles_fetched} 篇 | 已筛选文章: {self.total_articles_selected} 篇"
            self.stats_var.set(stats_text)
            
            # 更新界面
            self.dialog.update_idletasks()
            
        except tk.TclError:
            # 对话框可能已经被销毁
            pass
    
    # 实现BatchFilterProgressCallback接口
    def on_batch_start(self, total_subscriptions: int):
        """批量筛选开始"""
        self.total_subscriptions = total_subscriptions
        self.current_subscription = 0
        self.status_var.set(f"开始批量筛选 {total_subscriptions} 个订阅源...")
        self.add_log_message(f"开始批量筛选，共 {total_subscriptions} 个订阅源")
        self.update_progress()
    
    def on_subscription_start(self, subscription: Subscription, current: int, total: int):
        """开始处理订阅源"""
        self.current_subscription = current
        self.current_sub_var.set(f"正在处理: {subscription.get_display_title()}")
        self.add_log_message(f"[{current}/{total}] 开始处理订阅源: {subscription.title}")
        self.update_progress()
    
    def on_subscription_fetch_complete(self, subscription: Subscription, articles_count: int):
        """订阅源文章获取完成"""
        self.total_articles_fetched += articles_count
        self.add_log_message(f"获取到 {articles_count} 篇文章")
        self.update_progress()
    
    def on_subscription_filter_complete(self, subscription: Subscription, selected_count: int):
        """订阅源筛选完成"""
        self.total_articles_selected += selected_count
        self.add_log_message(f"筛选完成，选中 {selected_count} 篇文章")
        self.update_progress()
    
    def on_subscription_error(self, subscription: Subscription, error: str):
        """订阅源处理错误"""
        self.add_log_message(f"处理失败: {error}", "ERROR")
    
    def on_batch_complete(self, result: BatchFilterResult):
        """批量筛选完成"""
        self.status_var.set("批量筛选完成！")
        self.current_sub_var.set("")
        self.progress_var.set(100)
        self.progress_label.config(text="100% (完成)")
        
        # 更新按钮
        self.close_button.config(text="关闭", command=self.close)
        
        self.add_log_message("批量筛选完成！")
        self.add_log_message(f"处理了 {result.processed_subscriptions}/{result.total_subscriptions} 个订阅源")
        self.add_log_message(f"获取了 {result.total_articles_fetched} 篇文章")
        self.add_log_message(f"筛选出 {result.total_articles_selected} 篇文章")
        self.add_log_message(f"总耗时: {result.total_processing_time:.2f} 秒")
    
    def on_close_attempt(self):
        """用户尝试关闭对话框"""
        # 如果筛选还在进行中，询问用户是否确认关闭
        if self.progress_var.get() < 100:
            from tkinter import messagebox
            if messagebox.askyesno("确认", "批量筛选正在进行中，确定要关闭进度窗口吗？\n(筛选将在后台继续进行)"):
                self.minimize_dialog()
        else:
            self.close()
    
    def minimize_dialog(self):
        """最小化对话框（后台运行）"""
        if self.dialog:
            self.dialog.withdraw()  # 隐藏窗口但不销毁
    
    def close(self):
        """关闭对话框"""
        self.is_closed = True
        if self.dialog:
            try:
                self.dialog.destroy()
            except tk.TclError:
                pass
        self.dialog = None
