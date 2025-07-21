"""
批量筛选配置对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from ..services.batch_filter_service import BatchFilterConfig


class BatchFilterDialog:
    """批量筛选配置对话框"""
    
    def __init__(self, parent, auth=None):
        self.parent = parent
        self.auth = auth
        self.result = None
        self.dialog = None
        
        # 配置变量
        self.max_subscriptions_var = tk.StringVar(value="")

        self.articles_per_sub_var = tk.StringVar(value="20")
        self.filter_type_var = tk.StringVar(value="chain")
        self.enable_parallel_var = tk.BooleanVar(value=True)
        self.max_workers_var = tk.StringVar(value="3")
        self.min_score_var = tk.StringVar(value="0.6")
        self.max_results_per_sub_var = tk.StringVar(value="5")
        self.hours_back_var = tk.StringVar(value="24")
        self.exclude_read_var = tk.BooleanVar(value=True)
    
    def show(self) -> Optional[BatchFilterConfig]:
        """显示对话框并返回配置"""
        self.create_dialog()
        self.dialog.wait_window()
        return self.result
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("批量筛选配置")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        
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
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建滚动框架
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 订阅源配置
        self.create_subscription_config(scrollable_frame)
        
        # 文章获取配置
        self.create_article_config(scrollable_frame)
        
        # 筛选配置
        self.create_filter_config(scrollable_frame)
        
        # 性能配置
        self.create_performance_config(scrollable_frame)
        
        # 结果配置
        self.create_result_config(scrollable_frame)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="开始筛选", command=self.start_filter).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="重置", command=self.reset_config).pack(side=tk.LEFT)
        
        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_subscription_config(self, parent):
        """创建订阅源配置"""
        group = ttk.LabelFrame(parent, text="订阅源配置", padding="10")
        group.pack(fill=tk.X, pady=(0, 10))

        # 最大订阅源数量
        ttk.Label(group, text="最大处理订阅源数量:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(group, textvariable=self.max_subscriptions_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(group, text="(留空表示处理所有订阅源)", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
    
    def create_article_config(self, parent):
        """创建文章获取配置"""
        group = ttk.LabelFrame(parent, text="文章获取配置", padding="10")
        group.pack(fill=tk.X, pady=(0, 10))
        
        # 每个订阅源文章数量
        ttk.Label(group, text="每个订阅源获取文章数:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(group, textvariable=self.articles_per_sub_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # 时间范围
        ttk.Label(group, text="获取多少小时内的文章:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(group, textvariable=self.hours_back_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        ttk.Label(group, text="小时", foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
        
        # 排除已读
        ttk.Checkbutton(group, text="排除已读文章", variable=self.exclude_read_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))
    
    def create_filter_config(self, parent):
        """创建筛选配置"""
        group = ttk.LabelFrame(parent, text="筛选配置", padding="10")
        group.pack(fill=tk.X, pady=(0, 10))
        
        # 筛选类型
        ttk.Label(group, text="筛选类型:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        filter_frame = ttk.Frame(group)
        filter_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=(10, 0))
        
        ttk.Radiobutton(filter_frame, text="关键词筛选", variable=self.filter_type_var, value="keyword").pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="智能筛选", variable=self.filter_type_var, value="ai").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(filter_frame, text="综合筛选", variable=self.filter_type_var, value="chain").pack(side=tk.LEFT, padx=(10, 0))
        
        # 最小分数阈值
        ttk.Label(group, text="最小分数阈值:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(group, textvariable=self.min_score_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(group, text="(0.0-1.0)", foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
    
    def create_performance_config(self, parent):
        """创建性能配置"""
        group = ttk.LabelFrame(parent, text="性能配置", padding="10")
        group.pack(fill=tk.X, pady=(0, 10))
        
        # 并行处理
        ttk.Checkbutton(group, text="启用并行处理", variable=self.enable_parallel_var).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # 并行线程数
        ttk.Label(group, text="最大并行线程数:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Entry(group, textvariable=self.max_workers_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        ttk.Label(group, text="(建议2-5)", foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=(5, 0))
    
    def create_result_config(self, parent):
        """创建结果配置"""
        group = ttk.LabelFrame(parent, text="结果配置", padding="10")
        group.pack(fill=tk.X, pady=(0, 10))
        
        # 每个订阅源最大结果数
        ttk.Label(group, text="每个订阅源最大结果数:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(group, textvariable=self.max_results_per_sub_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(group, text="(留空表示不限制)", foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
    
    def start_filter(self):
        """开始筛选"""
        try:
            # 验证输入
            if not self.validate_input():
                return
            
            # 创建配置对象
            config = BatchFilterConfig()
            
            # 订阅源配置
            max_subs = self.max_subscriptions_var.get().strip()
            if max_subs:
                config.max_subscriptions = int(max_subs)

            # 文章获取配置
            config.articles_per_subscription = int(self.articles_per_sub_var.get())
            config.exclude_read = self.exclude_read_var.get()
            
            hours_back = self.hours_back_var.get().strip()
            if hours_back:
                config.hours_back = int(hours_back)
            
            # 筛选配置
            config.filter_type = self.filter_type_var.get()
            
            min_score = self.min_score_var.get().strip()
            if min_score:
                config.min_score_threshold = float(min_score)
            
            # 性能配置
            config.enable_parallel = self.enable_parallel_var.get()
            config.max_workers = int(self.max_workers_var.get())
            
            # 结果配置
            max_results = self.max_results_per_sub_var.get().strip()
            if max_results:
                config.max_results_per_subscription = int(max_results)
            
            self.result = config
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("输入错误", f"请检查输入的数值格式: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"配置创建失败: {e}")
    
    def validate_input(self) -> bool:
        """验证输入"""
        try:
            # 验证数值输入
            max_subs = self.max_subscriptions_var.get().strip()
            if max_subs and (not max_subs.isdigit() or int(max_subs) <= 0):
                messagebox.showerror("输入错误", "最大订阅源数量必须是正整数")
                return False
            
            if not self.articles_per_sub_var.get().isdigit() or int(self.articles_per_sub_var.get()) <= 0:
                messagebox.showerror("输入错误", "每个订阅源文章数必须是正整数")
                return False
            
            hours_back = self.hours_back_var.get().strip()
            if hours_back and (not hours_back.isdigit() or int(hours_back) <= 0):
                messagebox.showerror("输入错误", "时间范围必须是正整数")
                return False
            
            min_score = self.min_score_var.get().strip()
            if min_score:
                score = float(min_score)
                if score < 0 or score > 1:
                    messagebox.showerror("输入错误", "最小分数阈值必须在0.0-1.0之间")
                    return False
            
            if not self.max_workers_var.get().isdigit() or int(self.max_workers_var.get()) <= 0:
                messagebox.showerror("输入错误", "最大并行线程数必须是正整数")
                return False
            
            max_results = self.max_results_per_sub_var.get().strip()
            if max_results and (not max_results.isdigit() or int(max_results) <= 0):
                messagebox.showerror("输入错误", "每个订阅源最大结果数必须是正整数")
                return False

            return True
            
        except ValueError:
            messagebox.showerror("输入错误", "请检查数值输入格式")
            return False
    
    def reset_config(self):
        """重置配置"""
        self.max_subscriptions_var.set("")

        self.articles_per_sub_var.set("20")
        self.filter_type_var.set("chain")
        self.enable_parallel_var.set(True)
        self.max_workers_var.set("3")
        self.min_score_var.set("0.6")
        self.max_results_per_sub_var.set("5")
        self.hours_back_var.set("24")
        self.exclude_read_var.set(True)
    
    def cancel(self):
        """取消"""
        self.result = None
        self.dialog.destroy()
