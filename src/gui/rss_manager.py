"""
RSS管理界面模块
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading

from typing import List, Optional
from datetime import datetime

from ..services.custom_rss_service import CustomRSSService
from ..models.rss import RSSFeed


class RSSManager:
    """RSS管理界面"""

    def __init__(self, parent_frame: ttk.Frame, article_callback=None, auth=None, subscription_callback=None):
        self.parent_frame = parent_frame
        self.custom_rss_service = CustomRSSService()
        self.article_callback = article_callback  # 回调函数，用于通知主窗口更新文章列表
        self.auth = auth  # 认证信息
        self.subscription_callback = subscription_callback  # 回调函数，用于通知主窗口订阅源选择变化

        # 数据
        self.current_rss_feeds: List[RSSFeed] = []
        self.selected_feed: Optional[RSSFeed] = None

        # 创建RSS管理界面
        self.create_rss_interface()

        # 初始化数据
        self.refresh_rss_feed_list()
    
    def create_rss_interface(self):
        """创建RSS管理界面"""
        # 只创建RSS订阅源管理面板
        self.create_feed_management_panel()
    
    def create_feed_management_panel(self):
        """创建RSS订阅源管理面板"""
        # 直接在父框架中创建内容
        main_frame = self.parent_frame

        # 标题
        ttk.Label(main_frame, text="RSS订阅源", font=("Arial", 12, "bold")).pack(pady=(0, 5))

        # 使用提示
        tip_frame = ttk.Frame(main_frame)
        tip_frame.pack(fill=tk.X, pady=(0, 5))

        tip_label = ttk.Label(tip_frame,
                             text="💡 提示：选择RSS订阅源后，在右侧文章列表中右键点击文章进行筛选测试",
                             font=("Arial", 9),
                             foreground="gray")
        tip_label.pack(anchor=tk.W)

        # 搜索栏
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(search_frame, text="清除", command=self.clear_search).pack(side=tk.LEFT, padx=(0, 10))
        
        # 搜索提示
        search_tip = ttk.Label(search_frame, text="💡 支持按标题、分类、URL搜索", 
                              font=("Arial", 8), foreground="gray")
        search_tip.pack(side=tk.LEFT, padx=(10, 0))
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="添加RSS", command=self.add_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="编辑", command=self.edit_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="启用/停用", command=self.toggle_feed_status).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="删除", command=self.remove_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="刷新选中", command=self.refresh_selected_feed).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="全部刷新", command=self.refresh_all_feeds).pack(side=tk.LEFT, padx=(0, 5))

        # 时间范围筛选
        ttk.Label(toolbar, text="时间范围:").pack(side=tk.LEFT, padx=(10, 5))
        self.time_range_var = tk.StringVar(value="全部")
        time_range_combo = ttk.Combobox(toolbar, textvariable=self.time_range_var,
                                       values=["全部", "最近1小时", "最近1天", "最近7天", "最近30天"],
                                       state="readonly", width=12)
        time_range_combo.pack(side=tk.LEFT, padx=(0, 5))
        time_range_combo.bind("<<ComboboxSelected>>", self.on_time_range_changed)
        
        # RSS订阅源列表
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        self.feed_tree = ttk.Treeview(tree_frame, columns=("title", "category", "unread", "status"), show="tree headings")
        self.feed_tree.heading("#0", text="")
        self.feed_tree.heading("title", text="标题")
        self.feed_tree.heading("category", text="分类")
        self.feed_tree.heading("unread", text="未读")
        self.feed_tree.heading("status", text="状态")
        
        # 设置列宽
        self.feed_tree.column("#0", width=30)
        self.feed_tree.column("title", width=200)
        self.feed_tree.column("category", width=80)
        self.feed_tree.column("unread", width=50)
        self.feed_tree.column("status", width=60)
        
        # 滚动条
        feed_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.feed_tree.yview)
        self.feed_tree.configure(yscrollcommand=feed_scrollbar.set)
        
        self.feed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        feed_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.feed_tree.bind("<<TreeviewSelect>>", self.on_feed_select)
        self.feed_tree.bind("<Button-3>", self.show_feed_context_menu)  # 右键菜单
        self.feed_tree.bind("<Button-1>", self.on_main_header_click)
        
        # 主列表排序状态
        self.main_sort_column = None
        self.main_sort_reverse = False
    

    
    def add_rss_subscription(self):
        """添加RSS订阅"""
        dialog = RSSAddDialog(self.parent_frame)
        if dialog.result:
            url, category = dialog.result
            
            def add_subscription():
                try:
                    success, message = self.custom_rss_service.add_subscription(url, category)
                    
                    # 在主线程中更新UI
                    self.parent_frame.after(0, lambda: self._handle_add_result(success, message))
                except Exception as e:
                    self.parent_frame.after(0, lambda: messagebox.showerror("错误", f"添加RSS订阅失败: {e}"))
            
            # 在后台线程中执行
            threading.Thread(target=add_subscription, daemon=True).start()
    
    def _handle_add_result(self, success: bool, message: str):
        """处理添加结果"""
        if success:
            messagebox.showinfo("成功", message)
            self.refresh_rss_feed_list()
        else:
            messagebox.showerror("失败", message)
    
    def remove_rss_subscription(self):
        """删除RSS订阅"""
        selection = self.feed_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要删除的RSS订阅源")
            return
        
        item = selection[0]
        values = self.feed_tree.item(item)["values"]
        if not values:
            return
        
        # 通过标题查找对应的feed对象
        feed_title = values[0]  # 第一列是标题
        feed = None
        for f in self.current_rss_feeds:
            if f.title == feed_title:
                feed = f
                break
        
        if not feed:
            messagebox.showerror("错误", "未找到对应的RSS订阅源")
            return
        
        # 确认删除
        if messagebox.askyesno("确认删除", f"确定要删除RSS订阅源 '{feed.title}' 吗？"):
            success, message = self.custom_rss_service.remove_subscription(feed.id)
            
            if success:
                messagebox.showinfo("成功", message)
                self.refresh_rss_feed_list()
                # 清除选中状态
                self.selected_feed = None
                if hasattr(self, 'current_rss_articles'):
                    self.current_rss_articles.clear()
                if hasattr(self, 'update_article_list'):
                    self.update_article_list()
            else:
                messagebox.showerror("失败", message)
    
    def refresh_selected_feed(self):
        """刷新选中的订阅源"""
        if not self.selected_feed:
            messagebox.showwarning("警告", "请先选择要刷新的RSS订阅源")
            return
        
        def refresh_feed():
            try:
                success, message, new_count = self.custom_rss_service.refresh_feed(self.selected_feed.id)
                
                # 在主线程中更新UI
                self.parent_frame.after(0, lambda: self._handle_refresh_result(success, message, new_count))
            except Exception as e:
                self.parent_frame.after(0, lambda: messagebox.showerror("错误", f"刷新失败: {e}"))
        
        # 在后台线程中执行
        threading.Thread(target=refresh_feed, daemon=True).start()
    
    def _handle_refresh_result(self, success: bool, message: str, new_count: int):
        """处理刷新结果"""
        if success:
            messagebox.showinfo("刷新完成", f"{message}")
            self.refresh_rss_feed_list()
            if self.selected_feed:
                self.load_feed_articles(self.selected_feed)
        else:
            messagebox.showerror("刷新失败", message)
    
    def refresh_all_feeds(self):
        """刷新所有订阅源"""
        active_feeds = self.custom_rss_service.get_active_subscriptions()
        if not active_feeds:
            messagebox.showinfo("提示", "没有激活的RSS订阅源")
            return
        
        def refresh_all():
            try:
                results = self.custom_rss_service.refresh_all_feeds()
                
                # 统计结果
                success_count = sum(1 for success, _, _ in results.values() if success)
                total_new_articles = sum(count for _, _, count in results.values())
                
                message = f"刷新完成！\n成功: {success_count}/{len(results)}\n新文章: {total_new_articles} 篇"
                
                # 在主线程中更新UI
                self.parent_frame.after(0, lambda: self._handle_refresh_all_result(message))
            except Exception as e:
                self.parent_frame.after(0, lambda: messagebox.showerror("错误", f"批量刷新失败: {e}"))
        
        # 在后台线程中执行
        threading.Thread(target=refresh_all, daemon=True).start()
    
    def _handle_refresh_all_result(self, message: str):
        """处理批量刷新结果"""
        messagebox.showinfo("批量刷新完成", message)
        self.refresh_rss_feed_list()
        if self.selected_feed:
            self.load_feed_articles(self.selected_feed)

    def on_time_range_changed(self, event):
        """时间范围变化处理"""
        if self.selected_feed and self.article_callback:
            # 立即应用时间范围筛选并更新文章列表
            filtered_articles = self.filter_articles_by_time_range(self.selected_feed.articles)
            title = self.get_article_list_title(self.selected_feed, filtered_articles)
            self.article_callback(filtered_articles, title)

    def load_feed_articles(self, feed):
        """加载订阅源文章（应用时间范围筛选）"""
        if self.article_callback:
            filtered_articles = self.filter_articles_by_time_range(feed.articles)
            title = self.get_article_list_title(feed, filtered_articles)
            self.article_callback(filtered_articles, title)

    def get_article_list_title(self, feed, filtered_articles):
        """生成文章列表标题，包含筛选信息"""
        time_range = self.time_range_var.get()
        total_count = len(feed.articles)
        filtered_count = len(filtered_articles)

        if time_range == "全部":
            return f"RSS: {feed.title} ({total_count} 篇)"
        else:
            return f"RSS: {feed.title} ({time_range}: {filtered_count}/{total_count} 篇)"

    def get_time_range_hours(self):
        """获取时间范围对应的小时数"""
        time_range = self.time_range_var.get()
        if time_range == "最近1小时":
            return 1
        elif time_range == "最近1天":
            return 24
        elif time_range == "最近7天":
            return 24 * 7
        elif time_range == "最近30天":
            return 24 * 30
        else:  # "全部"
            return None

    def filter_articles_by_time_range(self, articles):
        """根据时间范围筛选文章"""
        hours = self.get_time_range_hours()
        if hours is None:
            return articles

        from datetime import datetime, timedelta
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered_articles = []
        for article in articles:
            # 检查文章发布时间
            if hasattr(article, 'published') and article.published:
                # 如果published是datetime对象
                if isinstance(article.published, datetime):
                    article_time = article.published
                else:
                    # 如果是字符串，尝试解析
                    try:
                        from dateutil import parser
                        article_time = parser.parse(str(article.published))
                    except:
                        # 解析失败，包含在结果中
                        filtered_articles.append(article)
                        continue

                # 移除时区信息进行比较
                if article_time.tzinfo is not None:
                    article_time = article_time.replace(tzinfo=None)

                if article_time >= cutoff_time:
                    filtered_articles.append(article)
            else:
                # 没有发布时间信息，包含在结果中
                filtered_articles.append(article)

        return filtered_articles

    def on_feed_select(self, event):
        """RSS订阅源选择事件"""
        selection = self.feed_tree.selection()
        if not selection:
            self.selected_feed = None
            # 通知主窗口清除订阅源选择
            if self.subscription_callback:
                self.subscription_callback(None)
            return

        item = selection[0]
        values = self.feed_tree.item(item)["values"]
        if not values:
            return

        # 获取选中的订阅源
        feed_title = values[0] if len(values) > 0 else ""
        for feed in self.current_rss_feeds:
            if feed.title == feed_title:
                self.selected_feed = feed
                # 通过回调通知主窗口更新订阅源选择
                if self.subscription_callback:
                    self.subscription_callback(feed)
                # 通过回调通知主窗口更新文章列表（应用时间范围筛选）
                if self.article_callback:
                    filtered_articles = self.filter_articles_by_time_range(feed.articles)
                    title = self.get_article_list_title(feed, filtered_articles)
                    self.article_callback(filtered_articles, title)
                break



    def refresh_rss_feed_list(self):
        """刷新RSS订阅源列表"""
        self.current_rss_feeds = self.custom_rss_service.get_all_subscriptions()
        self.update_feed_list()

    def update_feed_list(self):
        """更新订阅源列表显示"""
        # 清空现有项目
        for item in self.feed_tree.get_children():
            self.feed_tree.delete(item)

        # 获取搜索关键词
        search_keyword = getattr(self, 'search_var', None)
        search_text = search_keyword.get().lower().strip() if search_keyword else ""
        
        # 筛选订阅源（根据搜索条件过滤）
        filtered_feeds = []
        for feed in self.current_rss_feeds:
            # 如果有搜索条件，进行过滤
            if search_text:
                if not self._match_search_criteria(feed, search_text):
                    continue
            filtered_feeds.append(feed)
        
        # 排序
        if self.main_sort_column:
            if self.main_sort_column == "title":
                filtered_feeds.sort(key=lambda x: x.title.lower(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "category":
                filtered_feeds.sort(key=lambda x: x.category.lower(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "unread":
                filtered_feeds.sort(key=lambda x: x.get_unread_count(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "status":
                filtered_feeds.sort(key=lambda x: x.is_active, reverse=self.main_sort_reverse)
        
        # 添加订阅源到树形控件
        for feed in filtered_feeds:
            status = "激活" if feed.is_active else "停用"
            unread_count = feed.get_unread_count()

            self.feed_tree.insert("", "end", values=(
                feed.title,
                feed.category,
                unread_count,
                status
            ))

    def edit_rss_subscription(self):
        """编辑RSS订阅"""
        if not self.selected_feed:
            messagebox.showwarning("提示", "请先选择要编辑的RSS订阅源")
            return

        dialog = RSSEditDialog(self.parent_frame, self.selected_feed)
        if dialog.result:
            # 更新RSS订阅
            success, message = self.custom_rss_service.update_subscription(
                self.selected_feed.id,
                dialog.result['url'],
                dialog.result['category']
            )

            if success:
                messagebox.showinfo("成功", "RSS订阅更新成功")
                self.refresh_rss_feed_list()
            else:
                messagebox.showerror("错误", f"更新RSS订阅失败: {message}")

    def toggle_feed_status(self):
        """切换RSS订阅源状态（启用/停用）"""
        if not self.selected_feed:
            messagebox.showwarning("提示", "请先选择要操作的RSS订阅源")
            return

        # 切换状态
        new_status = not self.selected_feed.is_active
        success = self.custom_rss_service.subscription_manager.set_feed_active(
            self.selected_feed.id, new_status
        )

        if success:
            status_text = "启用" if new_status else "停用"
            messagebox.showinfo("成功", f"已{status_text}RSS订阅源: {self.selected_feed.title}")
            self.refresh_rss_feed_list()
        else:
            messagebox.showerror("错误", "状态切换失败")

    def show_feed_context_menu(self, event):
        """显示订阅源右键菜单"""
        # TODO: 实现右键菜单
        pass
    
    def on_main_header_click(self, event):
        """主列表列标题点击事件"""
        region = self.feed_tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.feed_tree.identify_column(event.x)
            self.sort_main_list_by_column(column)
    
    def sort_main_list_by_column(self, column):
        """主列表按列排序"""
        # 确定排序列和对应的属性
        if column == "#1":  # 标题列
            sort_key = "title"
            column_name = "title"
        elif column == "#2":  # 分类列
            sort_key = "category"
            column_name = "category"
        elif column == "#3":  # 未读列
            sort_key = "unread"
            column_name = "unread"
        elif column == "#4":  # 状态列
            sort_key = "status"
            column_name = "status"
        else:
            return
        
        # 如果点击的是同一列，则反转排序
        if self.main_sort_column == sort_key:
            self.main_sort_reverse = not self.main_sort_reverse
        else:
            self.main_sort_column = sort_key
            self.main_sort_reverse = False
        
        # 更新主列表列标题显示排序指示器
        self.update_main_column_headers()
        
        # 重新更新列表（带排序）
        self.update_feed_list()
    
    def update_main_column_headers(self):
        """更新主列表列标题显示排序指示器"""
        # 清除所有列的排序指示器
        self.feed_tree.heading("title", text="标题")
        self.feed_tree.heading("category", text="分类")
        self.feed_tree.heading("unread", text="未读")
        self.feed_tree.heading("status", text="状态")
        
        # 为当前排序列添加指示器
        if self.main_sort_column:
            arrow = " ↓" if self.main_sort_reverse else " ↑"
            if self.main_sort_column == "title":
                self.feed_tree.heading("title", text="标题" + arrow)
            elif self.main_sort_column == "category":
                self.feed_tree.heading("category", text="分类" + arrow)
            elif self.main_sort_column == "unread":
                self.feed_tree.heading("unread", text="未读" + arrow)
            elif self.main_sort_column == "status":
                self.feed_tree.heading("status", text="状态" + arrow)
    
    def on_search_change(self, *args):
        """搜索框内容变化事件"""
        self.update_feed_list()
    
    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
    
    def _match_search_criteria(self, feed, search_text):
        """检查RSS订阅源是否匹配搜索条件"""
        # 在标题中搜索
        if search_text in feed.title.lower():
            return True
        
        # 在分类中搜索
        if search_text in feed.category.lower():
            return True
        
        # 在URL中搜索
        if search_text in feed.url.lower():
            return True
        
        # 在描述中搜索（如果有）
        if hasattr(feed, 'description') and feed.description:
            if search_text in feed.description.lower():
                return True
        
        return False

    def _handle_import_result(self, success_count: int, total_count: int):
        """处理导入结果"""
        if success_count > 0:
            messagebox.showinfo("导入完成", f"成功导入 {success_count}/{total_count} 个RSS源")
            self.refresh_rss_feed_list()
        else:
            messagebox.showwarning("导入失败", "没有成功导入任何RSS源，可能已存在相同的源")


class RSSAddDialog:
    """RSS添加对话框"""

    def __init__(self, parent):
        self.result = None

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加RSS订阅")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        self.create_widgets()

        # 等待对话框关闭
        self.dialog.wait_window()

    def create_widgets(self):
        """创建对话框组件"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # RSS URL输入
        ttk.Label(main_frame, text="RSS URL:").pack(anchor=tk.W)
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=50)
        url_entry.pack(fill=tk.X, pady=(5, 15))
        url_entry.focus()

        # 分类输入
        ttk.Label(main_frame, text="分类:").pack(anchor=tk.W)
        self.category_var = tk.StringVar(value="默认")
        category_entry = ttk.Entry(main_frame, textvariable=self.category_var, width=50)
        category_entry.pack(fill=tk.X, pady=(5, 20))

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="确定", command=self.ok).pack(side=tk.RIGHT)

        # 绑定回车键
        self.dialog.bind("<Return>", lambda e: self.ok())
        self.dialog.bind("<Escape>", lambda e: self.cancel())

    def ok(self):
        """确定按钮"""
        url = self.url_var.get().strip()
        category = self.category_var.get().strip()

        if not url:
            messagebox.showerror("错误", "请输入RSS URL", parent=self.dialog)
            return

        if not category:
            category = "默认"

        self.result = (url, category)
        self.dialog.destroy()

    def cancel(self):
        """取消按钮"""
        self.dialog.destroy()


