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
from .rss_manager import RSSManager
# from .ai_analysis_dialog import AIAnalysisDialog  # 不再需要，改为直接在日志中显示


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
        self.selected_subscription = None  # 当前选中的订阅源
        
        # 同步Agent配置到FilterService
        self.sync_agent_config_on_startup()

        # 创建界面
        self.create_widgets()
        self.update_login_status()

    def sync_agent_config_on_startup(self):
        """应用启动时同步Agent配置到FilterService"""
        try:
            from src.config.agent_config import agent_config_manager
            from src.services.filter_service import filter_service

            # 获取当前Agent配置
            current_config = agent_config_manager.get_current_config()
            if current_config and current_config.api_config:
                # 同步API配置到FilterService
                filter_service.update_config("ai",
                    api_key=current_config.api_config.api_key,
                    model_name=current_config.api_config.model_name,
                    base_url=current_config.api_config.base_url
                )
                # 重置AI筛选器缓存以使用新配置
                filter_service.reset_ai_filter()
                print(f"✅ 启动时已同步Agent配置 '{current_config.config_name}' 到FilterService")
            else:
                print("⚠️  启动时没有找到有效的Agent配置")
        except Exception as e:
            print(f"❌ 启动时同步Agent配置失败: {e}")

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
        filter_menu.add_command(label="性能指标", command=self.show_filter_metrics)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="导出Inoreader订阅源", command=self.export_inoreader_subscriptions)
        tools_menu.add_separator()
        tools_menu.add_command(label="RSS管理", command=self.show_rss_manager)

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

        # 统一筛选按钮
        ttk.Button(filter_buttons_frame, text="筛选",
                  command=self.show_filter_dialog).pack(side=tk.LEFT, padx=(0, 5))

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

        # 创建主内容区域（文章列表 + 日志区域）
        main_content_frame = ttk.Frame(articles_frame)
        main_content_frame.pack(fill=tk.BOTH, expand=True)

        # 创建垂直分割面板
        main_paned = ttk.PanedWindow(main_content_frame, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # 文章列表区域
        list_frame = ttk.Frame(main_paned)
        main_paned.add(list_frame, weight=3)  # 文章列表占更多空间

        # 创建Treeview用于显示文章
        columns = ("title", "feed", "date", "status", "ai_score", "final_score", "ai_summary", "ai_tags")
        self.article_tree = ttk.Treeview(list_frame, columns=columns, show="headings")

        # 设置列
        self.article_tree.heading("title", text="标题")
        self.article_tree.heading("feed", text="来源")
        self.article_tree.heading("date", text="日期")
        self.article_tree.heading("status", text="状态")
        self.article_tree.heading("ai_score", text="AI分数")
        self.article_tree.heading("final_score", text="综合分数")
        self.article_tree.heading("ai_summary", text="AI摘要")
        self.article_tree.heading("ai_tags", text="AI标签")

        self.article_tree.column("title", width=280)
        self.article_tree.column("feed", width=100)
        self.article_tree.column("date", width=100)
        self.article_tree.column("status", width=80)
        self.article_tree.column("ai_score", width=70)
        self.article_tree.column("final_score", width=80)
        self.article_tree.column("ai_summary", width=200)
        self.article_tree.column("ai_tags", width=150)

        # 添加滚动条
        article_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.article_tree.yview)
        self.article_tree.configure(yscrollcommand=article_scrollbar.set)

        self.article_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        article_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 绑定双击事件
        self.article_tree.bind("<Double-1>", self.on_article_double_click)

        # 绑定右键菜单
        self.article_tree.bind("<Button-3>", self.show_article_context_menu)

        # 创建日志区域
        self.create_log_area(main_paned)

        # 右键菜单
        self.create_article_context_menu()

    def create_log_area(self, parent):
        """创建日志区域"""
        log_frame = ttk.LabelFrame(parent, text="AI分析日志", padding="5")
        parent.add(log_frame, weight=1)  # 日志区域占较少空间

        # 日志工具栏
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill=tk.X, pady=(0, 5))

        # 清空日志按钮
        ttk.Button(log_toolbar, text="清空日志", command=self.clear_log).pack(side=tk.LEFT)

        # 自动滚动选项
        self.auto_scroll_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(log_toolbar, text="自动滚动", variable=self.auto_scroll_var).pack(side=tk.LEFT, padx=(10, 0))

        # MCP结构化输出选项
        self.use_mcp_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(log_toolbar, text="MCP结构化", variable=self.use_mcp_var).pack(side=tk.LEFT, padx=(10, 0))

        # 日志级别选择
        ttk.Label(log_toolbar, text="级别:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level_var = tk.StringVar(value="INFO")
        log_level_combo = ttk.Combobox(log_toolbar, textvariable=self.log_level_var,
                                     values=["DEBUG", "INFO", "WARNING", "ERROR"], width=8, state="readonly")
        log_level_combo.pack(side=tk.LEFT)

        # 创建日志文本区域
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=tk.BOTH, expand=True)

        # 日志文本控件
        self.log_text = scrolledtext.ScrolledText(
            log_text_frame,
            wrap=tk.WORD,
            height=8,
            font=("Consolas", 9),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置日志文本的颜色标签
        self.log_text.tag_configure("DEBUG", foreground="gray")
        self.log_text.tag_configure("INFO", foreground="black")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("AI_RESPONSE", foreground="blue", font=("Consolas", 9, "bold"))
        self.log_text.tag_configure("TIMESTAMP", foreground="gray", font=("Consolas", 8))

        # 初始化日志
        self.log_message("INFO", "日志系统已初始化")

    def log_message(self, level, message, tag=None):
        """添加日志消息"""
        import datetime

        # 检查日志级别过滤
        level_priority = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
        current_level = self.log_level_var.get()
        if level_priority.get(level, 1) < level_priority.get(current_level, 1):
            return

        # 格式化时间戳
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # 启用文本编辑
        self.log_text.config(state=tk.NORMAL)

        # 添加时间戳
        self.log_text.insert(tk.END, f"[{timestamp}] ", "TIMESTAMP")

        # 添加级别标签
        self.log_text.insert(tk.END, f"[{level}] ", level)

        # 添加消息内容
        if tag:
            self.log_text.insert(tk.END, f"{message}\n", tag)
        else:
            self.log_text.insert(tk.END, f"{message}\n")

        # 禁用文本编辑
        self.log_text.config(state=tk.DISABLED)

        # 自动滚动到底部
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)

        # 更新界面
        self.root.update_idletasks()

    def clear_log(self):
        """清空日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_message("INFO", "日志已清空")
    
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
        self.article_context_menu.add_command(label="AI分析", command=self.analyze_article_with_ai)
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
                "",  # 普通文章没有AI分数
                "",  # 普通文章没有综合分数
                "",  # 普通文章没有AI摘要
                ""   # 普通文章没有AI标签
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
                "",  # 搜索结果没有筛选分数
                "",  # 搜索结果没有AI摘要
                ""   # 搜索结果没有AI标签
            ))

        self.update_status(f"找到 {len(matched_articles)} 篇相关文章")

    def on_subscription_select(self, event):
        """订阅源选择事件"""
        selection = self.subscription_tree.selection()
        if not selection:
            self.selected_subscription = None
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
            self.selected_subscription = selected_subscription  # 保存当前选中的订阅源
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

    def show_article_context_menu(self, event):
        """显示文章右键菜单"""
        # 选择点击的项目
        item = self.article_tree.identify_row(event.y)
        if item:
            self.article_tree.selection_set(item)

            # 创建右键菜单
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="🧪 测试筛选", command=self.test_single_article_filter)
            context_menu.add_separator()
            context_menu.add_command(label="📖 查看详情", command=lambda: self.on_article_double_click(None))
            context_menu.add_command(label="🌐 打开原文", command=self.open_article_url)

            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()

    def test_single_article_filter(self):
        """测试单条文章的筛选"""
        selection = self.article_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要测试的文章")
            return

        # 获取选中的文章
        item_index = self.article_tree.index(selection[0])

        # 根据当前显示模式获取文章
        if self.display_mode == "filtered" and self.filtered_articles:
            if item_index < len(self.filtered_articles):
                article = self.filtered_articles[item_index]
            else:
                messagebox.showerror("错误", "无法获取选中的文章")
                return
        else:
            displayed_articles = self.get_displayed_articles()
            if item_index < len(displayed_articles):
                article = displayed_articles[item_index]
            else:
                messagebox.showerror("错误", "无法获取选中的文章")
                return

        # 显示筛选类型选择对话框
        self.show_single_article_filter_dialog(article)

    def show_single_article_filter_dialog(self, article):
        """显示单条文章筛选对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("单条文章筛选测试")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # 文章信息
        info_frame = ttk.LabelFrame(main_frame, text="文章信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(info_frame, text="标题:", font=("", 10, "bold")).pack(anchor=tk.W)
        title_label = ttk.Label(info_frame, text=article.title, wraplength=450)
        title_label.pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(info_frame, text="来源:", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=article.feed_title or "未知").pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(info_frame, text="发布时间:", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=article.published.strftime("%Y-%m-%d %H:%M:%S")).pack(anchor=tk.W)

        # 筛选类型选择
        filter_frame = ttk.LabelFrame(main_frame, text="筛选类型", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 15))

        filter_type_var = tk.StringVar(value="chain")
        ttk.Radiobutton(filter_frame, text="关键词筛选", variable=filter_type_var, value="keyword").pack(anchor=tk.W)
        ttk.Radiobutton(filter_frame, text="AI智能筛选", variable=filter_type_var, value="ai").pack(anchor=tk.W)
        ttk.Radiobutton(filter_frame, text="综合筛选（推荐）", variable=filter_type_var, value="chain").pack(anchor=tk.W)

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        def start_test():
            filter_type = filter_type_var.get()
            dialog.destroy()
            self.execute_single_article_filter(article, filter_type)

        ttk.Button(button_frame, text="开始测试", command=start_test).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.RIGHT)

    def open_article_url(self):
        """打开文章原文链接"""
        selection = self.article_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择要打开的文章")
            return

        # 获取选中的文章
        item_index = self.article_tree.index(selection[0])

        # 根据当前显示模式获取文章
        if self.display_mode == "filtered" and self.filtered_articles:
            if item_index < len(self.filtered_articles):
                article = self.filtered_articles[item_index]
            else:
                messagebox.showerror("错误", "无法获取选中的文章")
                return
        else:
            displayed_articles = self.get_displayed_articles()
            if item_index < len(displayed_articles):
                article = displayed_articles[item_index]
            else:
                messagebox.showerror("错误", "无法获取选中的文章")
                return

        # 打开链接
        if article.url:
            import webbrowser
            webbrowser.open(article.url)
        else:
            messagebox.showwarning("警告", "该文章没有可用的链接")

    def execute_single_article_filter(self, article, filter_type):
        """执行单条文章筛选"""
        try:
            self.update_status(f"正在测试筛选文章: {article.title[:50]}...")

            # 创建筛选服务
            from ..services.filter_service import FilterService
            filter_service = FilterService()

            # 执行筛选
            result = filter_service.filter_articles([article], filter_type)

            # 显示结果
            self.show_single_article_filter_result(article, result, filter_type)

        except Exception as e:
            messagebox.showerror("错误", f"筛选测试失败: {e}")
            self.update_status("筛选测试失败")

    def show_single_article_filter_result(self, article, result, filter_type):
        """显示单条文章筛选结果"""
        dialog = tk.Toplevel(self.root)
        dialog.title("筛选测试结果")
        dialog.geometry("700x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

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

        # 文章信息
        info_frame = ttk.LabelFrame(scrollable_frame, text="文章信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(info_frame, text="标题:", font=("", 10, "bold")).pack(anchor=tk.W)
        title_label = ttk.Label(info_frame, text=article.title, wraplength=650)
        title_label.pack(anchor=tk.W, pady=(0, 5))

        ttk.Label(info_frame, text="来源:", font=("", 10, "bold")).pack(anchor=tk.W)
        ttk.Label(info_frame, text=article.feed_title or "未知").pack(anchor=tk.W, pady=(0, 5))

        # 筛选结果
        result_frame = ttk.LabelFrame(scrollable_frame, text=f"筛选结果 ({filter_type})", padding="10")
        result_frame.pack(fill=tk.X, pady=(0, 15))

        if result.selected_articles:
            combined_result = result.selected_articles[0]

            # 基本结果
            ttk.Label(result_frame, text="筛选结果: ✅ 通过", font=("", 10, "bold"), foreground="green").pack(anchor=tk.W)
            ttk.Label(result_frame, text=f"综合分数: {combined_result.final_score:.3f}", font=("", 10, "bold")).pack(anchor=tk.W, pady=(5, 0))

            # 关键词筛选结果
            if combined_result.keyword_result:
                keyword_frame = ttk.LabelFrame(result_frame, text="关键词筛选结果", padding="10")
                keyword_frame.pack(fill=tk.X, pady=(10, 0))

                ttk.Label(keyword_frame, text=f"相关性分数: {combined_result.keyword_result.relevance_score:.3f}").pack(anchor=tk.W)
                ttk.Label(keyword_frame, text=f"匹配关键词数: {len(combined_result.keyword_result.matched_keywords)}").pack(anchor=tk.W)

                if combined_result.keyword_result.matched_keywords:
                    ttk.Label(keyword_frame, text="匹配的关键词:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
                    for match in combined_result.keyword_result.matched_keywords[:5]:  # 显示前5个
                        ttk.Label(keyword_frame, text=f"  • {match.keyword} ({match.category})", font=("", 9)).pack(anchor=tk.W)

            # AI筛选结果
            if combined_result.ai_result:
                ai_frame = ttk.LabelFrame(result_frame, text="AI筛选结果", padding="10")
                ai_frame.pack(fill=tk.X, pady=(10, 0))

                evaluation = combined_result.ai_result.evaluation
                ttk.Label(ai_frame, text=f"AI总分: {evaluation.total_score}/30", font=("", 10, "bold")).pack(anchor=tk.W)
                ttk.Label(ai_frame, text=f"政策相关性: {evaluation.relevance_score}/10").pack(anchor=tk.W)
                ttk.Label(ai_frame, text=f"创新影响: {evaluation.innovation_impact}/10").pack(anchor=tk.W)
                ttk.Label(ai_frame, text=f"实用性: {evaluation.practicality}/10").pack(anchor=tk.W)
                ttk.Label(ai_frame, text=f"置信度: {evaluation.confidence:.2f}").pack(anchor=tk.W)

                if evaluation.summary:
                    ttk.Label(ai_frame, text="AI摘要:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(10, 0))
                    summary_label = ttk.Label(ai_frame, text=evaluation.summary, wraplength=600, font=("", 9))
                    summary_label.pack(anchor=tk.W, pady=(0, 5))

                if evaluation.reasoning:
                    ttk.Label(ai_frame, text="评估理由:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
                    reasoning_label = ttk.Label(ai_frame, text=evaluation.reasoning, wraplength=600, font=("", 9))
                    reasoning_label.pack(anchor=tk.W, pady=(0, 5))

                if evaluation.tags:
                    ttk.Label(ai_frame, text="相关标签:", font=("", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))
                    ttk.Label(ai_frame, text=", ".join(evaluation.tags), font=("", 9)).pack(anchor=tk.W)
        else:
            ttk.Label(result_frame, text="筛选结果: ❌ 未通过", font=("", 10, "bold"), foreground="red").pack(anchor=tk.W)
            if result.rejected_articles:
                rejected_result = result.rejected_articles[0]
                if rejected_result.rejection_reason:
                    ttk.Label(result_frame, text=f"拒绝原因: {rejected_result.rejection_reason}").pack(anchor=tk.W, pady=(5, 0))

        # 性能统计
        perf_frame = ttk.LabelFrame(scrollable_frame, text="性能统计", padding="10")
        perf_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(perf_frame, text=f"总处理时间: {result.total_processing_time:.2f}秒").pack(anchor=tk.W)
        if hasattr(result, 'keyword_filter_time'):
            ttk.Label(perf_frame, text=f"关键词筛选时间: {result.keyword_filter_time:.2f}秒").pack(anchor=tk.W)
        if hasattr(result, 'ai_filter_time'):
            ttk.Label(perf_frame, text=f"AI筛选时间: {result.ai_filter_time:.2f}秒").pack(anchor=tk.W)

        # 配置滚动
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 关闭按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT)

        self.update_status("筛选测试完成")

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

    def analyze_article_with_ai(self):
        """对选中文章执行AI分析"""
        selection = self.article_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一篇文章")
            return

        # 获取选中的文章
        article = self.get_selected_article()
        if not article:
            messagebox.showwarning("警告", "无法获取选中的文章")
            return

        # 在后台线程中执行AI分析
        import threading

        def run_ai_analysis():
            try:
                self.log_message("INFO", f"开始AI分析: {article.title[:50]}...")

                # 创建AI客户端
                from ..ai.factory import create_ai_client
                from ..config.filter_config import AIFilterConfig

                # 获取AI配置
                ai_config = AIFilterConfig()

                # 检查是否使用MCP
                use_mcp = self.use_mcp_var.get()
                client = create_ai_client(ai_config, use_mcp=use_mcp)

                if use_mcp:
                    self.log_message("INFO", "使用MCP客户端（结构化输出）")
                else:
                    self.log_message("INFO", f"使用AI模型: {ai_config.model_name}")

                self.log_message("DEBUG", f"文章内容长度: {len(article.content or '')} 字符")
                self.log_message("DEBUG", f"API配置: {ai_config.base_url}")

                # 执行AI评估
                self.log_message("DEBUG", "正在调用AI客户端进行评估...")
                evaluation = client.evaluate_article(article)
                self.log_message("DEBUG", "AI客户端评估完成")

                # 在主线程中更新UI
                self.root.after(0, lambda: self.handle_ai_analysis_result(article, evaluation))

            except Exception as e:
                error_msg = f"AI分析失败: {str(e)}"
                self.root.after(0, lambda: self.handle_ai_analysis_error(article, error_msg))

        # 启动后台分析
        threading.Thread(target=run_ai_analysis, daemon=True).start()

        # 更新状态
        self.update_status(f"正在分析文章: {article.title[:50]}...")

    def get_selected_article(self):
        """获取当前选中的文章"""
        selection = self.article_tree.selection()
        if not selection:
            return None

        item_index = self.article_tree.index(selection[0])

        # 根据当前显示模式获取文章
        if self.display_mode == "filtered" and self.filtered_articles:
            if item_index < len(self.filtered_articles):
                return self.filtered_articles[item_index]
        elif self.current_articles:
            if item_index < len(self.current_articles):
                return self.current_articles[item_index]

        return None

    def handle_ai_analysis_result(self, article, evaluation):
        """处理AI分析结果"""
        try:
            self.log_message("INFO", f"AI分析完成: {article.title[:50]}")
            self.log_message("INFO", f"总分: {evaluation.total_score}/30 (置信度: {evaluation.confidence:.2f})")
            self.log_message("INFO", f"政策相关性: {evaluation.relevance_score}/10")
            self.log_message("INFO", f"创新影响: {evaluation.innovation_impact}/10")
            self.log_message("INFO", f"实用性: {evaluation.practicality}/10")

            # 显示AI响应的详细内容
            if evaluation.reasoning:
                self.log_message("INFO", "AI评估理由:", "AI_RESPONSE")
                self.log_message("DEBUG", f"理由长度: {len(evaluation.reasoning)} 字符")

                # 如果理由太短或看起来是占位符，显示警告
                if len(evaluation.reasoning) < 20 or "详细理由" in evaluation.reasoning:
                    self.log_message("WARNING", f"AI评估理由可能不完整: {evaluation.reasoning}")
                    self.log_message("WARNING", "这可能是AI响应解析问题，建议检查原始响应")
                else:
                    self.log_message("INFO", evaluation.reasoning, "AI_RESPONSE")

            if evaluation.summary:
                self.log_message("INFO", "AI生成摘要:", "AI_RESPONSE")
                self.log_message("INFO", evaluation.summary, "AI_RESPONSE")

            if evaluation.key_insights:
                self.log_message("INFO", "关键洞察:", "AI_RESPONSE")
                for insight in evaluation.key_insights:
                    self.log_message("INFO", f"• {insight}", "AI_RESPONSE")

            if evaluation.highlights:
                self.log_message("INFO", "推荐亮点:", "AI_RESPONSE")
                for highlight in evaluation.highlights:
                    self.log_message("INFO", f"• {highlight}", "AI_RESPONSE")

            if evaluation.tags:
                self.log_message("INFO", f"相关标签: {', '.join(evaluation.tags)}", "AI_RESPONSE")

            if evaluation.detailed_analysis:
                self.log_message("INFO", "详细分析:", "AI_RESPONSE")
                for dimension, analysis in evaluation.detailed_analysis.items():
                    self.log_message("INFO", f"{dimension}: {analysis}", "AI_RESPONSE")

            if evaluation.recommendation_reason:
                self.log_message("INFO", "推荐理由:", "AI_RESPONSE")
                self.log_message("INFO", evaluation.recommendation_reason, "AI_RESPONSE")

            if evaluation.risk_assessment:
                self.log_message("WARNING", "风险评估:", "AI_RESPONSE")
                self.log_message("WARNING", evaluation.risk_assessment, "AI_RESPONSE")

            if evaluation.implementation_suggestions:
                self.log_message("INFO", "实施建议:", "AI_RESPONSE")
                for suggestion in evaluation.implementation_suggestions:
                    self.log_message("INFO", f"• {suggestion}", "AI_RESPONSE")

            self.log_message("INFO", "=" * 50)



            self.update_status("AI分析完成")

        except Exception as e:
            self.log_message("ERROR", f"处理AI分析结果时出错: {e}")

    def handle_ai_analysis_error(self, article, error_msg):
        """处理AI分析错误"""
        self.log_message("ERROR", error_msg)
        self.update_status("AI分析失败")
        messagebox.showerror("AI分析失败", error_msg)



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

    def export_inoreader_subscriptions(self):
        """导出Inoreader订阅源"""
        if not self.auth or not self.auth.is_authenticated():
            messagebox.showwarning("未登录", "请先登录Inoreader账户")
            return

        try:
            from .subscription_export_dialog import SubscriptionExportDialog
            # 传递RSS管理器的刷新回调
            refresh_callback = None
            if hasattr(self, 'rss_manager') and self.rss_manager:
                refresh_callback = self.rss_manager.refresh_rss_feed_list

            SubscriptionExportDialog(self.root, self.auth, refresh_callback)
        except Exception as e:
            messagebox.showerror("错误", f"打开导出对话框失败: {e}")

    def show_rss_manager(self):
        """显示RSS管理器"""
        # 切换到自定义RSS标签页
        try:
            # 找到自定义RSS标签页的索引
            for i in range(self.subscription_notebook.index("end")):
                tab_text = self.subscription_notebook.tab(i, "text")
                if "自定义RSS" in tab_text:
                    self.subscription_notebook.select(i)
                    break
        except Exception as e:
            messagebox.showerror("错误", f"切换到RSS管理器失败: {e}")

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

    def get_displayed_articles(self):
        """获取当前显示的文章列表"""
        filter_type = self.filter_var.get()

        # 如果当前显示的是筛选结果
        if filter_type == "filtered" and self.filtered_articles:
            print(f"📋 获取显示文章: 筛选结果 ({len(self.filtered_articles)} 篇)")
            return [result.article if hasattr(result, 'article') else result for result in self.filtered_articles]

        # 否则根据过滤条件从current_articles中筛选
        displayed_articles = []
        for article in self.current_articles:
            # 应用过滤条件
            if filter_type == "unread" and article.is_read:
                continue
            elif filter_type == "starred" and not article.is_starred:
                continue

            displayed_articles.append(article)

        print(f"📋 获取显示文章: {filter_type} ({len(displayed_articles)} 篇)")
        return displayed_articles

    def show_filter_dialog(self):
        """显示筛选对话框"""
        try:
            # 导入筛选对话框
            from .filter_dialog import FilterDialog

            # 创建并显示筛选对话框
            dialog = FilterDialog(self.root, self)
            result = dialog.show()

            if result:
                if result["mode"] == "batch":
                    # 批量筛选模式 - 传递筛选类型
                    self.batch_filter_articles(result["filter_type"])
                else:
                    # 单个订阅源筛选模式
                    self.filter_single_subscription(result["subscription"], result["filter_type"])

        except ImportError:
            messagebox.showerror("错误", "筛选功能模块未找到")
        except Exception as e:
            messagebox.showerror("错误", f"启动筛选失败: {e}")

    def filter_single_subscription(self, subscription, filter_type):
        """筛选单个订阅源"""
        try:
            # 检查是否是RSS订阅源
            if subscription.id.startswith("rss_"):
                # RSS订阅源处理
                self.update_status(f"正在获取RSS订阅源 {subscription.title} 的文章...")

                # 从RSS管理器获取文章
                if hasattr(self, 'rss_manager') and self.rss_manager.selected_feed:
                    rss_feed = self.rss_manager.selected_feed
                    rss_articles = rss_feed.articles

                    if not rss_articles:
                        messagebox.showinfo("提示", f"RSS订阅源 {subscription.title} 没有可筛选的文章")
                        return

                    # 将RSS文章转换为NewsArticle格式
                    from ..models.news import NewsArticle, NewsAuthor
                    articles = []
                    for rss_article in rss_articles:
                        if not rss_article.is_read:  # 只处理未读文章
                            news_article = NewsArticle(
                                id=rss_article.id,
                                title=rss_article.title,
                                summary=rss_article.summary or "",
                                content=rss_article.content or rss_article.summary or "",
                                url=rss_article.url,
                                published=rss_article.published,
                                updated=rss_article.published,  # RSS文章通常没有更新时间，使用发布时间
                                author=NewsAuthor(name=rss_article.author or "未知作者") if rss_article.author else None,
                                categories=[],
                                is_read=rss_article.is_read,
                                is_starred=False,
                                feed_title=rss_feed.title
                            )
                            articles.append(news_article)
                else:
                    messagebox.showwarning("警告", "无法获取RSS订阅源文章")
                    return
            else:
                # Inoreader订阅源处理
                self.update_status(f"正在获取 {subscription.title} 的文章...")
                articles = self.news_service.get_articles_by_feed(
                    feed_id=subscription.id,
                    count=50,  # 获取最近50篇文章
                    exclude_read=True
                )

            if not articles:
                messagebox.showinfo("提示", f"订阅源 {subscription.title} 没有可筛选的文章")
                return

            # 执行筛选
            self.update_status(f"开始筛选 {subscription.title} 的 {len(articles)} 篇文章...")
            self.quick_filter_with_articles(articles, filter_type)

        except Exception as e:
            messagebox.showerror("错误", f"筛选订阅源失败: {e}")

    def quick_filter_with_articles(self, articles, filter_type):
        """使用指定文章列表进行筛选"""
        # 更新筛选类型选择器
        self.filter_type_var.set(filter_type)

        # 显示筛选类型说明
        filter_descriptions = {
            "keyword": "使用关键词快速筛选，速度快，适合大批量处理",
            "ai": "使用AI智能评估，准确度高，适合精准筛选",
            "chain": "关键词+AI综合筛选，平衡速度和准确性"
        }

        description = filter_descriptions.get(filter_type, "")

        # 显示确认对话框（仅对AI筛选，因为消耗资源）
        if filter_type == "ai":
            confirm_msg = f"将对 {len(articles)} 篇文章进行智能筛选。\n\n{description}\n\n是否继续？"
            if not messagebox.askyesno("确认智能筛选", confirm_msg):
                return

        # 筛选类型显示名称
        filter_type_names = {
            "keyword": "关键词筛选",
            "ai": "智能筛选",
            "chain": "综合筛选"
        }
        filter_name = filter_type_names.get(filter_type, filter_type)

        self.update_status(f"开始{filter_name}: {len(articles)}篇文章")

        # 显示进度对话框并执行筛选
        progress_dialog = FilterProgressDialog(
            self.root,
            articles,
            filter_type
        )

        # 获取筛选结果
        if progress_dialog.result and not progress_dialog.cancelled:
            self.filter_result = progress_dialog.result

            # 安全地提取文章对象
            self.filtered_articles = []
            for r in self.filter_result.selected_articles:
                try:
                    if hasattr(r, 'article'):
                        # CombinedFilterResult 对象
                        self.filtered_articles.append(r.article)
                    elif hasattr(r, 'title'):
                        # 直接是 NewsArticle 对象
                        self.filtered_articles.append(r)
                    else:
                        print(f"⚠️ 未知的筛选结果类型: {type(r)}")
                        print(f"   对象属性: {dir(r)}")
                except Exception as e:
                    print(f"❌ 提取文章对象失败: {e}")
                    print(f"   结果对象类型: {type(r)}")
                    continue

            print(f"✅ 成功提取 {len(self.filtered_articles)} 篇筛选文章")
            self.display_mode = "filtered"

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
            self.update_status("筛选失败")

    def batch_filter_articles(self, preset_filter_type=None):
        """批量筛选文章"""
        try:
            # 导入批量筛选对话框
            from .batch_filter_dialog import BatchFilterDialog

            # 创建并显示批量筛选配置对话框
            dialog = BatchFilterDialog(self.root)

            # 如果有预设的筛选类型，设置到对话框中
            if preset_filter_type:
                dialog.filter_type_var.set(preset_filter_type)
                print(f"🔧 设置批量筛选类型为: {preset_filter_type}")

            result = dialog.show()

            if result:
                # 用户确认了批量筛选配置，执行筛选
                print(f"📋 批量筛选配置: 筛选类型={result.filter_type}")
                self.execute_batch_filter(result)

        except ImportError:
            messagebox.showerror("错误", "批量筛选功能模块未找到")
        except Exception as e:
            messagebox.showerror("错误", f"启动批量筛选失败: {e}")

    def execute_batch_filter(self, config):
        """执行批量筛选"""
        try:
            from .batch_filter_progress_dialog import BatchFilterProgressDialog

            # 根据当前活动的标签页选择合适的批量筛选管理器
            current_tab = self.subscription_notebook.tab(self.subscription_notebook.select(), "text")

            if current_tab == "自定义RSS":
                # 使用自定义RSS批量筛选管理器
                from ..services.batch_filter_service import custom_rss_batch_filter_manager
                manager = custom_rss_batch_filter_manager
                print("使用自定义RSS批量筛选管理器")
            else:
                # 使用Inoreader批量筛选管理器
                from ..services.batch_filter_service import BatchFilterManager
                manager = BatchFilterManager(self.auth)
                print("使用Inoreader批量筛选管理器")

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
                print(f"🔄 开始集成批量筛选结果: {len(batch_articles)} 篇文章")

                # 自动显示批量筛选结果（不再询问用户）
                # 用户既然执行了批量筛选，就是想看到结果

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

                # 设置筛选结果 - 安全地提取文章对象
                self.filtered_articles = []
                for r in combined_results:
                    try:
                        if hasattr(r, 'article'):
                            # CombinedFilterResult 对象
                            self.filtered_articles.append(r.article)
                        elif hasattr(r, 'title'):
                            # 直接是 NewsArticle 对象
                            self.filtered_articles.append(r)
                        else:
                            print(f"⚠️ 批量筛选结果未知类型: {type(r)}")
                            continue
                    except Exception as e:
                        print(f"❌ 提取批量筛选文章失败: {e}")
                        continue

                print(f"✅ 批量筛选成功提取 {len(self.filtered_articles)} 篇文章")
                self.filter_result = filter_result

                # 启用筛选结果选项
                self.filtered_radio.config(state=tk.NORMAL)

                # 切换到筛选结果视图
                self.filter_var.set("filtered")
                self.display_mode = "filtered"

                # 更新文章列表显示
                self.update_filtered_article_list()

                # 更新状态
                self.update_status(f"已显示批量筛选结果: {len(self.filtered_articles)} 篇文章")

        except Exception as e:
            messagebox.showerror("错误", f"集成批量筛选结果失败: {e}")

    def handle_batch_filter_error(self, error_msg):
        """处理批量筛选错误"""
        messagebox.showerror("批量筛选失败", f"批量筛选过程中发生错误:\n{error_msg}")
        self.update_status("批量筛选失败")

    def quick_filter(self, filter_type: str):
        """快速筛选文章"""
        # 获取当前显示的文章列表
        displayed_articles = self.get_displayed_articles()

        # 检查是否有文章
        if not displayed_articles:
            messagebox.showinfo("提示", "当前没有可筛选的文章")
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

        # 获取当前显示模式的描述
        current_filter = self.filter_var.get()
        filter_mode_descriptions = {
            "all": "全部文章",
            "unread": "未读文章",
            "starred": "星标文章",
            "filtered": "已筛选文章"
        }
        current_mode_desc = filter_mode_descriptions.get(current_filter, "当前显示的文章")

        # 显示确认对话框（仅对AI筛选，因为消耗资源）
        if filter_type == "ai":
            confirm_msg = f"将对{current_mode_desc}中的 {len(displayed_articles)} 篇文章进行智能筛选。\n\n{description}\n\n是否继续？"
            if not messagebox.askyesno("确认智能筛选", confirm_msg):
                return

        # 筛选类型显示名称
        filter_type_names = {
            "keyword": "关键词筛选",
            "ai": "智能筛选",
            "chain": "综合筛选"
        }
        filter_name = filter_type_names.get(filter_type, filter_type)

        self.update_status(f"开始{filter_name}: 从{current_mode_desc}({len(displayed_articles)}篇)中筛选")

        # 显示进度对话框并执行筛选
        progress_dialog = FilterProgressDialog(
            self.root,
            displayed_articles,  # 使用当前显示的文章列表
            filter_type
        )

        # 获取筛选结果
        print(f"筛选对话框关闭，结果: {progress_dialog.result is not None}, 取消: {progress_dialog.cancelled}")

        if progress_dialog.result and not progress_dialog.cancelled:
            self.filter_result = progress_dialog.result

            # 安全地提取文章对象
            self.filtered_articles = []
            for r in self.filter_result.selected_articles:
                try:
                    if hasattr(r, 'article'):
                        # CombinedFilterResult 对象
                        self.filtered_articles.append(r.article)
                    elif hasattr(r, 'title'):
                        # 直接是 NewsArticle 对象
                        self.filtered_articles.append(r)
                    else:
                        print(f"⚠️ 未知的筛选结果类型: {type(r)}")
                        continue
                except Exception as e:
                    print(f"❌ 提取文章对象失败: {e}")
                    continue

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

                # 获取筛选分数和AI分析信息
                ai_score_text = ""
                final_score_text = ""
                ai_summary = ""
                ai_tags = ""

                if self.filter_result and i < len(self.filter_result.selected_articles):
                    combined_result = self.filter_result.selected_articles[i]

                    # 显示AI分数
                    if combined_result.ai_result and combined_result.ai_result.evaluation:
                        ai_score = combined_result.ai_result.evaluation.total_score
                        ai_score_text = f"{ai_score}/30"

                        # 获取AI分析信息
                        evaluation = combined_result.ai_result.evaluation
                        ai_summary = evaluation.summary[:50] + "..." if len(evaluation.summary) > 50 else evaluation.summary
                        ai_tags = ", ".join(evaluation.tags[:3])  # 显示前3个标签

                    # 显示综合分数
                    final_score_text = f"{combined_result.final_score:.3f}"

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
                    ai_score_text,
                    final_score_text,
                    ai_summary,
                    ai_tags
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

        # 创建RSS管理器，传入文章回调函数、订阅源选择回调和认证信息
        self.rss_manager = RSSManager(rss_frame, self.on_rss_articles_loaded, self.auth, self.on_rss_subscription_selected)

    def on_rss_subscription_selected(self, rss_feed):
        """处理RSS订阅源选择事件"""
        # 将RSS订阅源转换为Subscription格式并设置为当前选中的订阅源
        from ..models.subscription import Subscription

        if rss_feed:
            # 创建一个模拟的Subscription对象来兼容现有的筛选逻辑
            subscription = Subscription(
                id=f"rss_{rss_feed.id}",  # 添加前缀以区分RSS订阅源
                title=rss_feed.title,
                url=rss_feed.url,
                html_url=rss_feed.link or rss_feed.url,
                icon_url=None,
                categories=[],
                first_item_msec=None,
                sort_id=None
            )
            self.selected_subscription = subscription
            print(f"🔄 RSS订阅源已选中: {subscription.title}")
        else:
            self.selected_subscription = None
            print("🔄 RSS订阅源选择已清除")

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
