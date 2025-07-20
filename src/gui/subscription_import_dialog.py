"""
订阅源导入对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import List, Dict, Any, Optional

from ..services.subscription_export_service import SubscriptionExportService


class SubscriptionImportProgressDialog:
    """订阅源导入进度对话框"""
    
    def __init__(self, parent, export_data: List[Dict[str, Any]]):
        self.parent = parent
        self.export_data = export_data
        self.export_service = SubscriptionExportService()
        self.cancelled = False
        self.completed = False
        self.result = None
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("批量导入RSS订阅源")
        self.dialog.geometry("600x400")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self.create_widgets()
        self.center_window()
        
        # 开始导入
        self.start_import()
        
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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 标题
        title_label = ttk.Label(main_frame, text="🔄 正在导入RSS订阅源...", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 15))
        
        # 状态信息框架
        status_frame = ttk.LabelFrame(main_frame, text="导入状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 当前状态
        self.status_label = ttk.Label(status_frame, text="准备开始导入...", 
                                     font=("Arial", 10))
        self.status_label.pack(anchor=tk.W)
        
        # 进度条框架
        progress_frame = ttk.Frame(status_frame)
        progress_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 进度百分比
        self.progress_label = ttk.Label(progress_frame, text="0%", width=8)
        self.progress_label.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 详细日志框架
        log_frame = ttk.LabelFrame(main_frame, text="导入详情", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 创建日志文本框和滚动条
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(log_container, height=12, wrap=tk.WORD, 
                               font=("Consolas", 9), state=tk.DISABLED,
                               bg="#f8f9fa", fg="#333333")
        
        log_scrollbar = ttk.Scrollbar(log_container, orient=tk.VERTICAL, 
                                     command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(15, 0))
        
        # 右侧按钮
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        self.cancel_button = ttk.Button(right_buttons, text="取消", command=self.cancel)
        self.cancel_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.close_button = ttk.Button(right_buttons, text="关闭", command=self.close, state=tk.DISABLED)
        self.close_button.pack(side=tk.LEFT)
    
    def update_status(self, message: str):
        """更新状态信息"""
        if not self.cancelled:
            self.status_label.config(text=message)
            self.dialog.update_idletasks()
    
    def set_progress(self, current: int, total: int):
        """设置进度"""
        if not self.cancelled:
            percentage = (current / total) * 100 if total > 0 else 0
            self.progress_var.set(percentage)
            self.progress_label.config(text=f"{percentage:.1f}%")
            self.dialog.update_idletasks()
    
    def add_log(self, message: str, level: str = "info"):
        """添加日志"""
        if not self.cancelled:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # 根据级别添加图标
            icons = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "skip": "⏭️"
            }
            icon = icons.get(level, "ℹ️")
            
            log_entry = f"[{timestamp}] {icon} {message}"
            
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, log_entry + "\n")
            self.log_text.see(tk.END)  # 自动滚动到底部
            self.log_text.config(state=tk.DISABLED)
            self.dialog.update_idletasks()
    
    def start_import(self):
        """开始导入"""
        def import_task():
            try:
                # 进度回调函数
                def progress_callback(current, total, message):
                    if not self.cancelled:
                        self.dialog.after(0, lambda: self.update_status(f"正在处理: {message}"))
                        self.dialog.after(0, lambda: self.set_progress(current, total))
                        self.dialog.after(0, lambda: self.add_log(f"处理第 {current}/{total} 项: {message}"))
                
                # 执行批量导入
                success, summary, results = self.export_service.batch_import_to_custom_rss(
                    self.export_data, progress_callback
                )
                
                # 在主线程中处理结果
                if not self.cancelled:
                    self.dialog.after(0, lambda: self._handle_import_result(success, summary, results))
                
            except Exception as e:
                if not self.cancelled:
                    self.dialog.after(0, lambda: self._handle_import_error(str(e)))
        
        # 启动导入线程
        self.import_thread = threading.Thread(target=import_task, daemon=True)
        self.import_thread.start()
    
    def _handle_import_result(self, success: bool, summary: str, results: Dict[str, Any]):
        """处理导入结果"""
        self.result = results
        self.completed = True
        
        # 更新状态
        self.update_status("导入完成！")
        self.set_progress(100, 100)
        
        # 添加结果日志
        self.add_log("=" * 50)
        self.add_log("导入完成！", "success")
        self.add_log(f"总计: {results.get('total', 0)} 个订阅源")
        self.add_log(f"成功: {results.get('success', 0)} 个", "success")
        self.add_log(f"跳过: {results.get('skipped', 0)} 个", "skip")
        self.add_log(f"失败: {results.get('failed', 0)} 个", "error")
        
        # 显示详细结果
        if results.get('failed_items'):
            self.add_log("\n失败的订阅源:", "error")
            for item in results['failed_items']:
                self.add_log(f"  • {item['title']}: {item['reason']}", "error")
        
        if results.get('skipped_items'):
            self.add_log("\n跳过的订阅源:", "skip")
            for item in results['skipped_items']:
                self.add_log(f"  • {item['title']}: {item['reason']}", "skip")
        
        # 启用关闭按钮
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)
    
    def _handle_import_error(self, error: str):
        """处理导入错误"""
        self.add_log(f"导入过程发生错误: {error}", "error")
        self.update_status("导入失败")
        
        # 启用关闭按钮
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)
        
        messagebox.showerror("导入错误", f"导入过程中发生错误:\n{error}")
    
    def cancel(self):
        """取消导入"""
        self.cancelled = True
        self.update_status("正在取消导入...")
        self.add_log("用户取消了导入操作", "warning")
        self.cancel_button.config(state=tk.DISABLED)
        self.close_button.config(state=tk.NORMAL)
    
    def close(self):
        """关闭对话框"""
        self.dialog.destroy()
