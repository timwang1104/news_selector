"""
表格导出对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from datetime import datetime
from typing import List, Optional

from ...models.news import NewsArticle
from ...services.filter_service import get_filter_service
from ...filters.base import FilterChainResult


class TableExportDialog:
    """表格导出对话框"""
    
    def __init__(self, parent, data):
        """
        初始化对话框
        
        Args:
            parent: 父窗口
            data: 要导出的数据，可以是文章列表或FilterChainResult
        """
        self.parent = parent
        self.dialog = None
        self.export_thread = None
        self.export_completed = False  # 标记导出是否已完成

        # 处理不同类型的输入数据
        if isinstance(data, FilterChainResult):
            self.filter_result = data
            self.articles = [result.article for result in data.selected_articles]
        elif isinstance(data, list):
            self.articles = data
            self.filter_result = None
        else:
            raise ValueError("数据类型不支持，请传入文章列表或FilterChainResult")
        
        # 导出选项
        self.format_var = tk.StringVar(value="excel")
        self.enable_translation_var = tk.BooleanVar(value=False)
        self.output_path_var = tk.StringVar()
        
        # 进度相关
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="准备导出...")
        
    def show(self):
        """显示对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("表格导出")
        self.dialog.geometry("550x600")
        self.dialog.resizable(True, True)
        self.dialog.minsize(500, 550)
        
        # 设置模态
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建界面
        self.create_widgets()
        
        # 绑定关闭事件
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        
        # 获取对话框尺寸
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # 获取父窗口位置和尺寸
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # 计算居中位置
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 文章信息
        self.create_article_info(main_frame)
        
        # 导出选项
        self.create_export_options(main_frame)
        
        # 输出路径
        self.create_output_path(main_frame)
        
        # 高级选项
        self.create_advanced_options(main_frame)
        
        # 进度条
        self.create_progress_section(main_frame)
        
        # 按钮
        self.create_buttons(main_frame)
    
    def create_article_info(self, parent):
        """创建文章信息区域"""
        info_frame = ttk.LabelFrame(parent, text="文章信息", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text=f"文章数量: {len(self.articles)} 篇").pack(anchor=tk.W)
        
        if self.articles:
            # 显示文章来源统计
            sources = {}
            for article in self.articles:
                source = article.feed_title or "未知来源"
                sources[source] = sources.get(source, 0) + 1
            
            sources_text = ", ".join([f"{source}({count})" for source, count in sources.items()])
            ttk.Label(info_frame, text=f"来源分布: {sources_text}", wraplength=450).pack(anchor=tk.W)
    
    def create_export_options(self, parent):
        """创建导出选项"""
        options_frame = ttk.LabelFrame(parent, text="导出格式", padding="5")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 格式选择
        formats = [
            ("Excel文件 (.xlsx)", "excel"),
            ("CSV文件 (.csv)", "csv"),
            ("HTML报告 (.html)", "html"),
            ("JSON数据 (.json)", "json")
        ]
        
        for text, value in formats:
            ttk.Radiobutton(
                options_frame, 
                text=text, 
                variable=self.format_var, 
                value=value
            ).pack(anchor=tk.W, pady=2)
    
    def create_output_path(self, parent):
        """创建输出路径选择"""
        path_frame = ttk.LabelFrame(parent, text="输出路径", padding="5")
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill=tk.X)
        
        self.path_entry = ttk.Entry(path_entry_frame, textvariable=self.output_path_var)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(
            path_entry_frame, 
            text="浏览...", 
            command=self.browse_output_path
        ).pack(side=tk.RIGHT)
        
        # 设置默认路径
        self.set_default_output_path()
    
    def create_advanced_options(self, parent):
        """创建高级选项"""
        advanced_frame = ttk.LabelFrame(parent, text="高级选项", padding="5")
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 翻译选项
        ttk.Checkbutton(
            advanced_frame,
            text="启用翻译功能（中英文互译）",
            variable=self.enable_translation_var
        ).pack(anchor=tk.W, pady=2)
        
        # 提示信息
        ttk.Label(
            advanced_frame,
            text="注意: 启用翻译功能会增加导出时间",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W, padx=(20, 0))
    
    def create_progress_section(self, parent):
        """创建进度显示区域"""
        progress_frame = ttk.LabelFrame(parent, text="导出进度", padding="5")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X)
    
    def create_buttons(self, parent):
        """创建按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(15, 10))

        # 左侧按钮
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(
            left_frame,
            text="预览",
            command=self.preview_export,
            width=12
        ).pack(side=tk.LEFT, padx=(0, 5))

        # 右侧按钮
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(
            right_frame,
            text="取消",
            command=self.on_close,
            width=12
        ).pack(side=tk.RIGHT, padx=(5, 0))

        # 确定/导出按钮（更明显的样式）
        self.export_button = ttk.Button(
            right_frame,
            text="确定导出",
            command=self.start_export,
            width=15
        )
        self.export_button.pack(side=tk.RIGHT, padx=(5, 5))
    
    def set_default_output_path(self):
        """设置默认输出路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        format_ext = {
            "excel": "xlsx",
            "csv": "csv", 
            "html": "html",
            "json": "json"
        }
        
        ext = format_ext.get(self.format_var.get(), "xlsx")
        filename = f"news_export_{timestamp}.{ext}"
        self.output_path_var.set(filename)
    
    def browse_output_path(self):
        """浏览输出路径"""
        format_type = self.format_var.get()
        
        filetypes = {
            "excel": [("Excel文件", "*.xlsx"), ("所有文件", "*.*")],
            "csv": [("CSV文件", "*.csv"), ("所有文件", "*.*")],
            "html": [("HTML文件", "*.html"), ("所有文件", "*.*")],
            "json": [("JSON文件", "*.json"), ("所有文件", "*.*")]
        }
        
        filepath = filedialog.asksaveasfilename(
            title="选择导出路径",
            filetypes=filetypes.get(format_type, [("所有文件", "*.*")]),
            defaultextension=f".{format_type}",
            initialvalue=self.output_path_var.get()
        )
        
        if filepath:
            self.output_path_var.set(filepath)
    
    def preview_export(self):
        """预览导出内容"""
        try:
            from .table_preview_dialog import TablePreviewDialog
            
            # 创建并显示详细预览对话框
            preview_dialog = TablePreviewDialog(
                parent=self.dialog,
                articles=self.articles,
                format_type=self.format_var.get(),
                enable_translation=self.enable_translation_var.get()
            )
            preview_dialog.show()
            
        except Exception as e:
            messagebox.showerror("错误", f"预览失败: {str(e)}")
    
    def start_export(self):
        """开始导出"""
        # 验证输入
        if not self.output_path_var.get().strip():
            messagebox.showwarning("警告", "请选择输出路径")
            return
        
        if not self.articles:
            messagebox.showwarning("警告", "没有可导出的文章")
            return
        
        # 禁用导出按钮
        self.export_button.config(state="disabled")
        
        # 重置进度
        self.progress_var.set(0)
        self.status_var.set("正在准备导出...")
        
        # 在后台线程中执行导出
        self.export_thread = threading.Thread(target=self._do_export, daemon=True)
        self.export_thread.start()
    
    def _do_export(self):
        """执行导出（在后台线程中运行）"""
        try:
            # 获取筛选结果
            if self.filter_result:
                # 如果已有筛选结果，直接使用
                self.dialog.after(0, lambda: self.status_var.set("使用现有筛选结果..."))
                self.dialog.after(0, lambda: self.progress_var.set(30))
                filter_result = self.filter_result
            else:
                # 如果没有筛选结果，执行筛选
                self.dialog.after(0, lambda: self.status_var.set("正在筛选文章..."))
                self.dialog.after(0, lambda: self.progress_var.set(10))

                filter_result = get_filter_service().filter_articles(
                    articles=self.articles,
                    filter_type="keyword"  # 使用关键词筛选避免AI调用
                )

                self.dialog.after(0, lambda: self.progress_var.set(30))

            self.dialog.after(0, lambda: self.progress_var.set(50))
            self.dialog.after(0, lambda: self.status_var.set("正在导出表格..."))

            # 执行导出
            export_result = get_filter_service().export_results_to_table(
                result=filter_result,
                output_format=self.format_var.get(),
                output_path=self.output_path_var.get(),
                enable_translation=self.enable_translation_var.get()
            )
            
            self.dialog.after(0, lambda: self.progress_var.set(100))
            
            if export_result.get("success", False):
                self.export_completed = True  # 标记导出完成
                self.dialog.after(0, lambda: self.status_var.set("导出完成"))
                self.dialog.after(0, lambda: messagebox.showinfo(
                    "成功", 
                    f"导出完成！\n文件: {self.output_path_var.get()}\n导出数量: {export_result.get('exported_count', 0)} 篇"
                ))
                self.dialog.after(0, self.close_dialog)  # 直接关闭对话框
            else:
                error_msg = export_result.get("message", "未知错误")
                self.dialog.after(0, lambda: self.status_var.set(f"导出失败: {error_msg}"))
                self.dialog.after(0, lambda: messagebox.showerror("错误", f"导出失败: {error_msg}"))
            
        except Exception as e:
            self.dialog.after(0, lambda: self.status_var.set(f"导出失败: {str(e)}"))
            self.dialog.after(0, lambda: messagebox.showerror("错误", f"导出失败: {str(e)}"))
        
        finally:
            # 重新启用导出按钮
            self.dialog.after(0, lambda: self.export_button.config(state="normal"))
    
    def on_close(self):
        """关闭对话框"""
        # 如果导出已完成，直接关闭
        if self.export_completed:
            self.close_dialog()
            return
            
        # 如果正在导出，询问是否取消
        if self.export_thread and self.export_thread.is_alive():
            if messagebox.askyesno("确认", "导出正在进行中，确定要取消吗？"):
                # 这里可以添加取消导出的逻辑
                self.close_dialog()
            else:
                return
        else:
            self.close_dialog()
    
    def close_dialog(self):
        """直接关闭对话框"""
        if self.dialog:
            self.dialog.destroy()
