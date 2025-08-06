"""表格预览对话框"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional
import threading

from ...models.news import NewsArticle
from ...services.table_export_service import get_table_export_service
from ...filters.base import FilterChainResult, CombinedFilterResult
from ...services.filter_service import get_filter_service


class TablePreviewDialog:
    """表格预览对话框"""
    
    def __init__(self, parent, articles: List[NewsArticle], 
                 format_type: str = "excel", 
                 enable_translation: bool = False):
        """
        初始化预览对话框
        
        Args:
            parent: 父窗口
            articles: 文章列表
            format_type: 导出格式
            enable_translation: 是否启用翻译
        """
        self.parent = parent
        self.articles = articles
        self.format_type = format_type
        self.enable_translation = enable_translation
        self.dialog = None
        self.preview_data = None
        self.loading = False
        
    def show(self):
        """显示预览对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"表格预览 - {self.format_type.upper()}格式")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        self.dialog.minsize(800, 600)
        
        # 设置模态
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建界面
        self.create_widgets()
        
        # 开始加载预览数据
        self.load_preview_data()
        
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
        
        # 信息区域
        self.create_info_section(main_frame)
        
        # 预览区域
        self.create_preview_section(main_frame)
        
        # 按钮区域
        self.create_buttons(main_frame)
    
    def create_info_section(self, parent):
        """创建信息区域"""
        info_frame = ttk.LabelFrame(parent, text="导出信息", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 基本信息
        info_text = f"文章数量: {len(self.articles)} 篇\n"
        info_text += f"导出格式: {self.format_type.upper()}\n"
        info_text += f"翻译功能: {'启用' if self.enable_translation else '禁用'}\n"
        
        # 显示文章来源统计
        if self.articles:
            sources = {}
            for article in self.articles:
                source = article.feed_title or "未知来源"
                sources[source] = sources.get(source, 0) + 1
            
            sources_text = ", ".join([f"{source}({count})" for source, count in sources.items()])
            info_text += f"来源分布: {sources_text}"
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def create_preview_section(self, parent):
        """创建预览区域"""
        preview_frame = ttk.LabelFrame(parent, text="表格预览", padding="5")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建Notebook用于显示不同的预览内容
        self.notebook = ttk.Notebook(preview_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 表格结构标签页
        self.create_structure_tab()
        
        # 样本数据标签页
        self.create_sample_data_tab()
        
        # 统计信息标签页
        self.create_statistics_tab()
    
    def create_structure_tab(self):
        """创建表格结构标签页"""
        structure_frame = ttk.Frame(self.notebook)
        self.notebook.add(structure_frame, text="表格结构")
        
        # 创建Treeview显示列信息
        columns = ("列名", "数据类型", "描述")
        self.structure_tree = ttk.Treeview(structure_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        for col in columns:
            self.structure_tree.heading(col, text=col)
            self.structure_tree.column(col, width=200)
        
        # 添加滚动条
        structure_scrollbar_y = ttk.Scrollbar(structure_frame, orient=tk.VERTICAL, command=self.structure_tree.yview)
        structure_scrollbar_x = ttk.Scrollbar(structure_frame, orient=tk.HORIZONTAL, command=self.structure_tree.xview)
        self.structure_tree.configure(yscrollcommand=structure_scrollbar_y.set, xscrollcommand=structure_scrollbar_x.set)
        
        # 布局
        self.structure_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        structure_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        structure_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_sample_data_tab(self):
        """创建样本数据标签页"""
        sample_frame = ttk.Frame(self.notebook)
        self.notebook.add(sample_frame, text="样本数据")
        
        # 创建Text组件显示样本数据
        self.sample_text = tk.Text(sample_frame, wrap=tk.NONE, font=("Consolas", 9))
        
        # 添加滚动条
        sample_scrollbar_y = ttk.Scrollbar(sample_frame, orient=tk.VERTICAL, command=self.sample_text.yview)
        sample_scrollbar_x = ttk.Scrollbar(sample_frame, orient=tk.HORIZONTAL, command=self.sample_text.xview)
        self.sample_text.configure(yscrollcommand=sample_scrollbar_y.set, xscrollcommand=sample_scrollbar_x.set)
        
        # 布局
        self.sample_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sample_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        sample_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_statistics_tab(self):
        """创建统计信息标签页"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="统计信息")
        
        # 创建Text组件显示统计信息
        self.stats_text = tk.Text(stats_frame, wrap=tk.WORD, font=("Microsoft YaHei", 10))
        
        # 添加滚动条
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_text.yview)
        self.stats_text.configure(yscrollcommand=stats_scrollbar.set)
        
        # 布局
        self.stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_buttons(self, parent):
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 刷新按钮
        ttk.Button(
            button_frame,
            text="刷新预览",
            command=self.refresh_preview,
            width=12
        ).pack(side=tk.LEFT)
        
        # 关闭按钮
        ttk.Button(
            button_frame,
            text="关闭",
            command=self.on_close,
            width=12
        ).pack(side=tk.RIGHT)
    
    def load_preview_data(self):
        """加载预览数据"""
        if self.loading:
            return
            
        self.loading = True
        
        # 显示加载状态
        self.show_loading_state()
        
        # 在后台线程中加载数据
        thread = threading.Thread(target=self._load_preview_data_thread, daemon=True)
        thread.start()
    
    def _load_preview_data_thread(self):
        """在后台线程中加载预览数据"""
        try:
            # 创建筛选结果
            filter_result = get_filter_service().filter_articles(
                articles=self.articles,
                filter_type="keyword"  # 使用关键词筛选避免AI调用
            )
            
            # 获取表格导出服务
            export_service = get_table_export_service(
                enable_translation=self.enable_translation
            )
            
            # 获取预览数据
            preview_data = export_service.preview_table_structure(
                results=filter_result.selected_articles,
                sample_size=5  # 获取5个样本
            )
            
            # 在主线程中更新UI
            self.dialog.after(0, lambda: self.update_preview_ui(preview_data))
            
        except Exception as e:
            error_msg = f"加载预览数据失败: {str(e)}"
            self.dialog.after(0, lambda: self.show_error_state(error_msg))
        
        finally:
            self.loading = False
    
    def show_loading_state(self):
        """显示加载状态"""
        # 清空现有内容
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        self.sample_text.delete(1.0, tk.END)
        self.stats_text.delete(1.0, tk.END)
        
        # 显示加载信息
        self.structure_tree.insert("", tk.END, values=("正在加载...", "", ""))
        self.sample_text.insert(tk.END, "正在加载样本数据...")
        self.stats_text.insert(tk.END, "正在生成统计信息...")
    
    def show_error_state(self, error_msg: str):
        """显示错误状态"""
        # 清空现有内容
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        self.sample_text.delete(1.0, tk.END)
        self.stats_text.delete(1.0, tk.END)
        
        # 显示错误信息
        self.structure_tree.insert("", tk.END, values=("加载失败", "错误", error_msg))
        self.sample_text.insert(tk.END, f"加载失败: {error_msg}")
        self.stats_text.insert(tk.END, f"加载失败: {error_msg}")
    
    def update_preview_ui(self, preview_data: Dict[str, Any]):
        """更新预览UI"""
        self.preview_data = preview_data
        
        # 更新表格结构
        self.update_structure_view()
        
        # 更新样本数据
        self.update_sample_data_view()
        
        # 更新统计信息
        self.update_statistics_view()
    
    def update_structure_view(self):
        """更新表格结构视图"""
        # 清空现有内容
        for item in self.structure_tree.get_children():
            self.structure_tree.delete(item)
        
        if not self.preview_data or "headers" not in self.preview_data:
            self.structure_tree.insert("", tk.END, values=("无数据", "", ""))
            return
        
        # 定义列描述
        column_descriptions = {
            "标题": "文章标题",
            "中文标题": "翻译后的中文标题",
            "摘要": "文章摘要",
            "中文摘要": "翻译后的中文摘要",
            "内容": "文章正文内容",
            "链接": "文章原始链接",
            "发布时间": "文章发布时间",
            "来源": "文章来源/订阅源",
            "作者": "文章作者",
            "标签": "文章标签",
            "语言": "文章语言",
            "筛选原因": "AI筛选的原因说明",
            "筛选分数": "AI筛选的评分"
        }
        
        # 添加列信息
        for header in self.preview_data["headers"]:
            data_type = "文本"
            if "时间" in header or "date" in header.lower():
                data_type = "日期时间"
            elif "分数" in header or "score" in header.lower():
                data_type = "数值"
            elif "链接" in header or "url" in header.lower():
                data_type = "URL"
            
            description = column_descriptions.get(header, "")
            self.structure_tree.insert("", tk.END, values=(header, data_type, description))
    
    def update_sample_data_view(self):
        """更新样本数据视图"""
        self.sample_text.delete(1.0, tk.END)
        
        if not self.preview_data or "sample_data" not in self.preview_data:
            self.sample_text.insert(tk.END, "无样本数据")
            return
        
        sample_data = self.preview_data["sample_data"]
        if not sample_data:
            self.sample_text.insert(tk.END, "无样本数据")
            return
        
        # 格式化显示样本数据
        self.sample_text.insert(tk.END, f"样本数据 (共 {len(sample_data)} 条):\n\n")
        
        for i, row in enumerate(sample_data, 1):
            self.sample_text.insert(tk.END, f"=== 样本 {i} ===\n")
            for key, value in row.items():
                # 限制显示长度
                if isinstance(value, str) and len(value) > 100:
                    display_value = value[:100] + "..."
                else:
                    display_value = str(value) if value is not None else "(空)"
                
                self.sample_text.insert(tk.END, f"{key}: {display_value}\n")
            self.sample_text.insert(tk.END, "\n")
    
    def update_statistics_view(self):
        """更新统计信息视图"""
        self.stats_text.delete(1.0, tk.END)
        
        if not self.preview_data:
            self.stats_text.insert(tk.END, "无统计信息")
            return
        
        # 基本统计
        stats_text = "=== 导出统计信息 ===\n\n"
        stats_text += f"总文章数量: {self.preview_data.get('total_count', 0)} 篇\n"
        stats_text += f"样本数量: {self.preview_data.get('sample_size', 0)} 篇\n"
        stats_text += f"列数量: {len(self.preview_data.get('headers', []))} 列\n\n"
        
        # 列信息统计
        headers = self.preview_data.get('headers', [])
        if headers:
            stats_text += "=== 列信息 ===\n"
            for i, header in enumerate(headers, 1):
                stats_text += f"{i}. {header}\n"
            stats_text += "\n"
        
        # 文章来源统计
        if self.articles:
            stats_text += "=== 来源统计 ===\n"
            sources = {}
            for article in self.articles:
                source = article.feed_title or "未知来源"
                sources[source] = sources.get(source, 0) + 1
            
            for source, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(self.articles)) * 100
                stats_text += f"{source}: {count} 篇 ({percentage:.1f}%)\n"
            stats_text += "\n"
        
        # 导出格式信息
        stats_text += "=== 导出格式信息 ===\n"
        stats_text += f"格式: {self.format_type.upper()}\n"
        stats_text += f"翻译: {'启用' if self.enable_translation else '禁用'}\n"
        
        if self.format_type == "excel":
            stats_text += "特性: 支持多工作表、格式化、图表等\n"
        elif self.format_type == "csv":
            stats_text += "特性: 纯文本格式、易于导入其他工具\n"
        elif self.format_type == "html":
            stats_text += "特性: 网页格式、支持样式和链接\n"
        elif self.format_type == "json":
            stats_text += "特性: 结构化数据、易于程序处理\n"
        
        self.stats_text.insert(tk.END, stats_text)
    
    def refresh_preview(self):
        """刷新预览"""
        if not self.loading:
            self.load_preview_data()
    
    def on_close(self):
        """关闭对话框"""
        if self.dialog:
            self.dialog.destroy()