"""
筛选进度对话框
"""
import tkinter as tk
from tkinter import ttk
import threading
from ..services.filter_service import FilterService, CLIProgressCallback


class FilterProgressCallback(CLIProgressCallback):
    """GUI筛选进度回调"""

    def __init__(self, dialog, filter_type="chain"):
        super().__init__(show_progress=False)
        self.dialog = dialog
        self.filter_type = filter_type

    def on_start(self, total_articles: int):
        """筛选开始"""
        self.total_articles = total_articles
        filter_names = {
            "keyword": "关键词筛选",
            "ai": "AI筛选",
            "chain": "综合筛选"
        }
        filter_name = filter_names.get(self.filter_type, "筛选")
        self.dialog.update_status(f"开始{filter_name} {total_articles} 篇文章...")
        self.dialog.set_progress(0, 100)

    def on_keyword_progress(self, processed: int, total: int):
        """关键词筛选进度"""
        if self.filter_type == "keyword":
            # 关键词单独筛选时占100%
            percentage = (processed / total) * 90  # 留10%给完成处理
        else:
            # 综合筛选时关键词占50%
            percentage = (processed / total) * 50
        self.dialog.update_status(f"关键词筛选进度: {processed}/{total}")
        self.dialog.set_progress(percentage, 100)

    def on_keyword_complete(self, results_count: int):
        """关键词筛选完成"""
        self.dialog.update_status(f"关键词筛选完成: {results_count} 篇文章通过")
        if self.filter_type == "keyword":
            self.dialog.set_progress(95, 100)
        else:
            self.dialog.set_progress(50, 100)

    def on_ai_progress(self, processed: int, total: int):
        """AI筛选进度"""
        if self.filter_type == "ai":
            # AI单独筛选时占100%
            percentage = (processed / total) * 90  # 留10%给完成处理
        else:
            # 综合筛选时AI占40%
            percentage = 50 + (processed / total) * 40
        self.dialog.update_status(f"AI筛选进度: {processed}/{total}")
        self.dialog.set_progress(percentage, 100)

    def on_ai_complete(self, results_count: int):
        """AI筛选完成"""
        self.dialog.update_status(f"AI筛选完成: {results_count} 篇文章通过")
        if self.filter_type == "ai":
            self.dialog.set_progress(95, 100)
        else:
            self.dialog.set_progress(90, 100)

    def on_complete(self, final_count: int):
        """筛选完成"""
        filter_names = {
            "keyword": "关键词筛选",
            "ai": "AI筛选",
            "chain": "综合筛选"
        }
        filter_name = filter_names.get(self.filter_type, "筛选")
        self.dialog.update_status(f"{filter_name}完成: 最终选出 {final_count} 篇文章")
        self.dialog.set_progress(100, 100)
        self.dialog.on_complete()

    def on_error(self, error: str):
        """筛选错误"""
        self.dialog.update_status(f"筛选错误: {error}")
        self.dialog.on_error(error)


class FilterProgressDialog:
    """筛选进度对话框"""
    
    def __init__(self, parent, articles, filter_type="chain"):
        self.parent = parent
        self.articles = articles
        self.filter_type = filter_type
        self.result = None
        self.cancelled = False
        self.completed = False  # 新增：标记筛选是否正常完成
        self.filter_thread = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("筛选进度")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self.create_widgets()
        self.center_window()
        
        # 开始筛选
        self.start_filtering()
        
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
        title_label = ttk.Label(main_frame, text="正在执行智能筛选...", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 状态信息
        self.status_label = ttk.Label(main_frame, text="准备开始筛选...")
        self.status_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, 
                                          maximum=100, length=300)
        self.progress_bar.pack(pady=(0, 10))
        
        # 进度百分比
        self.progress_label = ttk.Label(main_frame, text="0%")
        self.progress_label.pack(pady=(0, 20))
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()
        
        self.cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.close_button = ttk.Button(button_frame, text="关闭", command=self.close, state=tk.DISABLED)
        self.close_button.pack(side=tk.LEFT)
    
    def update_status(self, message: str):
        """更新状态信息"""
        if not self.cancelled:
            self.status_label.config(text=message)
            self.dialog.update_idletasks()
    
    def set_progress(self, value: float, maximum: float = 100):
        """设置进度"""
        if not self.cancelled:
            self.progress_var.set(value)
            percentage = (value / maximum) * 100
            self.progress_label.config(text=f"{percentage:.1f}%")
            self.dialog.update_idletasks()
    
    def start_filtering(self):
        """开始筛选"""
        def filter_task():
            try:
                filter_service = FilterService()
                callback = FilterProgressCallback(self, self.filter_type)

                # 执行筛选
                result = filter_service.filter_articles(
                    articles=self.articles,
                    filter_type=self.filter_type,
                    callback=callback
                )

                # 确保在主线程中设置结果
                if not self.cancelled:
                    self.dialog.after(0, lambda: self._set_result(result))

            except Exception as e:
                if not self.cancelled:
                    self.dialog.after(0, lambda: self.on_error(str(e)))
        
        self.filter_thread = threading.Thread(target=filter_task, daemon=True)
        self.filter_thread.start()

    def _set_result(self, result):
        """在主线程中设置筛选结果"""
        self.result = result
        print(f"筛选结果已设置: {result.final_selected_count if result else 0} 篇文章")
        # 设置结果后调用完成处理
        self.on_complete()

    def on_complete(self):
        """筛选完成"""
        print(f"🔄 FilterProgressDialog.on_complete() 被调用")
        self.completed = True  # 标记为正常完成
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)

        # 显示完成信息，让用户手动关闭
        self.update_status("筛选完成！请点击关闭按钮。")


    
    def on_error(self, error: str):
        """筛选错误"""
        from tkinter import messagebox
        messagebox.showerror("筛选错误", f"筛选过程中发生错误:\n{error}")
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)
    
    def cancel(self):
        """取消筛选"""
        self.cancelled = True
        self.update_status("正在取消筛选...")
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)
        
        # 注意：实际的筛选线程可能无法立即停止
        # 这里只是标记取消状态，避免更新UI
    
    def close(self):
        """关闭对话框"""
        print(f"🔄 FilterProgressDialog.close() 被调用")
        print(f"   completed: {self.completed}, result: {self.result is not None}")
        # 只有在没有正常完成且没有结果的情况下才标记为取消
        if not self.completed and self.result is None:
            print(f"   设置 cancelled = True")
            self.cancelled = True
        else:
            print(f"   保持 cancelled = {self.cancelled}")
        self.dialog.destroy()


