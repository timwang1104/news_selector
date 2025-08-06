"""
批量导出对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
from datetime import datetime
from typing import List, Dict, Any

from ...models.news import NewsArticle
from ...services.table_export_service import get_table_export_service
from ...filters.base import FilterChainResult


class BatchExportDialog:
    """批量导出对话框"""
    
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
        self.output_dir_var = tk.StringVar()
        self.enable_translation_var = tk.BooleanVar(value=False)
        
        # 格式选择变量
        self.format_vars = {
            "excel": tk.BooleanVar(value=True),
            "csv": tk.BooleanVar(value=True),
            "html": tk.BooleanVar(value=False),
            "json": tk.BooleanVar(value=False)
        }
        
        # 进度相关
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="准备批量导出...")
        self.current_format_var = tk.StringVar()
        
        # 结果统计
        self.results = {}
    
    def show(self):
        """显示对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("批量导出")
        self.dialog.geometry("600x550")
        self.dialog.resizable(True, True)
        self.dialog.minsize(550, 500)
        
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
        
        # 格式选择
        self.create_format_selection(main_frame)
        
        # 输出目录
        self.create_output_directory(main_frame)
        
        # 高级选项
        self.create_advanced_options(main_frame)
        
        # 进度显示
        self.create_progress_section(main_frame)
        
        # 结果显示
        self.create_results_section(main_frame)
        
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
            
            sources_text = ", ".join([f"{source}({count})" for source, count in list(sources.items())[:3]])
            if len(sources) > 3:
                sources_text += f" 等{len(sources)}个来源"
            
            ttk.Label(info_frame, text=f"来源: {sources_text}", wraplength=500).pack(anchor=tk.W)
    
    def create_format_selection(self, parent):
        """创建格式选择区域"""
        format_frame = ttk.LabelFrame(parent, text="导出格式", padding="5")
        format_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 创建两列布局
        left_frame = ttk.Frame(format_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        right_frame = ttk.Frame(format_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 格式选项
        formats = [
            ("Excel文件 (.xlsx)", "excel", "推荐用于数据分析"),
            ("CSV文件 (.csv)", "csv", "通用格式，兼容性好"),
            ("HTML报告 (.html)", "html", "适合查看和分享"),
            ("JSON数据 (.json)", "json", "适合程序处理")
        ]
        
        for i, (text, value, desc) in enumerate(formats):
            frame = left_frame if i < 2 else right_frame
            
            cb = ttk.Checkbutton(frame, text=text, variable=self.format_vars[value])
            cb.pack(anchor=tk.W, pady=2)
            
            ttk.Label(frame, text=f"  {desc}", font=("Arial", 8), foreground="gray").pack(anchor=tk.W)
        
        # 全选/全不选按钮
        button_frame = ttk.Frame(format_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="全选", command=self.select_all_formats).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="全不选", command=self.deselect_all_formats).pack(side=tk.LEFT)
    
    def create_output_directory(self, parent):
        """创建输出目录选择"""
        dir_frame = ttk.LabelFrame(parent, text="输出目录", padding="5")
        dir_frame.pack(fill=tk.X, pady=(0, 10))
        
        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill=tk.X)
        
        self.dir_entry = ttk.Entry(dir_entry_frame, textvariable=self.output_dir_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        ttk.Button(dir_entry_frame, text="浏览...", command=self.browse_output_directory).pack(side=tk.RIGHT)
        
        # 设置默认目录
        self.output_dir_var.set("output")
    
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
            text="注意: 启用翻译功能会显著增加导出时间",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W, padx=(20, 0))
    
    def create_progress_section(self, parent):
        """创建进度显示区域"""
        progress_frame = ttk.LabelFrame(parent, text="导出进度", padding="5")
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.pack(anchor=tk.W, pady=(0, 2))
        
        # 当前格式标签
        self.current_format_label = ttk.Label(progress_frame, textvariable=self.current_format_var, font=("Arial", 8))
        self.current_format_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X)
    
    def create_results_section(self, parent):
        """创建结果显示区域"""
        results_frame = ttk.LabelFrame(parent, text="导出结果", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建结果树
        columns = ("格式", "状态", "文件路径")
        self.results_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=4)
        
        # 设置列标题
        for col in columns:
            self.results_tree.heading(col, text=col)
            self.results_tree.column(col, width=100)
        
        # 调整列宽
        self.results_tree.column("格式", width=80)
        self.results_tree.column("状态", width=80)
        self.results_tree.column("文件路径", width=300)
        
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.results_tree.configure(yscrollcommand=scrollbar.set)
    
    def create_buttons(self, parent):
        """创建按钮"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(15, 10))

        # 左侧按钮
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        self.open_dir_button = ttk.Button(
            left_frame,
            text="打开输出目录",
            command=self.open_output_directory,
            state="disabled",
            width=15
        )
        self.open_dir_button.pack(side=tk.LEFT)

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
            text="开始批量导出",
            command=self.start_batch_export,
            width=18
        )
        self.export_button.pack(side=tk.RIGHT, padx=(5, 5))
    
    def select_all_formats(self):
        """全选格式"""
        for var in self.format_vars.values():
            var.set(True)
    
    def deselect_all_formats(self):
        """全不选格式"""
        for var in self.format_vars.values():
            var.set(False)
    
    def browse_output_directory(self):
        """浏览输出目录"""
        directory = filedialog.askdirectory(
            title="选择输出目录",
            initialdir=self.output_dir_var.get()
        )
        
        if directory:
            self.output_dir_var.set(directory)
    
    def start_batch_export(self):
        """开始批量导出"""
        # 验证输入
        selected_formats = [fmt for fmt, var in self.format_vars.items() if var.get()]
        if not selected_formats:
            messagebox.showwarning("警告", "请至少选择一种导出格式")
            return
        
        if not self.output_dir_var.get().strip():
            messagebox.showwarning("警告", "请选择输出目录")
            return
        
        if not self.articles:
            messagebox.showwarning("警告", "没有可导出的文章")
            return
        
        # 禁用导出按钮
        self.export_button.config(state="disabled")
        
        # 清空结果树
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # 重置进度
        self.progress_var.set(0)
        self.status_var.set("正在准备批量导出...")
        self.current_format_var.set("")
        
        # 在后台线程中执行导出
        self.export_thread = threading.Thread(
            target=self._do_batch_export, 
            args=(selected_formats,),
            daemon=True
        )
        self.export_thread.start()
    
    def _do_batch_export(self, selected_formats: List[str]):
        """执行批量导出（在后台线程中运行）"""
        try:
            # 获取导出服务
            export_service = get_table_export_service(
                enable_translation=self.enable_translation_var.get()
            )
            
            # 获取筛选结果
            if self.filter_result:
                # 如果已有筛选结果，直接使用
                self.dialog.after(0, lambda: self.status_var.set("使用现有筛选结果..."))
                self.dialog.after(0, lambda: self.progress_var.set(20))
                filter_result = self.filter_result
            else:
                # 如果没有筛选结果，执行筛选
                self.dialog.after(0, lambda: self.status_var.set("正在筛选文章..."))
                self.dialog.after(0, lambda: self.progress_var.set(10))

                from ...services.filter_service import get_filter_service
                filter_result = get_filter_service().filter_articles(
                    articles=self.articles,
                    filter_type="keyword"
                )

                self.dialog.after(0, lambda: self.progress_var.set(20))

            if not filter_result.selected_articles:
                self.dialog.after(0, lambda: messagebox.showwarning("警告", "没有文章通过筛选"))
                return

            # 执行批量导出
            self.dialog.after(0, lambda: self.status_var.set("正在批量导出..."))
            self.dialog.after(0, lambda: self.progress_var.set(30))
            
            batch_result = export_service.batch_export(
                results=filter_result.selected_articles,
                formats=selected_formats,
                output_dir=self.output_dir_var.get()
            )
            
            # 更新结果显示
            self.dialog.after(0, lambda: self._update_results_display(batch_result))
            self.dialog.after(0, lambda: self.progress_var.set(100))
            self.dialog.after(0, lambda: self.status_var.set("批量导出完成"))
            
            # 启用打开目录按钮
            self.dialog.after(0, lambda: self.open_dir_button.config(state="normal"))
            
            # 显示完成消息
            success_count = batch_result.get("successful_exports", 0)
            total_count = batch_result.get("total_formats", 0)
            
            self.export_completed = True  # 标记导出完成
            self.dialog.after(0, lambda: messagebox.showinfo(
                "完成",
                f"批量导出完成！\n成功: {success_count}/{total_count} 种格式\n输出目录: {self.output_dir_var.get()}"
            ))
            self.dialog.after(0, self.close_dialog)  # 自动关闭对话框
            
        except Exception as e:
            self.dialog.after(0, lambda: self.status_var.set(f"批量导出失败: {str(e)}"))
            self.dialog.after(0, lambda: messagebox.showerror("错误", f"批量导出失败: {str(e)}"))
        
        finally:
            # 重新启用导出按钮
            self.dialog.after(0, lambda: self.export_button.config(state="normal"))
    
    def _update_results_display(self, batch_result: Dict[str, Any]):
        """更新结果显示"""
        results = batch_result.get("results", {})
        
        for format_type, result in results.items():
            status = "✅ 成功" if result.get("success", False) else "❌ 失败"
            
            # 获取文件路径
            if result.get("success", False):
                message = result.get("message", "")
                # 从消息中提取文件路径（简单实现）
                file_path = message.split("到 ")[-1] if "到 " in message else "已生成"
            else:
                file_path = result.get("message", "失败")
            
            # 添加到结果树
            self.results_tree.insert("", "end", values=(format_type.upper(), status, file_path))
    
    def open_output_directory(self):
        """打开输出目录"""
        output_dir = self.output_dir_var.get()
        if os.path.exists(output_dir):
            import subprocess
            import platform
            
            try:
                if platform.system() == "Windows":
                    os.startfile(output_dir)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", output_dir])
                else:  # Linux
                    subprocess.run(["xdg-open", output_dir])
            except Exception as e:
                messagebox.showerror("错误", f"无法打开目录: {str(e)}")
        else:
            messagebox.showwarning("警告", "输出目录不存在")
    
    def on_close(self):
        """关闭对话框"""
        # 如果导出已完成，直接关闭
        if self.export_completed:
            self.close_dialog()
            return
            
        # 如果正在导出，询问是否取消
        if self.export_thread and self.export_thread.is_alive():
            if messagebox.askyesno("确认", "批量导出正在进行中，确定要取消吗？"):
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
