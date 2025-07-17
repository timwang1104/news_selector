"""
主窗口界面
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from typing import List, Optional

from ..api.auth import InoreaderAuth
from ..services.news_service import NewsService
from ..services.subscription_service import SubscriptionService
from ..models.news import NewsArticle
from ..models.subscription import Subscription
from .login_dialog import LoginDialog


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("新闻订阅工具 - News Selector")
        self.root.geometry("1200x800")
        
        # 服务实例
        self.auth = InoreaderAuth()
        self.news_service = NewsService()
        self.subscription_service = SubscriptionService()
        
        # 数据
        self.current_articles: List[NewsArticle] = []
        self.current_subscriptions: List[Subscription] = []
        
        # 创建界面
        self.create_widgets()
        self.update_login_status()
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建菜单栏
        self.create_menu()
        
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左侧面板（订阅源列表）
        self.create_left_panel(main_frame)
        
        # 创建右侧面板（文章列表和详情）
        self.create_right_panel(main_frame)
        
        # 创建状态栏
        self.create_status_bar()
    
    def create_menu(self):
        """创建菜单栏"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 文件菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="登录", command=self.login)
        file_menu.add_command(label="登出", command=self.logout)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 查看菜单
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="查看", menu=view_menu)
        view_menu.add_command(label="刷新新闻", command=self.refresh_news)
        view_menu.add_command(label="刷新订阅源", command=self.refresh_subscriptions)
        view_menu.add_command(label="显示统计", command=self.show_statistics)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_left_panel(self, parent):
        """创建左侧面板"""
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))
        
        # 订阅源标题
        ttk.Label(left_frame, text="订阅源", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # 搜索框
        search_frame = ttk.Frame(left_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        search_entry.bind('<Return>', self.search_subscriptions)
        
        # 订阅源列表
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview用于显示订阅源
        columns = ("title", "unread")
        self.subscription_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", height=15)
        
        # 设置列
        self.subscription_tree.heading("#0", text="订阅源")
        self.subscription_tree.heading("title", text="标题")
        self.subscription_tree.heading("unread", text="未读")
        
        self.subscription_tree.column("#0", width=200)
        self.subscription_tree.column("title", width=150)
        self.subscription_tree.column("unread", width=50)
        
        # 添加滚动条
        sub_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.subscription_tree.yview)
        self.subscription_tree.configure(yscrollcommand=sub_scrollbar.set)
        
        self.subscription_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sub_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.subscription_tree.bind("<<TreeviewSelect>>", self.on_subscription_select)
        
        # 按钮框架
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="刷新订阅源", command=self.refresh_subscriptions).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(button_frame, text="获取最新新闻", command=self.refresh_news).pack(fill=tk.X)
    
    def create_right_panel(self, parent):
        """创建右侧面板"""
        right_frame = ttk.Frame(parent)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 文章列表标签页
        self.create_articles_tab()
        
        # 文章详情标签页
        self.create_article_detail_tab()
    
    def create_articles_tab(self):
        """创建文章列表标签页"""
        articles_frame = ttk.Frame(self.notebook)
        self.notebook.add(articles_frame, text="文章列表")
        
        # 工具栏
        toolbar = ttk.Frame(articles_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        # 过滤选项
        ttk.Label(toolbar, text="显示:").pack(side=tk.LEFT)
        
        self.filter_var = tk.StringVar(value="all")
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Radiobutton(filter_frame, text="全部", variable=self.filter_var, 
                       value="all", command=self.filter_articles).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="未读", variable=self.filter_var, 
                       value="unread", command=self.filter_articles).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(filter_frame, text="星标", variable=self.filter_var, 
                       value="starred", command=self.filter_articles).pack(side=tk.LEFT, padx=(10, 0))
        
        # 文章搜索
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        
        ttk.Label(search_frame, text="搜索文章:").pack(side=tk.LEFT)
        self.article_search_var = tk.StringVar()
        article_search_entry = ttk.Entry(search_frame, textvariable=self.article_search_var, width=20)
        article_search_entry.pack(side=tk.LEFT, padx=(5, 0))
        article_search_entry.bind('<Return>', self.search_articles)
        
        # 文章列表
        list_frame = ttk.Frame(articles_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview用于显示文章
        columns = ("title", "feed", "date", "status")
        self.article_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列
        self.article_tree.heading("title", text="标题")
        self.article_tree.heading("feed", text="来源")
        self.article_tree.heading("date", text="日期")
        self.article_tree.heading("status", text="状态")
        
        self.article_tree.column("title", width=400)
        self.article_tree.column("feed", width=150)
        self.article_tree.column("date", width=120)
        self.article_tree.column("status", width=80)
        
        # 添加滚动条
        article_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.article_tree.yview)
        self.article_tree.configure(yscrollcommand=article_scrollbar.set)
        
        self.article_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        article_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定双击事件
        self.article_tree.bind("<Double-1>", self.on_article_double_click)
        
        # 右键菜单
        self.create_article_context_menu()
    
    def create_article_detail_tab(self):
        """创建文章详情标签页"""
        detail_frame = ttk.Frame(self.notebook)
        self.notebook.add(detail_frame, text="文章详情")
        
        # 文章标题
        self.article_title_label = ttk.Label(detail_frame, text="", font=("Arial", 14, "bold"), wraplength=600)
        self.article_title_label.pack(pady=(10, 5), anchor=tk.W)
        
        # 文章信息
        info_frame = ttk.Frame(detail_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.article_info_label = ttk.Label(info_frame, text="", foreground="gray")
        self.article_info_label.pack(side=tk.LEFT)
        
        # 操作按钮
        button_frame = ttk.Frame(info_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.open_url_button = ttk.Button(button_frame, text="打开原文", command=self.open_article_url)
        self.open_url_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.star_button = ttk.Button(button_frame, text="加星标", command=self.toggle_star)
        self.star_button.pack(side=tk.LEFT)
        
        # 文章内容
        self.article_content = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, height=25)
        self.article_content.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 当前显示的文章
        self.current_article: Optional[NewsArticle] = None
    
    def create_article_context_menu(self):
        """创建文章右键菜单"""
        self.article_context_menu = tk.Menu(self.root, tearoff=0)
        self.article_context_menu.add_command(label="查看详情", command=self.view_article_detail)
        self.article_context_menu.add_command(label="打开原文", command=self.open_article_url)
        self.article_context_menu.add_separator()
        self.article_context_menu.add_command(label="标记为已读", command=self.mark_as_read)
        self.article_context_menu.add_command(label="标记为未读", command=self.mark_as_unread)
        self.article_context_menu.add_separator()
        self.article_context_menu.add_command(label="加星标", command=self.toggle_star)
        
        self.article_tree.bind("<Button-3>", self.show_article_context_menu)
    
    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def update_login_status(self):
        """更新登录状态"""
        if self.auth.is_authenticated():
            self.update_status("已登录")
            self.refresh_subscriptions()
        else:
            self.update_status("未登录 - 请先登录")

    def login(self):
        """登录"""
        if self.auth.is_authenticated():
            messagebox.showinfo("提示", "您已经登录")
            return

        # 显示登录对话框
        login_dialog = LoginDialog(self.root, self.auth)
        if login_dialog.result:
            self.update_login_status()
            messagebox.showinfo("成功", "登录成功！")
        else:
            messagebox.showerror("错误", "登录失败")

    def logout(self):
        """登出"""
        if messagebox.askyesno("确认", "确定要登出吗？"):
            self.auth.logout()
            self.current_articles.clear()
            self.current_subscriptions.clear()
            self.refresh_ui()
            self.update_status("已登出")
            messagebox.showinfo("提示", "已登出")

    def refresh_subscriptions(self):
        """刷新订阅源列表"""
        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        def load_subscriptions():
            try:
                self.update_status("正在加载订阅源...")
                subscriptions_with_unread = self.subscription_service.get_subscriptions_with_unread_counts()

                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_subscription_list(subscriptions_with_unread))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载订阅源失败: {e}"))
                self.root.after(0, lambda: self.update_status("加载订阅源失败"))

        # 在后台线程中加载
        threading.Thread(target=load_subscriptions, daemon=True).start()

    def update_subscription_list(self, subscriptions_with_unread):
        """更新订阅源列表UI"""
        # 清空现有项目
        for item in self.subscription_tree.get_children():
            self.subscription_tree.delete(item)

        self.current_subscriptions.clear()

        for item in subscriptions_with_unread:
            subscription = item['subscription']
            unread_count = item['unread_count']

            self.current_subscriptions.append(subscription)

            # 添加到树形控件
            unread_text = str(unread_count) if unread_count > 0 else ""
            self.subscription_tree.insert("", tk.END,
                                        text=subscription.get_display_title(30),
                                        values=(subscription.title, unread_text))

        self.update_status(f"已加载 {len(subscriptions_with_unread)} 个订阅源")

    def refresh_news(self):
        """刷新新闻列表"""
        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        def load_news():
            try:
                self.update_status("正在加载最新新闻...")
                articles = self.news_service.get_latest_articles(count=100, exclude_read=False)

                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_article_list(articles))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载新闻失败: {e}"))
                self.root.after(0, lambda: self.update_status("加载新闻失败"))

        # 在后台线程中加载
        threading.Thread(target=load_news, daemon=True).start()

    def update_article_list(self, articles: List[NewsArticle]):
        """更新文章列表UI"""
        self.current_articles = articles
        self.filter_articles()
        self.update_status(f"已加载 {len(articles)} 篇文章")

    def filter_articles(self):
        """根据过滤条件显示文章"""
        # 清空现有项目
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

        filter_type = self.filter_var.get()

        for article in self.current_articles:
            # 应用过滤条件
            if filter_type == "unread" and article.is_read:
                continue
            elif filter_type == "starred" and not article.is_starred:
                continue

            # 状态指示
            status = []
            if not article.is_read:
                status.append("未读")
            if article.is_starred:
                status.append("★")

            status_text = " ".join(status) if status else "已读"

            # 添加到列表
            self.article_tree.insert("", tk.END, values=(
                article.get_display_title(60),
                article.feed_title or "未知",
                article.published.strftime("%m-%d %H:%M"),
                status_text
            ))

    def search_subscriptions(self, event=None):
        """搜索订阅源"""
        keyword = self.search_var.get().strip()
        if not keyword:
            self.refresh_subscriptions()
            return

        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        def search():
            try:
                self.update_status(f"正在搜索订阅源: {keyword}")
                subscriptions = self.subscription_service.search_subscriptions(keyword)

                # 转换为带未读数量的格式
                subscriptions_with_unread = []
                unread_counts = self.subscription_service.get_unread_counts()

                for sub in subscriptions:
                    subscriptions_with_unread.append({
                        'subscription': sub,
                        'unread_count': unread_counts.get(sub.id, 0)
                    })

                self.root.after(0, lambda: self.update_subscription_list(subscriptions_with_unread))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"搜索失败: {e}"))

        threading.Thread(target=search, daemon=True).start()

    def search_articles(self, event=None):
        """搜索文章"""
        keyword = self.article_search_var.get().strip()
        if not keyword:
            self.filter_articles()
            return

        if not self.current_articles:
            messagebox.showinfo("提示", "请先加载文章")
            return

        # 在当前文章中搜索
        matched_articles = self.news_service.search_articles(keyword, self.current_articles)

        # 清空现有项目
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

        # 显示搜索结果
        for article in matched_articles:
            status = []
            if not article.is_read:
                status.append("未读")
            if article.is_starred:
                status.append("★")

            status_text = " ".join(status) if status else "已读"

            self.article_tree.insert("", tk.END, values=(
                article.get_display_title(60),
                article.feed_title or "未知",
                article.published.strftime("%m-%d %H:%M"),
                status_text
            ))

        self.update_status(f"找到 {len(matched_articles)} 篇相关文章")

    def on_subscription_select(self, event):
        """订阅源选择事件"""
        selection = self.subscription_tree.selection()
        if not selection:
            return

        # 获取选中的订阅源
        item = self.subscription_tree.item(selection[0])
        subscription_title = item['values'][0]

        # 找到对应的订阅源对象
        selected_subscription = None
        for sub in self.current_subscriptions:
            if sub.title == subscription_title:
                selected_subscription = sub
                break

        if selected_subscription:
            self.load_subscription_articles(selected_subscription)

    def load_subscription_articles(self, subscription: Subscription):
        """加载指定订阅源的文章"""
        def load_articles():
            try:
                self.update_status(f"正在加载 {subscription.title} 的文章...")
                articles = self.news_service.get_articles_by_feed(
                    feed_id=subscription.id,
                    count=50,
                    exclude_read=False
                )

                self.root.after(0, lambda: self.update_article_list(articles))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载文章失败: {e}"))

        threading.Thread(target=load_articles, daemon=True).start()

    def on_article_double_click(self, event):
        """文章双击事件"""
        self.view_article_detail()

    def view_article_detail(self):
        """查看文章详情"""
        selection = self.article_tree.selection()
        if not selection:
            return

        # 获取选中的文章
        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]
            self.show_article_detail(article)

    def show_article_detail(self, article: NewsArticle):
        """显示文章详情"""
        self.current_article = article

        # 更新标题
        self.article_title_label.config(text=article.title)

        # 更新信息
        info_text = f"来源: {article.feed_title or '未知'} | 时间: {article.published.strftime('%Y-%m-%d %H:%M')}"
        if article.author:
            info_text += f" | 作者: {article.author.name}"
        self.article_info_label.config(text=info_text)

        # 更新按钮状态
        self.star_button.config(text="移除星标" if article.is_starred else "加星标")

        # 更新内容
        self.article_content.delete(1.0, tk.END)
        content = article.content or article.summary
        if content:
            self.article_content.insert(1.0, content)
        else:
            self.article_content.insert(1.0, "无内容预览，请点击'打开原文'查看完整内容。")

        # 切换到详情标签页
        self.notebook.select(1)

        # 标记为已读
        if not article.is_read:
            self.mark_article_read(article)

    def open_article_url(self):
        """打开文章原文"""
        if self.current_article and self.current_article.url:
            webbrowser.open(self.current_article.url)
        else:
            messagebox.showwarning("警告", "没有可用的文章链接")

    def toggle_star(self):
        """切换星标状态"""
        if not self.current_article:
            return

        def update_star():
            try:
                if self.current_article.is_starred:
                    success = self.news_service.unstar_article(self.current_article.id)
                    action = "移除星标"
                else:
                    success = self.news_service.star_article(self.current_article.id)
                    action = "添加星标"

                if success:
                    self.current_article.is_starred = not self.current_article.is_starred
                    self.root.after(0, lambda: self.update_star_button())
                    self.root.after(0, lambda: self.update_status(f"{action}成功"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"{action}失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"{action}失败: {e}"))

        threading.Thread(target=update_star, daemon=True).start()

    def update_star_button(self):
        """更新星标按钮"""
        if self.current_article:
            self.star_button.config(text="移除星标" if self.current_article.is_starred else "加星标")

    def mark_article_read(self, article: NewsArticle):
        """标记文章为已读"""
        def mark_read():
            try:
                if self.news_service.mark_article_as_read(article.id):
                    article.is_read = True
            except Exception:
                pass  # 静默失败

        threading.Thread(target=mark_read, daemon=True).start()

    def show_article_context_menu(self, event):
        """显示文章右键菜单"""
        # 选中右键点击的项目
        item = self.article_tree.identify_row(event.y)
        if item:
            self.article_tree.selection_set(item)
            self.article_context_menu.post(event.x_root, event.y_root)

    def mark_as_read(self):
        """标记为已读"""
        selection = self.article_tree.selection()
        if not selection:
            return

        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]

            def mark_read():
                try:
                    if self.news_service.mark_article_as_read(article.id):
                        article.is_read = True
                        self.root.after(0, self.filter_articles)
                        self.root.after(0, lambda: self.update_status("标记为已读"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "标记失败"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"标记失败: {e}"))

            threading.Thread(target=mark_read, daemon=True).start()

    def mark_as_unread(self):
        """标记为未读"""
        selection = self.article_tree.selection()
        if not selection:
            return

        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]

            def mark_unread():
                try:
                    if self.news_service.mark_article_as_unread(article.id):
                        article.is_read = False
                        self.root.after(0, self.filter_articles)
                        self.root.after(0, lambda: self.update_status("标记为未读"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "标记失败"))
                except Exception as e:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"标记失败: {e}"))

            threading.Thread(target=mark_unread, daemon=True).start()

    def show_statistics(self):
        """显示统计信息"""
        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        def load_stats():
            try:
                self.update_status("正在加载统计信息...")
                stats = self.subscription_service.get_subscription_statistics()

                self.root.after(0, lambda: self.display_statistics(stats))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"加载统计信息失败: {e}"))

        threading.Thread(target=load_stats, daemon=True).start()

    def display_statistics(self, stats):
        """显示统计信息对话框"""
        stats_window = tk.Toplevel(self.root)
        stats_window.title("统计信息")
        stats_window.geometry("500x400")
        stats_window.transient(self.root)
        stats_window.grab_set()

        # 创建滚动文本框
        text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 格式化统计信息
        content = f"""📊 订阅统计信息

📡 订阅源总数: {stats['total_subscriptions']}
📰 未读文章总数: {stats['total_unread']}

🏷️ 分类统计:
"""

        for category, data in stats['categories'].items():
            content += f"   • {category}: {data['count']} 个订阅源, {data['unread']} 篇未读\n"

        content += "\n🔥 最活跃的订阅源:\n"
        for item in stats['most_active_feeds'][:10]:
            subscription = item['subscription']
            unread_count = item['unread_count']
            if unread_count > 0:
                content += f"   • {subscription.get_display_title(40)}: {unread_count} 篇未读\n"

        text_widget.insert(1.0, content)
        text_widget.config(state=tk.DISABLED)

        # 关闭按钮
        ttk.Button(stats_window, text="关闭", command=stats_window.destroy).pack(pady=10)

        self.update_status("统计信息已显示")

    def show_about(self):
        """显示关于对话框"""
        about_text = """新闻订阅工具 v0.1.0

基于Inoreader API的新闻订阅和管理工具

功能特性:
• OAuth2认证登录
• 获取订阅源列表
• 获取最新文章
• 文章搜索和过滤
• 星标管理
• 统计信息

开发: News Selector Team
"""
        messagebox.showinfo("关于", about_text)

    def refresh_ui(self):
        """刷新整个UI"""
        # 清空订阅源列表
        for item in self.subscription_tree.get_children():
            self.subscription_tree.delete(item)

        # 清空文章列表
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

        # 清空文章详情
        self.article_title_label.config(text="")
        self.article_info_label.config(text="")
        self.article_content.delete(1.0, tk.END)
        self.current_article = None

        # 重置搜索框
        self.search_var.set("")
        self.article_search_var.set("")
        self.filter_var.set("all")

    def run(self):
        """运行主循环"""
        self.root.mainloop()