class RSSEditDialog:
    """RSS订阅编辑对话框"""

    def __init__(self, parent, feed):
        self.result = None
        self.feed = feed

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑RSS订阅")
        self.dialog.geometry("500x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 居中显示
        self.dialog.geometry("+%d+%d" % (
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        self.create_widgets()

        # 等待对话框关闭
        self.dialog.wait_window()

    def create_widgets(self):
        """创建对话框组件"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 标题
        ttk.Label(main_frame, text="编辑RSS订阅", font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # RSS URL
        ttk.Label(main_frame, text="RSS URL:").pack(anchor=tk.W)
        self.url_var = tk.StringVar(value=self.feed.url)
        url_entry = ttk.Entry(main_frame, textvariable=self.url_var, width=60)
        url_entry.pack(fill=tk.X, pady=(5, 15))

        # 分类
        ttk.Label(main_frame, text="分类:").pack(anchor=tk.W)
        self.category_var = tk.StringVar(value=self.feed.category)
        category_entry = ttk.Entry(main_frame, textvariable=self.category_var, width=60)
        category_entry.pack(fill=tk.X, pady=(5, 15))

        # 标题（只读）
        ttk.Label(main_frame, text="标题:").pack(anchor=tk.W)
        title_entry = ttk.Entry(main_frame, width=60, state="readonly")
        title_entry.insert(0, self.feed.title)
        title_entry.pack(fill=tk.X, pady=(5, 15))

        # 描述（只读）
        ttk.Label(main_frame, text="描述:").pack(anchor=tk.W)
        desc_text = tk.Text(main_frame, height=4, width=60, state="disabled")
        desc_text.config(state="normal")
        desc_text.insert("1.0", self.feed.description or "无描述")
        desc_text.config(state="disabled")
        desc_text.pack(fill=tk.X, pady=(5, 20))

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.RIGHT)

        # 绑定快捷键
        self.dialog.bind("<Return>", lambda e: self.save())
        self.dialog.bind("<Escape>", lambda e: self.cancel())

        # 焦点设置到URL输入框
        url_entry.focus()
        url_entry.select_range(0, tk.END)

    def save(self):
        """保存按钮"""
        url = self.url_var.get().strip()
        category = self.category_var.get().strip()

        if not url:
            messagebox.showerror("错误", "请输入RSS URL", parent=self.dialog)
            return

        self.result = {
            'url': url,
            'category': category or "默认"
        }
        self.dialog.destroy()

    def cancel(self):
        """取消按钮"""
        self.dialog.destroy()