class FilterMetricsDialog:
    """筛选性能指标对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("筛选性能指标")
        self.dialog.geometry("500x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        
        # 创建界面
        self.create_widgets()
        self.load_metrics()
        self.center_window()
    
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
        title_label = ttk.Label(main_frame, text="筛选性能指标", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 创建文本框显示指标
        self.metrics_text = tk.Text(main_frame, wrap=tk.WORD, height=15, width=60)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.metrics_text.yview)
        self.metrics_text.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.metrics_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        ttk.Button(button_frame, text="刷新", command=self.load_metrics).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="重置指标", command=self.reset_metrics).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT)
    
    def load_metrics(self):
        """加载性能指标"""
        try:
            from ..services.filter_service import filter_service
            
            metrics = filter_service.get_metrics()
            
            # 清空文本框
            self.metrics_text.delete(1.0, tk.END)
            
            # 显示指标
            self.metrics_text.insert(tk.END, "筛选性能指标报告\n")
            self.metrics_text.insert(tk.END, "=" * 50 + "\n\n")
            
            for filter_type, filter_metrics in metrics.items():
                if filter_metrics.get('status') == 'no_data':
                    self.metrics_text.insert(tk.END, f"{filter_type.upper()} 筛选器: 暂无数据\n\n")
                    continue
                
                self.metrics_text.insert(tk.END, f"{filter_type.upper()} 筛选器:\n")
                self.metrics_text.insert(tk.END, "-" * 30 + "\n")
                
                if 'avg_processing_time' in filter_metrics:
                    self.metrics_text.insert(tk.END, f"平均处理时间: {filter_metrics['avg_processing_time']:.2f}ms\n")
                    self.metrics_text.insert(tk.END, f"中位数处理时间: {filter_metrics.get('median_processing_time', 0):.2f}ms\n")
                    self.metrics_text.insert(tk.END, f"最大处理时间: {filter_metrics['max_processing_time']:.2f}ms\n")
                    self.metrics_text.insert(tk.END, f"最小处理时间: {filter_metrics['min_processing_time']:.2f}ms\n")
                    self.metrics_text.insert(tk.END, f"处理文章总数: {filter_metrics['total_processed']}\n")
                    self.metrics_text.insert(tk.END, f"错误率: {filter_metrics['error_rate']:.2%}\n")
                
                if 'cache_hit_rate' in filter_metrics:
                    self.metrics_text.insert(tk.END, f"缓存命中率: {filter_metrics['cache_hit_rate']:.2%}\n")
                    self.metrics_text.insert(tk.END, f"缓存大小: {filter_metrics.get('cache_size', 0)}\n")
                    self.metrics_text.insert(tk.END, f"缓存命中次数: {filter_metrics.get('hits', 0)}\n")
                    self.metrics_text.insert(tk.END, f"缓存未命中次数: {filter_metrics.get('misses', 0)}\n")
                
                self.metrics_text.insert(tk.END, "\n")
            
            # 移动到开头
            self.metrics_text.see(1.0)
            
        except Exception as e:
            self.metrics_text.delete(1.0, tk.END)
            self.metrics_text.insert(tk.END, f"加载指标失败: {e}")
    
    def reset_metrics(self):
        """重置性能指标"""
        from tkinter import messagebox
        
        if messagebox.askyesno("确认", "确定要重置所有性能指标吗？"):
            try:
                from ..services.filter_service import filter_service
                filter_service.reset_metrics()
                messagebox.showinfo("成功", "性能指标已重置")
                self.load_metrics()
            except Exception as e:
                messagebox.showerror("错误", f"重置指标失败: {e}")
