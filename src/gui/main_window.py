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
from ..services.filter_service import filter_service
from ..models.news import NewsArticle
from ..models.subscription import Subscription
from .login_dialog import LoginDialog
from .filter_config_dialog import FilterConfigDialog
from .filter_progress_dialog import FilterProgressDialog, FilterMetricsDialog
from .agent_config_dialog import AgentConfigDialog
from .rss_manager import RSSManager


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("新闻订阅工具 - News Selector")
        self.root.geometry("1200x800")
        
        # 服务实例
        self.auth = InoreaderAuth()
        self.news_service = NewsService(self.auth)
        self.subscription_service = SubscriptionService(self.auth)
        
        # 数据
        self.current_articles: List[NewsArticle] = []
        self.current_subscriptions: List[Subscription] = []
        self.filtered_articles: List[NewsArticle] = []  # 筛选后的文章
        self.filter_result = None  # 筛选结果
        self.display_mode = "all"  # 显示模式: "all" 或 "filtered"
        
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
        view_menu.add_separator()
        view_menu.add_command(label="清除缓存", command=self.clear_cache)
        view_menu.add_command(label="缓存状态", command=self.show_cache_status)
        view_menu.add_separator()
        view_menu.add_command(label="显示统计", command=self.show_statistics)

        # 筛选菜单
        filter_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="筛选", menu=filter_menu)
        filter_menu.add_command(label="智能筛选", command=self.smart_filter_articles)
        filter_menu.add_command(label="批量筛选", command=self.batch_filter_articles)
        filter_menu.add_separator()
        filter_menu.add_command(label="筛选配置", command=self.show_filter_config)
        filter_menu.add_command(label="AI Agent配置", command=self.show_agent_config)
        filter_menu.add_command(label="性能指标", command=self.show_filter_metrics)
        
        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_left_panel(self, parent):
        """创建左侧面板"""
        left_frame = ttk.Frame(parent)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5))

        # 订阅源管理标题
        ttk.Label(left_frame, text="订阅源管理", font=("Arial", 12, "bold")).pack(pady=(0, 10))

        # 创建订阅源标签页
        self.subscription_notebook = ttk.Notebook(left_frame)
        self.subscription_notebook.pack(fill=tk.BOTH, expand=True)

        # 创建Inoreader订阅标签页
        self.create_inoreader_subscription_tab()

        # 创建自定义RSS标签页
        self.create_custom_rss_subscription_tab()
    
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

        # 筛选结果选项（初始状态禁用）
        self.filtered_radio = ttk.Radiobutton(filter_frame, text="筛选", variable=self.filter_var,
                       value="filtered", command=self.filter_articles, state=tk.DISABLED)
        self.filtered_radio.pack(side=tk.LEFT, padx=(10, 0))

        # 智能筛选区域
        filter_action_frame = ttk.Frame(toolbar)
        filter_action_frame.pack(side=tk.LEFT, padx=(20, 0))

        # 筛选按钮组
        filter_buttons_frame = ttk.Frame(filter_action_frame)
        filter_buttons_frame.pack(side=tk.LEFT)

        # 快速筛选按钮
        ttk.Button(filter_buttons_frame, text="关键词筛选",
                  command=lambda: self.quick_filter("keyword")).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(filter_buttons_frame, text="AI筛选",
                  command=lambda: self.quick_filter("ai")).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(filter_buttons_frame, text="智能筛选",
                  command=lambda: self.quick_filter("chain")).pack(side=tk.LEFT, padx=(0, 5))

        # 显示所有文章按钮
        ttk.Button(filter_action_frame, text="显示全部", command=self.show_all_articles).pack(side=tk.LEFT, padx=(5, 0))

        # 筛选类型选择（保留用于高级用户）
        ttk.Label(filter_action_frame, text="模式:").pack(side=tk.LEFT, padx=(10, 5))
        self.filter_type_var = tk.StringVar(value="chain")
        filter_type_combo = ttk.Combobox(filter_action_frame, textvariable=self.filter_type_var,
                                       values=["keyword", "ai", "chain"], width=10, state="readonly")
        filter_type_combo.pack(side=tk.LEFT)

        # 绑定选择变化事件
        filter_type_combo.bind("<<ComboboxSelected>>", self.on_filter_type_changed)

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
        columns = ("title", "feed", "date", "status", "score")
        self.article_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # 设置列
        self.article_tree.heading("title", text="标题")
        self.article_tree.heading("feed", text="来源")
        self.article_tree.heading("date", text="日期")
        self.article_tree.heading("status", text="状态")
        self.article_tree.heading("score", text="筛选分数")

        self.article_tree.column("title", width=350)
        self.article_tree.column("feed", width=120)
        self.article_tree.column("date", width=120)
        self.article_tree.column("status", width=80)
        self.article_tree.column("score", width=80)
        
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
                self.update_status("正在刷新订阅源...")
                # 清除订阅源相关缓存
                self.subscription_service.refresh_subscriptions_cache()
                subscriptions_with_unread = self.subscription_service.get_subscriptions_with_unread_counts()

                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_subscription_list(subscriptions_with_unread))
                self.root.after(0, lambda: self.update_status("订阅源已刷新"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"刷新订阅源失败: {e}"))
                self.root.after(0, lambda: self.update_status("刷新订阅源失败"))

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
                self.update_status("正在刷新新闻...")
                # 清除文章相关缓存
                self.news_service.refresh_articles_cache()
                articles = self.news_service.get_latest_articles(count=100, exclude_read=False)

                # 在主线程中更新UI
                self.root.after(0, lambda: self.update_article_list(articles))
                self.root.after(0, lambda: self.update_status("新闻已刷新"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", f"刷新新闻失败: {e}"))
                self.root.after(0, lambda: self.update_status("刷新新闻失败"))

        # 在后台线程中加载
        threading.Thread(target=load_news, daemon=True).start()

    def update_article_list(self, articles: List[NewsArticle]):
        """更新文章列表UI"""
        print(f"🔄 update_article_list被调用，文章数量: {len(articles)}")
        self.current_articles = articles

        # 如果当前有筛选结果，不要覆盖
        if not self.filtered_articles:
            print(f"   没有筛选结果，调用filter_articles")
            self.filter_articles()
        else:
            print(f"   保持当前筛选结果，不调用filter_articles")

        self.update_status(f"已加载 {len(articles)} 篇文章")

    def filter_articles(self):
        """根据过滤条件显示文章"""
        print(f"🔄 filter_articles被调用")
        print(f"   display_mode: {self.display_mode}")
        print(f"   filtered_articles数量: {len(self.filtered_articles) if self.filtered_articles else 0}")
        print(f"   current_articles数量: {len(self.current_articles) if self.current_articles else 0}")

        filter_type = self.filter_var.get()
        print(f"   filter_type: {filter_type}")

        # 如果选择了筛选选项，显示筛选结果
        if filter_type == "filtered":
            if self.filtered_articles:
                print(f"   显示筛选结果")
                self.display_mode = "filtered"
                self.update_filtered_article_list()
                return
            else:
                print(f"   没有筛选结果，切换到全部")
                # 如果没有筛选结果，自动切换到"全部"
                self.filter_var.set("all")
                filter_type = "all"

        # 显示普通文章列表
        print(f"   显示普通文章列表，类型: {filter_type}")
        self.display_mode = "all"

        # 清空现有项目
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

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
                article.get_display_title(50),
                article.feed_title or "未知",
                article.published.strftime("%m-%d %H:%M"),
                status_text,
                ""  # 普通文章没有筛选分数
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
                article.get_display_title(50),
                article.feed_title or "未知",
                article.published.strftime("%m-%d %H:%M"),
                status_text,
                ""  # 搜索结果没有筛选分数
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
        selection = self.article_tree.selection()
        if not selection:
            return

        # 获取选中的文章
        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]

            # 检查是否是RSS文章（通过ID格式判断）
            if self.is_rss_article(article):
                # RSS文章：询问用户是打开原文还是查看详情
                import webbrowser
                from tkinter import messagebox

                choice = messagebox.askyesnocancel(
                    "打开文章",
                    f"文章: {article.title}\n\n选择操作：\n是 - 打开原文链接\n否 - 查看详情\n取消 - 关闭"
                )

                if choice is True:  # 打开原文
                    if article.url:
                        webbrowser.open(article.url)
                        # 标记为已读
                        self.mark_rss_article_read(article)
                elif choice is False:  # 查看详情
                    self.show_article_detail(article)
            else:
                # Inoreader文章：直接查看详情
                self.show_article_detail(article)

    def is_rss_article(self, article):
        """判断是否是RSS文章"""
        # 简单的判断方法：RSS文章的ID通常包含URL或特殊格式
        return hasattr(article, 'id') and ('#' in article.id or 'http' in article.id)

    def mark_rss_article_read(self, article):
        """标记RSS文章为已读"""
        if hasattr(self, 'rss_manager') and self.rss_manager:
            # 找到对应的RSS订阅源并标记文章为已读
            for feed in self.rss_manager.current_rss_feeds:
                for rss_article in feed.articles:
                    if rss_article.id == article.id:
                        self.rss_manager.custom_rss_service.mark_article_read(article.id, feed.id)
                        # 更新本地显示
                        article.is_read = True
                        self.update_article_list(self.current_articles)
                        return

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

    def smart_filter_articles(self):
        """智能筛选文章（使用当前选择的筛选类型）"""
        filter_type = self.filter_type_var.get()
        self.quick_filter(filter_type)

    def batch_filter_articles(self):
        """批量筛选文章"""
        try:
            # 导入批量筛选对话框
            from .batch_filter_dialog import BatchFilterDialog

            # 创建并显示批量筛选配置对话框
            dialog = BatchFilterDialog(self.root)
            result = dialog.show()

            if result:
                # 用户确认了批量筛选配置，执行筛选
                self.execute_batch_filter(result)

        except ImportError:
            messagebox.showerror("错误", "批量筛选功能模块未找到")
        except Exception as e:
            messagebox.showerror("错误", f"启动批量筛选失败: {e}")

    def execute_batch_filter(self, config):
        """执行批量筛选"""
        try:
            from ..services.batch_filter_service import BatchFilterManager
            from .batch_filter_progress_dialog import BatchFilterProgressDialog

            # 创建批量筛选管理器
            manager = BatchFilterManager(self.auth)

            # 创建进度对话框
            progress_dialog = BatchFilterProgressDialog(self.root)

            # 在后台线程中执行批量筛选
            def run_batch_filter():
                try:
                    result = manager.filter_subscriptions_batch(config, progress_dialog)
                    # 在主线程中处理结果
                    self.root.after(0, lambda: self.handle_batch_filter_result(result))
                except Exception as e:
                    self.root.after(0, lambda: self.handle_batch_filter_error(str(e)))
                finally:
                    self.root.after(0, progress_dialog.close)

            # 显示进度对话框并启动后台任务
            progress_dialog.show()
            threading.Thread(target=run_batch_filter, daemon=True).start()

        except Exception as e:
            messagebox.showerror("错误", f"批量筛选执行失败: {e}")

    def handle_batch_filter_result(self, result):
        """处理批量筛选结果"""
        try:
            from .batch_filter_result_dialog import BatchFilterResultDialog

            # 显示结果对话框
            result_dialog = BatchFilterResultDialog(self.root, result)
            result_dialog.show()

            # 将批量筛选结果集成到主窗口
            self.integrate_batch_filter_result(result)

            # 更新状态栏
            self.update_status(f"批量筛选完成: 处理了{result.processed_subscriptions}个订阅源，筛选出{result.total_articles_selected}篇文章")

        except Exception as e:
            messagebox.showerror("错误", f"显示批量筛选结果失败: {e}")

    def integrate_batch_filter_result(self, result):
        """将批量筛选结果集成到主窗口"""
        try:
            # 将批量筛选的文章转换为NewsArticle列表
            batch_articles = []
            for combined_result in result.all_selected_articles:
                # 添加批量筛选标记
                article = combined_result.article
                article.batch_filter_score = combined_result.final_score
                article.batch_filter_source = True
                batch_articles.append(article)

            if batch_articles:
                # 询问用户是否要在主窗口中显示批量筛选结果
                if messagebox.askyesno("集成结果",
                                     f"是否要在主窗口中显示批量筛选的 {len(batch_articles)} 篇文章？\n"
                                     "这将替换当前显示的文章列表。"):

                    # 更新当前文章列表
                    self.current_articles = batch_articles

                    # 创建模拟的筛选结果
                    from ..filters.base import FilterChainResult, CombinedFilterResult
                    from datetime import datetime

                    filter_result = FilterChainResult(
                        total_articles=len(batch_articles),
                        processing_start_time=result.processing_start_time,
                        processing_end_time=result.processing_end_time,
                        final_selected_count=len(batch_articles)
                    )

                    # 转换为CombinedFilterResult格式
                    combined_results = []
                    for combined_result in result.all_selected_articles:
                        combined_results.append(combined_result)

                    filter_result.selected_articles = combined_results

                    # 设置筛选结果
                    self.filtered_articles = combined_results
                    self.filter_result = filter_result

                    # 启用筛选结果选项
                    self.filtered_radio.config(state=tk.NORMAL)

                    # 切换到筛选结果视图
                    self.filter_var.set("filtered")
                    self.display_mode = "filtered"

                    # 更新文章列表显示
                    self.update_filtered_article_list()

                    # 更新状态
                    self.update_status(f"已显示批量筛选结果: {len(batch_articles)} 篇文章")

        except Exception as e:
            messagebox.showerror("错误", f"集成批量筛选结果失败: {e}")

    def handle_batch_filter_error(self, error_msg):
        """处理批量筛选错误"""
        messagebox.showerror("批量筛选失败", f"批量筛选过程中发生错误:\n{error_msg}")
        self.update_status("批量筛选失败")

    def quick_filter(self, filter_type: str):
        """快速筛选文章"""
        # 检查是否有文章
        if not self.current_articles:
            messagebox.showinfo("提示", "请先加载文章")
            return

        # 更新筛选类型选择器
        self.filter_type_var.set(filter_type)

        # 显示筛选类型说明
        filter_descriptions = {
            "keyword": "使用关键词快速筛选，速度快，适合大批量处理",
            "ai": "使用AI智能评估，准确度高，适合精准筛选",
            "chain": "关键词+AI综合筛选，平衡速度和准确性"
        }

        description = filter_descriptions.get(filter_type, "")
        self.update_status(f"开始{filter_type}筛选: {description}")

        # 显示进度对话框并执行筛选
        progress_dialog = FilterProgressDialog(
            self.root,
            self.current_articles,
            filter_type
        )

        # 获取筛选结果
        print(f"筛选对话框关闭，结果: {progress_dialog.result is not None}, 取消: {progress_dialog.cancelled}")

        if progress_dialog.result and not progress_dialog.cancelled:
            self.filter_result = progress_dialog.result
            self.filtered_articles = [r.article for r in self.filter_result.selected_articles]
            self.display_mode = "filtered"  # 设置为筛选模式

            print(f"筛选成功，获得 {len(self.filtered_articles)} 篇文章")
            print(f"设置显示模式为: {self.display_mode}")

            # 启用筛选选项并切换到筛选视图
            self.filtered_radio.config(state=tk.NORMAL)
            self.filter_var.set("filtered")

            # 更新文章列表显示
            self.update_filtered_article_list()

            # 显示筛选结果摘要
            self.show_filter_summary()
        elif progress_dialog.cancelled:
            self.update_status("筛选已取消")
        else:
            print(f"筛选失败，result: {progress_dialog.result}, cancelled: {progress_dialog.cancelled}")
            if progress_dialog.result is None:
                self.update_status("筛选失败：未获取到结果")
            else:
                self.update_status("筛选失败")

    def on_filter_type_changed(self, event=None):
        """筛选类型变化处理"""
        filter_type = self.filter_type_var.get()

        # 显示筛选类型说明
        filter_info = {
            "keyword": "关键词筛选：基于预设关键词快速筛选，速度快，成本低",
            "ai": "AI筛选：使用人工智能深度分析，准确度高，理解能力强",
            "chain": "综合筛选：关键词预筛选+AI精筛选，平衡效率和质量"
        }

        info = filter_info.get(filter_type, "")
        self.update_status(f"筛选模式: {info}")

    def update_filtered_article_list(self):
        """更新筛选后的文章列表显示"""
        print(f"🔄 开始更新筛选文章列表...")
        print(f"   filtered_articles数量: {len(self.filtered_articles) if self.filtered_articles else 0}")
        print(f"   filter_result存在: {self.filter_result is not None}")

        # 确保设置为筛选模式
        self.display_mode = "filtered"
        print(f"   设置显示模式为: {self.display_mode}")

        # 清空现有项目
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)
        print(f"   已清空文章列表")

        if not self.filtered_articles:
            print(f"   没有筛选文章，退出更新")
            self.update_status("没有文章通过筛选")
            return

        print(f"   开始添加 {len(self.filtered_articles)} 篇文章到列表")

        # 显示筛选后的文章
        for i, article in enumerate(self.filtered_articles):
            try:
                # 状态指示
                status = []
                if hasattr(article, 'is_read') and not article.is_read:
                    status.append("未读")
                if hasattr(article, 'is_starred') and article.is_starred:
                    status.append("★")

                status_text = " ".join(status) if status else "已读"

                # 添加筛选标记
                status_text = f"[筛选] {status_text}"

                # 获取筛选分数
                score_text = ""
                if self.filter_result and i < len(self.filter_result.selected_articles):
                    combined_result = self.filter_result.selected_articles[i]
                    score_text = f"{combined_result.final_score:.3f}"

                # 获取发布时间
                try:
                    if hasattr(article, 'published_date') and article.published_date:
                        date_text = article.published_date.strftime("%m-%d %H:%M")
                    elif hasattr(article, 'published') and article.published:
                        date_text = article.published.strftime("%m-%d %H:%M")
                    else:
                        date_text = "未知时间"
                except:
                    date_text = "时间错误"

                # 添加到列表
                item_id = self.article_tree.insert("", tk.END, values=(
                    article.get_display_title(50) if hasattr(article, 'get_display_title') else article.title[:50],
                    getattr(article, 'feed_title', None) or getattr(article, 'source', None) or "未知",
                    date_text,
                    status_text,
                    score_text
                ))

                print(f"   添加文章 {i+1}: {article.title[:30]}...")

            except Exception as e:
                print(f"   ❌ 添加文章 {i+1} 失败: {e}")
                print(f"      文章对象: {type(article)}")
                print(f"      文章属性: {dir(article)}")

        print(f"   ✅ 文章列表更新完成")
        self.update_status(f"显示筛选结果: {len(self.filtered_articles)} 篇文章")

        # 强制刷新界面
        self.article_tree.update_idletasks()

        # 切换到文章列表标签页
        self.notebook.select(0)  # 选择第一个标签页（文章列表）

    def show_filter_summary(self):
        """显示筛选结果摘要"""
        if not self.filter_result:
            return

        result = self.filter_result

        summary = f"""筛选完成！

输入文章数: {result.total_articles}
关键词筛选通过: {result.keyword_filtered_count}
AI筛选通过: {result.ai_filtered_count}
最终选出: {result.final_selected_count}
处理时间: {result.total_processing_time:.2f}秒

是否查看详细的筛选结果？"""

        if messagebox.askyesno("筛选完成", summary):
            self.show_filter_details()

    def show_filter_details(self):
        """显示筛选详细结果"""
        if not self.filter_result or not self.filter_result.selected_articles:
            return

        # 创建详情窗口
        detail_window = tk.Toplevel(self.root)
        detail_window.title("筛选详细结果")
        detail_window.geometry("800x600")
        detail_window.transient(self.root)

        # 创建文本框显示详情
        text_frame = ttk.Frame(detail_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        detail_text = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=detail_text.yview)
        detail_text.configure(yscrollcommand=scrollbar.set)

        # 显示详细信息
        detail_text.insert(tk.END, "筛选详细结果\n")
        detail_text.insert(tk.END, "=" * 60 + "\n\n")

        for i, combined_result in enumerate(self.filter_result.selected_articles, 1):
            article = combined_result.article
            detail_text.insert(tk.END, f"{i}. {article.title}\n")
            detail_text.insert(tk.END, f"   来源: {article.feed_title}\n")
            detail_text.insert(tk.END, f"   时间: {article.published.strftime('%Y-%m-%d %H:%M')}\n")

            if combined_result.keyword_result:
                kr = combined_result.keyword_result
                detail_text.insert(tk.END, f"   关键词分数: {kr.relevance_score:.3f}\n")
                if kr.matched_keywords:
                    keywords = [m.keyword for m in kr.matched_keywords[:3]]
                    detail_text.insert(tk.END, f"   匹配关键词: {', '.join(keywords)}\n")

            if combined_result.ai_result:
                ar = combined_result.ai_result
                eval_result = ar.evaluation
                detail_text.insert(tk.END, f"   AI评分: {eval_result.total_score}/30\n")
                detail_text.insert(tk.END, f"   评分详情: 相关性{eval_result.relevance_score} | 创新性{eval_result.innovation_impact} | 实用性{eval_result.practicality}\n")
                if ar.cached:
                    detail_text.insert(tk.END, f"   (使用缓存)\n")

            detail_text.insert(tk.END, f"   最终分数: {combined_result.final_score:.3f}\n")
            detail_text.insert(tk.END, "\n")

        # 布局
        detail_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 关闭按钮
        ttk.Button(detail_window, text="关闭", command=detail_window.destroy).pack(pady=10)

    def show_filter_config(self):
        """显示筛选配置对话框"""
        config_dialog = FilterConfigDialog(self.root)
        if config_dialog.result:
            messagebox.showinfo("提示", "配置已更新，下次筛选时生效")

    def show_agent_config(self):
        """显示AI Agent配置对话框"""
        agent_dialog = AgentConfigDialog(self.root)
        if agent_dialog.result:
            messagebox.showinfo("提示", "AI Agent配置已更新，下次筛选时生效")

    def show_filter_metrics(self):
        """显示筛选性能指标"""
        FilterMetricsDialog(self.root)

    def show_all_articles(self):
        """显示所有文章（取消筛选）"""
        print(f"🔄 show_all_articles被调用")
        self.filtered_articles = []
        self.filter_result = None
        self.display_mode = "all"  # 设置为显示所有文章模式
        print(f"设置显示模式为: {self.display_mode}")

        # 禁用筛选选项并切换到全部
        self.filtered_radio.config(state=tk.DISABLED)
        self.filter_var.set("all")

        self.filter_articles()  # 重新显示所有文章

    def clear_cache(self):
        """清除所有缓存"""
        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        try:
            # 询问用户确认
            if messagebox.askyesno("确认", "确定要清除所有缓存吗？\n这将删除所有已缓存的数据。"):
                self.news_service.refresh_cache()
                self.subscription_service.refresh_cache()
                messagebox.showinfo("成功", "缓存已清除")
                self.update_status("缓存已清除")
        except Exception as e:
            messagebox.showerror("错误", f"清除缓存失败: {e}")

    def show_cache_status(self):
        """显示缓存状态"""
        if not self.auth.is_authenticated():
            messagebox.showwarning("警告", "请先登录")
            return

        try:
            # 获取缓存信息
            news_cache_info = self.news_service.get_cache_info()
            sub_cache_info = self.subscription_service.get_cache_info()

            # 创建状态窗口
            status_window = tk.Toplevel(self.root)
            status_window.title("缓存和API状态")
            status_window.geometry("600x500")
            status_window.resizable(True, True)

            # 创建滚动文本框
            text_frame = ttk.Frame(status_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            text_widget = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 格式化状态信息
            status_text = self._format_cache_status(news_cache_info, sub_cache_info)

            text_widget.config(state=tk.NORMAL)
            text_widget.insert(tk.END, status_text)
            text_widget.config(state=tk.DISABLED)

            # 添加按钮
            button_frame = ttk.Frame(status_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            ttk.Button(button_frame, text="刷新状态",
                      command=lambda: self._refresh_cache_status(text_widget, news_cache_info, sub_cache_info)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="清除缓存",
                      command=lambda: self._clear_cache_from_status(status_window)).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="关闭",
                      command=status_window.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            messagebox.showerror("错误", f"获取缓存状态失败: {e}")

    def _format_cache_status(self, news_cache_info: dict, sub_cache_info: dict) -> str:
        """格式化缓存状态信息"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 缓存和API状态信息")
        lines.append("=" * 60)

        # API区域信息
        current_region = news_cache_info.get('current_region', {})
        lines.append(f"\n🌍 当前API区域:")
        lines.append(f"   名称: {current_region.get('name', '未知')}")
        lines.append(f"   描述: {current_region.get('description', '未知')}")
        lines.append(f"   URL: {current_region.get('base_url', '未知')}")
        lines.append(f"   切换次数: {current_region.get('switch_attempts', 0)}")

        # 缓存统计
        cache_stats = news_cache_info.get('cache_stats', {})
        lines.append(f"\n💾 缓存统计:")
        lines.append(f"   缓存状态: {'启用' if cache_stats.get('enabled', False) else '禁用'}")
        lines.append(f"   缓存文件数: {cache_stats.get('total_files', 0)}")
        lines.append(f"   有效文件数: {cache_stats.get('valid_files', 0)}")
        lines.append(f"   缓存大小: {cache_stats.get('total_size_mb', 0)} MB")
        lines.append(f"   最大大小: {cache_stats.get('max_size_mb', 0)} MB")
        lines.append(f"   过期时间: {cache_stats.get('expire_hours', 0)} 小时")
        lines.append(f"   缓存目录: {cache_stats.get('cache_dir', '未知')}")

        # 服务状态
        lines.append(f"\n🔧 服务状态:")
        lines.append(f"   新闻服务缓存: {'启用' if news_cache_info.get('cache_enabled', False) else '禁用'}")
        lines.append(f"   订阅服务缓存: {'启用' if sub_cache_info.get('cache_enabled', False) else '禁用'}")

        return "\n".join(lines)

    def _refresh_cache_status(self, text_widget, news_cache_info, sub_cache_info):
        """刷新缓存状态显示"""
        try:
            # 重新获取状态信息
            news_cache_info = self.news_service.get_cache_info()
            sub_cache_info = self.subscription_service.get_cache_info()

            # 更新显示
            status_text = self._format_cache_status(news_cache_info, sub_cache_info)

            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.insert(tk.END, status_text)
            text_widget.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("错误", f"刷新状态失败: {e}")

    def _clear_cache_from_status(self, parent_window):
        """从状态窗口清除缓存"""
        if messagebox.askyesno("确认", "确定要清除所有缓存吗？", parent=parent_window):
            try:
                self.news_service.refresh_cache()
                self.subscription_service.refresh_cache()
                messagebox.showinfo("成功", "缓存已清除", parent=parent_window)
                # 刷新状态显示
                parent_window.destroy()
                self.show_cache_status()
            except Exception as e:
                messagebox.showerror("错误", f"清除缓存失败: {e}", parent=parent_window)
        self.update_status(f"显示所有文章: {len(self.current_articles)} 篇")

    def create_inoreader_subscription_tab(self):
        """创建Inoreader订阅标签页"""
        inoreader_frame = ttk.Frame(self.subscription_notebook)
        self.subscription_notebook.add(inoreader_frame, text="Inoreader订阅")

        # 搜索框
        search_frame = ttk.Frame(inoreader_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        search_entry.bind('<Return>', self.search_subscriptions)

        # 订阅源列表
        list_frame = ttk.Frame(inoreader_frame)
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
        button_frame = ttk.Frame(inoreader_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="刷新订阅源", command=self.refresh_subscriptions).pack(fill=tk.X, pady=(0, 5))
        ttk.Button(button_frame, text="获取最新新闻", command=self.refresh_news).pack(fill=tk.X)

    def create_custom_rss_subscription_tab(self):
        """创建自定义RSS订阅标签页"""
        rss_frame = ttk.Frame(self.subscription_notebook)
        self.subscription_notebook.add(rss_frame, text="自定义RSS")

        # 创建RSS管理器，传入文章回调函数
        self.rss_manager = RSSManager(rss_frame, self.on_rss_articles_loaded)

    def on_rss_articles_loaded(self, rss_articles, source_name):
        """处理RSS文章加载事件"""
        # 将RSS文章转换为NewsArticle格式以便在主文章列表中显示
        from ..models.news import NewsArticle

        converted_articles = []
        for rss_article in rss_articles:
            # 创建NewsArticle对象
            from ..models.news import NewsAuthor

            # 处理作者信息
            author_obj = None
            if rss_article.author:
                author_obj = NewsAuthor(name=rss_article.author)

            news_article = NewsArticle(
                id=rss_article.id,
                title=rss_article.title,
                summary=rss_article.summary,
                content=rss_article.content,
                url=rss_article.url,
                published=rss_article.published,
                updated=rss_article.published,  # RSS文章使用发布时间作为更新时间
                author=author_obj,
                categories=[],  # RSS文章没有分类信息
                is_read=rss_article.is_read,
                is_starred=rss_article.is_starred,
                feed_title=source_name  # 设置来源标题
            )
            converted_articles.append(news_article)

        # 更新当前文章列表
        self.current_articles = converted_articles
        self.display_mode = "all"

        # 更新文章列表显示
        self.update_article_list(converted_articles)

        # 更新状态栏
        self.update_status(f"显示 {source_name} 文章: {len(converted_articles)} 篇")

    def run(self):
        """运行主循环"""
        self.root.mainloop()
