"""
批量筛选结果展示对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from typing import Optional

from ..filters.base import BatchFilterResult, CombinedFilterResult
from ..utils.result_formatter import ResultFormatter, ResultExporter


class BatchFilterResultDialog:
    """批量筛选结果展示对话框"""

    def __init__(self, parent, result: BatchFilterResult):
        self.parent = parent
        self.result = result
        self.dialog = None

        # 界面组件
        self.notebook = None
        self.summary_text = None
        self.subscription_tree = None
        self.article_tree = None
        self.detail_text = None

        # 当前选中的文章
        self.current_article: Optional[CombinedFilterResult] = None

        # 文章对象存储（因为Treeview不能直接存储Python对象）
        self.article_objects = {}  # item_id -> CombinedFilterResult

        # 显示选项
        self.group_by_subscription_var = tk.BooleanVar(value=True)
        self.show_details_var = tk.BooleanVar(value=True)
    
    def show(self):
        """显示结果对话框"""
        self.create_dialog()
        
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"批量筛选结果 - 共筛选出 {self.result.total_articles_selected} 篇文章")
        self.dialog.geometry("1000x700")
        self.dialog.resizable(True, True)
        
        # 设置为模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建界面
        self.create_widgets()
        
        # 加载数据
        self.load_data()
    
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
        
        # 工具栏
        self.create_toolbar(main_frame)
        
        # 创建标签页
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 摘要标签页
        self.create_summary_tab()
        
        # 订阅源结果标签页
        self.create_subscription_tab()
        
        # 文章列表标签页
        self.create_article_tab()
        
        # 文章详情标签页
        self.create_detail_tab()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="导出JSON", command=self.export_json).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导出CSV", command=self.export_csv).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="关闭", command=self.close).pack(side=tk.RIGHT)
    
    def create_toolbar(self, parent):
        """创建工具栏"""
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        # 显示选项
        ttk.Label(toolbar, text="显示选项:").pack(side=tk.LEFT)
        
        ttk.Checkbutton(toolbar, text="按订阅源分组", 
                       variable=self.group_by_subscription_var,
                       command=self.refresh_article_list).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Checkbutton(toolbar, text="显示详细信息", 
                       variable=self.show_details_var,
                       command=self.refresh_subscription_list).pack(side=tk.LEFT, padx=(10, 0))
        
        # 统计信息
        stats_text = f"处理订阅源: {self.result.processed_subscriptions}/{self.result.total_subscriptions} | "
        stats_text += f"获取文章: {self.result.total_articles_fetched} | "
        stats_text += f"筛选文章: {self.result.total_articles_selected} | "
        stats_text += f"耗时: {self.result.total_processing_time:.2f}秒"
        
        ttk.Label(toolbar, text=stats_text, foreground="gray").pack(side=tk.RIGHT)
    
    def create_summary_tab(self):
        """创建摘要标签页"""
        summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(summary_frame, text="摘要")
        
        # 创建滚动文本框
        text_frame = ttk.Frame(summary_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.summary_text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED)
        summary_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        
        self.summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_subscription_tab(self):
        """创建订阅源结果标签页"""
        sub_frame = ttk.Frame(self.notebook)
        self.notebook.add(sub_frame, text="订阅源结果")
        
        # 创建树形视图
        tree_frame = ttk.Frame(sub_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("title", "fetched", "selected", "time", "success_rate")
        self.subscription_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # 设置列标题
        self.subscription_tree.heading("title", text="订阅源")
        self.subscription_tree.heading("fetched", text="获取文章")
        self.subscription_tree.heading("selected", text="筛选文章")
        self.subscription_tree.heading("time", text="处理时间")
        self.subscription_tree.heading("success_rate", text="筛选率")
        
        # 设置列宽
        self.subscription_tree.column("title", width=300)
        self.subscription_tree.column("fetched", width=80, anchor=tk.CENTER)
        self.subscription_tree.column("selected", width=80, anchor=tk.CENTER)
        self.subscription_tree.column("time", width=80, anchor=tk.CENTER)
        self.subscription_tree.column("success_rate", width=80, anchor=tk.CENTER)
        
        # 滚动条
        sub_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.subscription_tree.yview)
        self.subscription_tree.configure(yscrollcommand=sub_scrollbar.set)
        
        self.subscription_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sub_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_article_tab(self):
        """创建文章列表标签页"""
        article_frame = ttk.Frame(self.notebook)
        self.notebook.add(article_frame, text="文章列表")
        
        # 创建树形视图
        tree_frame = ttk.Frame(article_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("title", "source", "score", "published", "type")
        self.article_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        # 设置列标题
        self.article_tree.heading("title", text="标题")
        self.article_tree.heading("source", text="来源")
        self.article_tree.heading("score", text="分数")
        self.article_tree.heading("published", text="发布时间")
        self.article_tree.heading("type", text="筛选类型")
        
        # 设置列宽
        self.article_tree.column("title", width=400)
        self.article_tree.column("source", width=150)
        self.article_tree.column("score", width=80, anchor=tk.CENTER)
        self.article_tree.column("published", width=120, anchor=tk.CENTER)
        self.article_tree.column("type", width=80, anchor=tk.CENTER)
        
        # 滚动条
        article_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.article_tree.yview)
        self.article_tree.configure(yscrollcommand=article_scrollbar.set)
        
        self.article_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        article_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.article_tree.bind("<<TreeviewSelect>>", self.on_article_select)
        self.article_tree.bind("<Double-1>", self.on_article_double_click)
    
    def create_detail_tab(self):
        """创建文章详情标签页"""
        detail_frame = ttk.Frame(self.notebook)
        self.notebook.add(detail_frame, text="文章详情")
        
        # 创建滚动文本框
        text_frame = ttk.Frame(detail_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.detail_text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED)
        detail_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)
        
        self.detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 操作按钮
        button_frame = ttk.Frame(detail_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        ttk.Button(button_frame, text="打开原文", command=self.open_article_url).pack(side=tk.LEFT)
    
    def load_data(self):
        """加载数据"""
        self.load_summary()
        self.load_subscription_results()
        self.load_article_list()
    
    def load_summary(self):
        """加载摘要信息"""
        summary = ResultFormatter.format_batch_summary(self.result)
        
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary)
        self.summary_text.config(state=tk.DISABLED)
    
    def load_subscription_results(self):
        """加载订阅源结果"""
        # 清空现有数据
        for item in self.subscription_tree.get_children():
            self.subscription_tree.delete(item)
        
        # 添加订阅源结果
        for sub_result in self.result.subscription_results:
            success_rate = 0
            if sub_result.articles_fetched > 0:
                success_rate = (sub_result.selected_count / sub_result.articles_fetched) * 100
            
            self.subscription_tree.insert("", tk.END, values=(
                sub_result.subscription_title,
                sub_result.articles_fetched,
                sub_result.selected_count,
                f"{sub_result.total_processing_time:.2f}s",
                f"{success_rate:.1f}%"
            ))
    
    def load_article_list(self):
        """加载文章列表"""
        # 清空现有数据
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

        # 清空文章对象存储
        self.article_objects.clear()

        # 获取所有文章
        all_articles = self.result.all_selected_articles

        if not all_articles:
            # 如果没有文章，显示提示信息
            self.article_tree.insert("", tk.END, values=(
                "没有筛选出任何文章", "", "", "", ""
            ))
            return

        # 按分数排序
        all_articles.sort(key=lambda x: x.final_score, reverse=True)

        # 添加文章
        if self.group_by_subscription_var.get():
            self.load_articles_grouped(all_articles)
        else:
            self.load_articles_flat(all_articles)
    
    def load_articles_grouped(self, articles):
        """按订阅源分组加载文章"""
        # 按订阅源分组
        subscription_groups = {}
        for article in articles:
            source = article.article.feed_title or "未知来源"
            if source not in subscription_groups:
                subscription_groups[source] = []
            subscription_groups[source].append(article)



        # 添加分组
        for source, group_articles in subscription_groups.items():
            # 添加分组标题
            group_item = self.article_tree.insert("", tk.END, values=(
                f"📰 {source} ({len(group_articles)}篇)",
                "", "", "", ""
            ), tags=("group",))

            # 添加文章
            for article in group_articles:
                self.add_article_item(group_item, article)

        # 展开所有分组
        for item in self.article_tree.get_children():
            self.article_tree.item(item, open=True)
    
    def load_articles_flat(self, articles):
        """平铺加载文章"""
        for article in articles:
            self.add_article_item("", article)
    
    def add_article_item(self, parent, article: CombinedFilterResult):
        """添加文章项"""
        # 确定筛选类型
        filter_type = ""
        if article.keyword_result and article.ai_result:
            filter_type = "综合"
        elif article.keyword_result:
            filter_type = "关键词"
        elif article.ai_result:
            filter_type = "AI"

        # 格式化发布时间
        published_str = article.article.published.strftime("%m-%d %H:%M")

        item = self.article_tree.insert(parent, tk.END, values=(
            article.article.title[:80] + "..." if len(article.article.title) > 80 else article.article.title,
            article.article.feed_title or "未知来源",
            f"{article.final_score:.2f}",
            published_str,
            filter_type
        ))

        # 存储文章对象到字典中（使用item作为key）
        self.article_objects[item] = article
    
    def refresh_subscription_list(self):
        """刷新订阅源列表"""
        self.load_subscription_results()
    
    def refresh_article_list(self):
        """刷新文章列表"""
        self.load_article_list()
    
    def on_article_select(self, event):
        """文章选择事件"""
        selection = self.article_tree.selection()
        if not selection:
            return

        item = selection[0]

        # 从字典中获取文章对象
        article_obj = self.article_objects.get(item)

        if article_obj and hasattr(article_obj, 'article'):
            self.current_article = article_obj
            self.show_article_detail(article_obj)
        else:
            # 可能是分组标题，不是文章项
            self.current_article = None
    
    def on_article_double_click(self, event):
        """文章双击事件"""
        if self.current_article:
            self.open_article_url()
    
    def show_article_detail(self, article: CombinedFilterResult):
        """显示文章详情"""
        detail_content = f"标题: {article.article.title}\n\n"
        detail_content += f"来源: {article.article.feed_title}\n"
        detail_content += f"发布时间: {article.article.published.strftime('%Y-%m-%d %H:%M:%S')}\n"
        detail_content += f"最终分数: {article.final_score:.2f}\n"
        
        if article.keyword_result:
            detail_content += f"关键词分数: {article.keyword_result.relevance_score:.2f}\n"
        
        if article.ai_result:
            detail_content += f"AI分数: {article.ai_result.evaluation.total_score}\n"
            detail_content += f"AI评估理由: {article.ai_result.evaluation.reasoning}\n"
        
        detail_content += f"\nURL: {article.article.url}\n\n"
        detail_content += f"摘要:\n{article.article.summary}\n\n"
        detail_content += f"内容:\n{article.article.content}"
        
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(1.0, detail_content)
        self.detail_text.config(state=tk.DISABLED)
        
        # 切换到详情标签页
        self.notebook.select(3)
    
    def open_article_url(self):
        """打开文章URL"""
        if self.current_article and self.current_article.article.url:
            webbrowser.open(self.current_article.article.url)
    
    def export_json(self):
        """导出JSON"""
        filename = filedialog.asksaveasfilename(
            title="导出JSON",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                json_content = ResultFormatter.export_to_json(self.result, include_content=True)
                ResultExporter.save_to_file(json_content, filename)
                messagebox.showinfo("成功", f"JSON文件已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出JSON失败: {e}")
    
    def export_csv(self):
        """导出CSV"""
        filename = filedialog.asksaveasfilename(
            title="导出CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                csv_content = ResultFormatter.export_to_csv(self.result)
                ResultExporter.save_to_file(csv_content, filename, encoding="utf-8-sig")  # 使用BOM以支持Excel
                messagebox.showinfo("成功", f"CSV文件已导出到: {filename}")
            except Exception as e:
                messagebox.showerror("错误", f"导出CSV失败: {e}")
    
    def close(self):
        """关闭对话框"""
        if self.dialog:
            self.dialog.destroy()
