"""
主窗口界面
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from typing import List, Optional


from ..models.news import NewsArticle
from .filter_config_dialog import FilterConfigDialog
from .filter_progress_dialog import FilterProgressDialog, FilterMetricsDialog
from .rss_manager import RSSManager
from .panels.preference_analysis_panel import PreferenceAnalysisPanel
from ..services.filter_service import get_filter_service
from ..services.preference_analysis_service import PreferenceAnalysisService
# from .ai_analysis_dialog import AIAnalysisDialog  # 不再需要，改为直接在日志中显示


class MainWindow:
    """主窗口类"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("新闻订阅工具 - News Selector")
        self.root.geometry("1600x800")
        
        # 数据
        self.current_articles: List[NewsArticle] = []
        self.filtered_articles: List[NewsArticle] = []  # 筛选后的文章
        self.filter_result = None  # 筛选结果
        self.display_mode = "all"  # 显示模式: "all" 或 "filtered"
        self.selected_subscription = None  # 当前选中的订阅源

        self.filter_service = get_filter_service()
        self.preference_analysis_service = PreferenceAnalysisService()
        # 同步Agent配置到FilterService
        self.sync_agent_config_on_startup()

        # 创建界面
        self.create_widgets()

        # 自动加载上次的筛选结果缓存
        self.check_and_prompt_cache_loading()

        self.update_status("RSS新闻订阅工具已启动")

    def sync_agent_config_on_startup(self):
        """应用启动时同步Agent配置到FilterService"""
        try:
            from src.config.agent_config import agent_config_manager
            # 获取当前Agent配置
            current_config = agent_config_manager.get_current_config()
            if current_config and current_config.api_config:
                # 同步API配置到FilterService
                self.filter_service.update_config("ai",
                    api_key=current_config.api_config.api_key,
                    model_name=current_config.api_config.model_name,
                    base_url=current_config.api_config.base_url
                )
                # 重置AI筛选器缓存以使用新配置
                self.filter_service.reset_ai_filter()
                print(f"✅ 启动时已同步Agent配置 '{current_config.config_name}' 到FilterService")
            else:
                print("⚠️  启动时没有找到有效的Agent配置")
        except Exception as e:
            print(f"❌ 启动时同步Agent配置失败: {e}")

    def check_and_prompt_cache_loading(self):
        """自动加载缓存的筛选结果"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()

            # 检查是否有有效的缓存
            if cache.has_cached_result(session_id="main_window"):
                cache_info = cache.get_cache_info()
                if cache_info and not cache_info['is_expired']:
                    # 延迟自动加载缓存，确保主窗口已完全加载
                    self.root.after(1000, lambda: self._auto_load_cache(cache_info))

        except Exception as e:
            pass

    def _auto_load_cache(self, cache_info):
        """自动加载缓存的筛选结果"""
        try:
            age_hours = cache_info['age_hours']
            article_count = cache_info['article_count']

            # 格式化时间显示
            if age_hours < 1:
                time_str = f"{age_hours * 60:.0f}分钟前"
            elif age_hours < 24:
                time_str = f"{age_hours:.1f}小时前"
            else:
                time_str = f"{age_hours / 24:.1f}天前"

            # 自动加载缓存
            success = self.load_cached_filter_result()
            if success:
                self.update_status(f"已自动恢复筛选结果：{article_count}篇文章 ({time_str})")
            else:
                self.update_status("缓存加载失败")

        except Exception as e:
            pass

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
        file_menu.add_command(label="导入RSS源", command=self.import_rss_feeds)
        file_menu.add_command(label="导出RSS源", command=self.export_rss_feeds)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        

        # 导出菜单
        export_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="导出", menu=export_menu)
        export_menu.add_command(label="导出表格", command=self.show_table_export_dialog)
        export_menu.add_command(label="批量导出", command=self.show_batch_export_dialog)

        # 工具菜单
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="工具", menu=tools_menu)
        tools_menu.add_command(label="批量筛选", command=self.show_batch_filter_dialog)
        tools_menu.add_separator()
        tools_menu.add_command(label="加载筛选缓存", command=self.load_filter_cache_menu)
        tools_menu.add_command(label="清理筛选缓存", command=self.clear_filter_result_cache)
        tools_menu.add_command(label="缓存信息", command=self.show_cache_info)

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

        # 创建自定义RSS标签页
        self.create_custom_rss_subscription_tab()

        # 创建偏好分析标签页
        self.create_preference_analysis_tab()
    
    def create_preference_analysis_tab(self):
        """创建偏好分析标签页"""
        self.preference_analysis_frame = PreferenceAnalysisPanel(self.subscription_notebook)
        self.subscription_notebook.add(self.preference_analysis_frame, text="偏好分析")

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

        # AI语义去重按钮
        ttk.Button(filter_buttons_frame, text="AI语义去重",
                  command=self.apply_ai_semantic_deduplication).pack(side=tk.LEFT, padx=(0, 5))

        # 显示所有文章按钮
        ttk.Button(filter_action_frame, text="显示全部", command=self.show_all_articles).pack(side=tk.LEFT, padx=(5, 0))
        
        # 翻译按钮
        ttk.Button(filter_action_frame, text="🌐 翻译", command=self.translate_selected_article).pack(side=tk.LEFT, padx=(5, 0))

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
        self.article_context_menu.add_command(label="📖 查看详情", command=self.view_article_detail)
        self.article_context_menu.add_command(label="🤖 查看AI分析", command=self.view_ai_analysis)
        self.article_context_menu.add_command(label="🧪 AI分析", command=self.analyze_article_with_ai)
        self.article_context_menu.add_command(label="🌐 打开原文", command=self.open_article_url)
        self.article_context_menu.add_separator()
        self.article_context_menu.add_command(label="✅ 标记为已读", command=self.mark_as_read)
        self.article_context_menu.add_command(label="⭕ 标记为未读", command=self.mark_as_unread)
        self.article_context_menu.add_separator()
        self.article_context_menu.add_command(label="⭐ 加星标", command=self.toggle_star)
    
    def create_status_bar(self):
        """创建状态栏"""
        # 创建状态栏框架
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # 主状态标签
        self.status_bar = ttk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 缓存状态标签
        self.cache_status_label = ttk.Label(status_frame, text="", relief=tk.SUNKEN, anchor=tk.E, width=20)
        self.cache_status_label.pack(side=tk.RIGHT)

        # 初始化缓存状态显示
        self.update_cache_status()

    def update_status(self, message: str):
        """更新状态栏"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()

    def update_cache_status(self):
        """更新缓存状态显示"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()

            if cache.has_cached_result(session_id="main_window"):
                cache_info = cache.get_cache_info()
                if cache_info and not cache_info['is_expired']:
                    age_hours = cache_info['age_hours']
                    article_count = cache_info['article_count']

                    # 格式化时间显示
                    if age_hours < 1:
                        time_str = f"{age_hours * 60:.0f}分钟前"
                    elif age_hours < 24:
                        time_str = f"{age_hours:.1f}小时前"
                    else:
                        time_str = f"{age_hours / 24:.1f}天前"

                    cache_text = f"📂 缓存: {article_count}篇 ({time_str})"
                    self.cache_status_label.config(text=cache_text)
                else:
                    self.cache_status_label.config(text="📂 缓存: 已过期")
            else:
                self.cache_status_label.config(text="📂 缓存: 无")

        except Exception as e:
            print(f"❌ 更新缓存状态失败: {e}")
            self.cache_status_label.config(text="📂 缓存: 错误")

    def update_login_status(self):
        """更新登录状态（已废弃）"""
        self.update_status("RSS新闻订阅工具")

    def login(self):
        """登录（已废弃）"""
        messagebox.showinfo("提示", "登录功能已移除，现在使用RSS订阅功能")

    def logout(self):
        """登出（已废弃）"""
        messagebox.showinfo("提示", "登出功能已移除，现在使用RSS订阅功能")

    def refresh_subscriptions(self):
        """刷新订阅源列表（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能来管理订阅源")

    def update_subscription_list(self, subscriptions_with_unread):
        """更新订阅源列表UI（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能")

    def refresh_news(self):
        """刷新新闻列表（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能来获取新闻")

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

            # 尝试获取AI分析结果
            ai_score_text = ""
            try:
                from ..utils.ai_analysis_storage import ai_analysis_storage
                analysis_record = ai_analysis_storage.get_analysis(article)
                if analysis_record:
                    ai_score_text = f"{analysis_record.evaluation.total_score}/30"
            except Exception as e:
                # 如果获取AI分析失败，保持空字符串
                pass

            # 添加到列表
            self.article_tree.insert("", tk.END, values=(
                article.get_display_title(50),
                article.feed_title or "未知",
                article.published.strftime("%m-%d %H:%M"),
                status_text,
                ai_score_text,  # 显示AI分数（如果有的话）
                "",  # 普通文章没有综合分数
                "",  # 普通文章没有AI摘要
                ""   # 普通文章没有AI标签
            ))

    def search_subscriptions(self, event=None):
        """搜索订阅源（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能来搜索订阅源")

    def search_articles(self, event=None):
        """搜索文章"""
        keyword = self.article_search_var.get().strip()
        if not keyword:
            self.filter_articles()
            return

        if not self.current_articles:
            messagebox.showinfo("提示", "请先加载文章")
            return

        # 在当前文章中搜索（简单的标题和内容匹配）
        matched_articles = []
        keyword_lower = keyword.lower()
        for article in self.current_articles:
            if (keyword_lower in article.title.lower() or
                keyword_lower in (article.summary or "").lower() or
                keyword_lower in (article.content or "").lower()):
                matched_articles.append(article)

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
        """订阅源选择事件（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能")

    def load_subscription_articles(self, subscription):
        """加载指定订阅源的文章（已废弃）"""
        messagebox.showinfo("提示", "请使用RSS管理功能来查看文章")

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
            context_menu.add_command(label="🤖 查看AI分析", command=self.view_ai_analysis)
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

                # 执行AI评估（获取原始响应）
                self.log_message("DEBUG", "正在调用AI客户端进行评估...")

                # 检查客户端是否支持原始响应方法
                if hasattr(client, 'evaluate_article_with_raw_response'):
                    evaluation, raw_response = client.evaluate_article_with_raw_response(article)
                else:
                    # 降级到普通方法
                    evaluation = client.evaluate_article(article)
                    raw_response = "该AI客户端不支持原始响应获取"

                self.log_message("DEBUG", "AI客户端评估完成")

                # 在主线程中更新UI
                self.root.after(0, lambda: self.handle_ai_analysis_result(article, evaluation, raw_response))

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

    def handle_ai_analysis_result(self, article, evaluation, raw_response=None):
        """处理AI分析结果"""
        try:
            self.log_message("INFO", f"AI分析完成: {article.title[:50]}")
            self.log_message("INFO", f"总分: {evaluation.total_score}/30 (置信度: {evaluation.confidence:.2f})")
            self.log_message("INFO", f"政策相关性: {evaluation.relevance_score}/10")
            self.log_message("INFO", f"创新影响: {evaluation.innovation_impact}/10")
            self.log_message("INFO", f"实用性: {evaluation.practicality}/10")

            # 显示原始AI响应
            if raw_response:
                self.log_message("INFO", "=" * 30 + " AI原始响应 " + "=" * 30, "AI_RESPONSE")
                self.log_message("INFO", raw_response, "AI_RESPONSE")
                self.log_message("INFO", "=" * 75, "AI_RESPONSE")

            self.log_message("INFO", "=" * 50)

            # 更新文章列表中的AI分数
            self.update_article_ai_score_in_list(article, evaluation)

            self.update_status("AI分析完成")

        except Exception as e:
            self.log_message("ERROR", f"处理AI分析结果时出错: {e}")

    def update_article_ai_score_in_list(self, article, evaluation):
        """更新文章列表中的AI分数"""
        try:
            # 查找对应的文章项
            article_found = False
            for item_index, item in enumerate(self.article_tree.get_children()):
                values = self.article_tree.item(item, 'values')
                if values and len(values) > 0:
                    # 多种匹配方式：
                    # 1. 通过索引匹配（最准确）
                    if hasattr(self, 'current_articles') and item_index < len(self.current_articles):
                        current_article = self.current_articles[item_index]
                        if current_article.id == article.id:
                            article_found = True
                        elif current_article.title == article.title:
                            article_found = True

                    # 2. 通过标题匹配（备用方案）
                    if not article_found:
                        display_title = article.get_display_title(50) if hasattr(article, 'get_display_title') else article.title[:50]
                        if values[0] == display_title:
                            article_found = True

                    if article_found:
                        # 更新AI分数栏（第5列，索引为4）
                        ai_score_text = f"{evaluation.total_score}/30"

                        # 获取当前的值并更新AI分数
                        current_values = list(values)
                        if len(current_values) > 4:
                            current_values[4] = ai_score_text
                        else:
                            # 如果列数不够，扩展列表
                            while len(current_values) <= 4:
                                current_values.append("")
                            current_values[4] = ai_score_text

                        # 更新树视图项
                        self.article_tree.item(item, values=current_values)

                        self.log_message("INFO", f"已更新文章AI分数: {article.title[:50]} -> {ai_score_text}")
                        break

            if not article_found:
                self.log_message("WARNING", f"未找到对应的文章项进行AI分数更新: {article.title[:50]}")

        except Exception as e:
            self.log_message("ERROR", f"更新文章AI分数时出错: {e}")

    def handle_ai_analysis_error(self, article, error_msg):
        """处理AI分析错误"""
        self.log_message("ERROR", error_msg)
        self.update_status("AI分析失败")
        messagebox.showerror("AI分析失败", error_msg)



    def toggle_star(self):
        """切换星标状态"""
        if not self.current_article:
            return

        # 星标功能已废弃
        messagebox.showinfo("提示", "星标功能已移除")

    def update_star_button(self):
        """更新星标按钮"""
        if self.current_article:
            self.star_button.config(text="移除星标" if self.current_article.is_starred else "加星标")

    def mark_article_read(self, article: NewsArticle):
        """标记文章为已读"""
        # 简单地标记为已读，不调用API
        article.is_read = True

    def mark_as_read(self):
        """标记为已读"""
        selection = self.article_tree.selection()
        if not selection:
            return

        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]

            # 简单地标记为已读
            article.is_read = True
            self.filter_articles()
            self.update_status("标记为已读")

    def view_ai_analysis(self):
        """查看文章的AI分析结果"""
        selection = self.article_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一篇文章")
            return

        # 获取选中的文章
        article = self.get_selected_article()
        if not article:
            messagebox.showwarning("警告", "无法获取选中的文章")
            return

        # 检查是否有AI分析结果
        from ..utils.ai_analysis_storage import ai_analysis_storage

        try:
            analysis_record = ai_analysis_storage.get_analysis(article)
            if analysis_record:
                # 显示AI分析结果
                self.show_ai_analysis_dialog(article, analysis_record)
            else:
                # 没有分析结果，询问是否进行AI分析
                result = messagebox.askyesno(
                    "AI分析",
                    f"文章「{article.title[:50]}...」还没有AI分析结果。\n\n是否现在进行AI分析？"
                )
                if result:
                    self.analyze_article_with_ai()
        except Exception as e:
            messagebox.showerror("错误", f"获取AI分析结果失败: {e}")

    def show_ai_analysis_dialog(self, article, analysis_record):
        """显示AI分析结果对话框"""
        # 创建新窗口
        dialog = tk.Toplevel(self.root)
        dialog.title(f"AI分析结果 - {article.title[:50]}...")
        dialog.geometry("800x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # 创建主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 文章标题
        title_label = ttk.Label(main_frame, text=article.title, font=("Arial", 12, "bold"), wraplength=750)
        title_label.pack(anchor=tk.W, pady=(0, 10))

        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # 评分概览标签页
        self.create_score_overview_tab(notebook, analysis_record)

        # 原始响应标签页
        self.create_raw_response_tab(notebook, analysis_record)

        # 关闭按钮
        close_button = ttk.Button(main_frame, text="关闭", command=dialog.destroy)
        close_button.pack(pady=(10, 0))

    def mark_as_unread(self):
        """标记为未读"""
        selection = self.article_tree.selection()
        if not selection:
            return

        item_index = self.article_tree.index(selection[0])
        if item_index < len(self.current_articles):
            article = self.current_articles[item_index]

            # 简单地标记为未读
            article.is_read = False
            self.filter_articles()
            self.update_status("标记为未读")

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

基于自定义RSS的新闻订阅和管理工具

功能特性:
• RSS订阅源管理
• 智能文章筛选
• AI文章分析
• 批量筛选处理
• 文章搜索和过滤
• 多种筛选算法

开发: News Selector Team
"""
        messagebox.showinfo("关于", about_text)

    def export_inoreader_subscriptions(self):
        """导出Inoreader订阅源（已废弃）"""
        messagebox.showinfo("提示", "Inoreader导出功能已移除，请使用RSS管理功能")

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
        # 订阅源列表已移除

        # 清空文章列表
        for item in self.article_tree.get_children():
            self.article_tree.delete(item)

        # 清空文章详情
        self.article_title_label.config(text="")
        self.article_info_label.config(text="")
        self.article_content.delete(1.0, tk.END)
        self.current_article = None

        # 重置搜索框
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
                # 获取测试模式设置
                test_mode = result.get("test_mode", False)
                
                if result["mode"] == "batch":
                    # 批量筛选模式 - 传递筛选类型和测试模式
                    self.batch_filter_articles(result["filter_type"], test_mode)
                else:
                    # 单个订阅源筛选模式
                    self.filter_single_subscription(result["subscription"], result["filter_type"], test_mode)

        except ImportError:
            messagebox.showerror("错误", "筛选功能模块未找到")
        except Exception as e:
            messagebox.showerror("错误", f"启动筛选失败: {e}")

    def filter_single_subscription(self, subscription, filter_type, test_mode=False):
        """筛选单个订阅源"""
        try:
            # 直接从RSS管理器获取当前选中的RSS订阅源
            if hasattr(self, 'rss_manager') and self.rss_manager.selected_feed:
                rss_feed = self.rss_manager.selected_feed
                self.update_status(f"正在获取RSS订阅源 {rss_feed.title} 的文章...")

                rss_articles = rss_feed.articles

                if not rss_articles:
                    messagebox.showinfo("提示", f"RSS订阅源 {rss_feed.title} 没有可筛选的文章")
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

                if not articles:
                    messagebox.showinfo("提示", f"RSS订阅源 {rss_feed.title} 没有可筛选的未读文章")
                    return

                # 执行筛选
                self.update_status(f"开始筛选 {rss_feed.title} 的 {len(articles)} 篇文章...")
                self.quick_filter_with_articles(articles, filter_type, test_mode)
            else:
                messagebox.showwarning("警告", "请先在RSS管理器中选择要筛选的订阅源")
                return

        except Exception as e:
            messagebox.showerror("错误", f"筛选订阅源失败: {e}")

    def quick_filter_with_articles(self, articles, filter_type, test_mode=False):
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
            filter_type,
            main_window=self,
            test_mode=test_mode
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

            # 保存筛选结果到缓存
            self.save_filter_result_to_cache()

            # 显示筛选结果摘要
            self.show_filter_summary()
        elif progress_dialog.cancelled:
            self.update_status("筛选已取消")
        else:
            self.update_status("筛选失败")

    def show_batch_filter_dialog(self):
        """显示批量筛选对话框（菜单调用）"""
        self.batch_filter_articles()

    def batch_filter_articles(self, preset_filter_type=None, test_mode=False):
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

            # 使用自定义RSS批量筛选管理器
            from ..services.batch_filter_service import custom_rss_batch_filter_manager
            manager = custom_rss_batch_filter_manager
            print("使用自定义RSS批量筛选管理器")

            # 创建进度对话框
            progress_dialog = BatchFilterProgressDialog(self.root)

            # 在后台线程中执行批量筛选
            def run_batch_filter():
                try:
                    result = manager.filter_subscriptions_batch(config, progress_dialog)
                    # 在主线程中处理结果
                    self.root.after(0, lambda r=result: self.handle_batch_filter_result(r))
                except Exception as e:
                    # 捕获异常信息，避免闭包问题
                    error_msg = str(e)
                    self.root.after(0, lambda msg=error_msg: self.handle_batch_filter_error(msg))
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

            # 保存筛选结果到缓存
            self.save_filter_result_to_cache()

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
            filter_type,
            main_window=self
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

            # 保存筛选结果到缓存
            self.save_filter_result_to_cache()

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

                    # 显示AI分数 - 优先从筛选结果获取，然后从缓存获取
                    evaluation = None
                    if combined_result.ai_result and combined_result.ai_result.evaluation:
                        evaluation = combined_result.ai_result.evaluation
                        print(f"   从筛选结果获取AI分数: {evaluation.total_score}/30")
                    else:
                        # 尝试从AI分析缓存获取
                        try:
                            from ..utils.ai_analysis_storage import ai_analysis_storage
                            analysis_record = ai_analysis_storage.get_analysis(article)
                            if analysis_record:
                                evaluation = analysis_record.evaluation
                                print(f"   从缓存获取AI分数: {evaluation.total_score}/30")
                        except Exception as e:
                            print(f"   获取缓存AI分数失败: {e}")

                    if evaluation:
                        ai_score = evaluation.total_score
                        ai_score_text = f"{ai_score}/30"

                        # 获取AI分析信息
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

    def apply_ai_semantic_deduplication(self):
        """对当前筛选结果应用AI语义去重"""
        try:
            # 检查是否有筛选结果
            if not self.filtered_articles:
                messagebox.showwarning("提示", "请先执行筛选，然后再进行AI语义去重")
                return

            # 检查筛选结果数量
            if len(self.filtered_articles) < 2:
                messagebox.showinfo("提示", f"当前只有{len(self.filtered_articles)}篇文章，无需去重")
                return

            print(f"🧠 开始对筛选结果进行AI语义去重...")
            print(f"   原始筛选结果: {len(self.filtered_articles)}篇文章")

            # 显示进度对话框
            progress_dialog = self._create_progress_dialog("AI语义去重", "正在分析文章语义相似度...")

            def run_ai_deduplication():
                try:
                    from ..services.ai_deduplication_service import ai_semantic_deduplicate
                    from ..filters.base import CombinedFilterResult

                    # 将筛选结果转换为CombinedFilterResult格式（如果需要）
                    combined_results = []
                    for article in self.filtered_articles:
                        if isinstance(article, CombinedFilterResult):
                            combined_results.append(article)
                        else:
                            # 创建CombinedFilterResult包装
                            combined_result = CombinedFilterResult(
                                article=article,
                                keyword_result=None,
                                ai_result=None,
                                final_score=0.8,  # 默认分数
                                selected=True,
                                rejection_reason=None
                            )
                            combined_results.append(combined_result)

                    # 执行AI语义去重
                    deduplicated_results, stats = ai_semantic_deduplicate(
                        combined_results,
                        semantic_threshold=0.85,
                        time_window_hours=48
                    )

                    return deduplicated_results, stats

                except Exception as e:
                    print(f"❌ AI语义去重失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return None, None

            # 在后台线程中执行AI去重
            import threading
            result_container = [None, None]

            def worker():
                result_container[0], result_container[1] = run_ai_deduplication()
                # 关闭进度对话框
                progress_dialog.destroy()

            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()

            # 显示进度对话框（阻塞）
            progress_dialog.wait_window()

            # 获取结果
            deduplicated_results, stats = result_container[0], result_container[1]

            if deduplicated_results is None:
                messagebox.showerror("错误", "AI语义去重失败，请检查AI服务配置")
                return

            # 更新筛选结果
            original_count = len(self.filtered_articles)
            self.filtered_articles = [r.article if hasattr(r, 'article') else r for r in deduplicated_results]

            # 更新显示
            self.update_filtered_article_list()

            # 显示去重统计
            removed_count = original_count - len(self.filtered_articles)

            print(f"✅ AI语义去重完成:")
            print(f"   原始文章: {original_count}篇")
            print(f"   保留文章: {len(self.filtered_articles)}篇")
            print(f"   去除重复: {removed_count}篇")
            print(f"   语义去重率: {stats.get('semantic_deduplication_rate', 0):.1%}")

            # 显示详细结果对话框
            self._show_ai_deduplication_result_dialog(stats, original_count, len(self.filtered_articles))

        except Exception as e:
            print(f"❌ AI语义去重异常: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", f"AI语义去重失败: {str(e)}")

    def _create_progress_dialog(self, title, message):
        """创建进度对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # 内容
        ttk.Label(dialog, text=message, font=("Arial", 10)).pack(pady=20)

        # 进度条
        progress = ttk.Progressbar(dialog, mode='indeterminate')
        progress.pack(pady=10, padx=20, fill=tk.X)
        progress.start()

        # 提示
        ttk.Label(dialog, text="请稍候...", foreground="gray").pack(pady=5)

        return dialog

    def _show_ai_deduplication_result_dialog(self, stats, original_count, final_count):
        """显示AI语义去重结果对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("AI语义去重结果")
        dialog.geometry("600x500")
        dialog.resizable(True, True)
        dialog.transient(self.root)

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

        # 主框架
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 统计信息
        stats_frame = ttk.LabelFrame(main_frame, text="去重统计", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        removed_count = original_count - final_count
        dedup_rate = (removed_count / original_count * 100) if original_count > 0 else 0

        ttk.Label(stats_frame, text=f"原始文章数: {original_count}篇").pack(anchor=tk.W)
        ttk.Label(stats_frame, text=f"保留文章数: {final_count}篇").pack(anchor=tk.W)
        ttk.Label(stats_frame, text=f"去除重复数: {removed_count}篇").pack(anchor=tk.W)
        ttk.Label(stats_frame, text=f"语义去重率: {dedup_rate:.1f}%").pack(anchor=tk.W)
        ttk.Label(stats_frame, text=f"语义组数: {stats.get('semantic_groups_count', 0)}个").pack(anchor=tk.W)

        # 语义组详情
        if stats.get('semantic_groups'):
            groups_frame = ttk.LabelFrame(main_frame, text="语义组详情", padding=10)
            groups_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # 创建文本框显示详情
            text_frame = ttk.Frame(groups_frame)
            text_frame.pack(fill=tk.BOTH, expand=True)

            text_widget = tk.Text(text_frame, wrap=tk.WORD, height=15)
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
            text_widget.configure(yscrollcommand=scrollbar.set)

            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # 填充语义组信息
            for i, group in enumerate(stats.get('semantic_groups', []), 1):
                text_widget.insert(tk.END, f"语义组 {i}: {group.get('core_topic', '未知主题')}\n")
                text_widget.insert(tk.END, f"  保留文章: {group.get('kept_article', {}).get('title', '未知')}\n")
                text_widget.insert(tk.END, f"  发布时间: {group.get('kept_article', {}).get('published', '未知')}\n")
                text_widget.insert(tk.END, f"  筛选分数: {group.get('kept_article', {}).get('final_score', 0):.2f}\n")
                text_widget.insert(tk.END, f"  去除文章:\n")

                for removed in group.get('removed_articles', []):
                    text_widget.insert(tk.END, f"    - {removed.get('title', '未知')}\n")
                    text_widget.insert(tk.END, f"      时间: {removed.get('published', '未知')}\n")
                    text_widget.insert(tk.END, f"      分数: {removed.get('final_score', 0):.2f}\n")

                text_widget.insert(tk.END, "\n")

            text_widget.config(state=tk.DISABLED)

        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="确定", command=dialog.destroy).pack(side=tk.RIGHT)

    def update_all_articles_ai_scores(self, all_ai_results):
        """更新所有文章的AI得分显示"""
        try:
            # 创建文章ID到评估结果的映射
            ai_scores_map = {}
            for result in all_ai_results:
                if hasattr(result, 'article') and hasattr(result, 'evaluation'):
                    article_id = result.article.id
                    ai_scores_map[article_id] = result.evaluation

            print(f"📊 准备更新 {len(ai_scores_map)} 篇文章的AI得分")

            # 更新当前文章列表中的AI得分显示
            if hasattr(self, 'article_tree') and self.article_tree:
                # 遍历树形控件中的所有项目
                for item in self.article_tree.get_children():
                    try:
                        # 获取项目对应的文章
                        item_index = self.article_tree.index(item)

                        # 根据当前显示模式获取对应的文章列表
                        if self.display_mode == "filtered" and self.filtered_articles:
                            if item_index < len(self.filtered_articles):
                                article = self.filtered_articles[item_index]
                            else:
                                continue
                        else:
                            if item_index < len(self.current_articles):
                                article = self.current_articles[item_index]
                            else:
                                continue

                        # 检查是否有AI评估结果
                        if article.id in ai_scores_map:
                            evaluation = ai_scores_map[article.id]
                            ai_score_text = f"{evaluation.total_score}/30"

                            # 获取当前项目的值
                            current_values = list(self.article_tree.item(item, 'values'))

                            # 更新AI得分列（第5列，索引为4）
                            if len(current_values) > 4:
                                current_values[4] = ai_score_text
                            else:
                                # 如果列数不够，扩展列表
                                while len(current_values) <= 4:
                                    current_values.append("")
                                current_values[4] = ai_score_text

                            self.article_tree.item(item, values=current_values)

                    except Exception as e:
                        print(f"⚠️ 更新单个文章AI得分失败: {e}")
                        continue

            print(f"✅ AI得分更新完成")

        except Exception as e:
            print(f"❌ 更新AI得分时出错: {e}")
            import traceback
            traceback.print_exc()

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

        # 清除筛选结果缓存
        self.clear_filter_result_cache()

        # 禁用筛选选项并切换到全部
        self.filtered_radio.config(state=tk.DISABLED)
        self.filter_var.set("all")

        self.filter_articles()  # 重新显示所有文章

    def clear_cache(self):
        """清除所有缓存（已废弃）"""
        messagebox.showinfo("提示", "缓存功能已移除")

    def show_cache_status(self):
        """显示缓存状态（已废弃）"""
        messagebox.showinfo("提示", "缓存功能已移除")



    def show_all_articles(self):
        """显示所有文章"""
        self.display_mode = "all"
        self.filter_var.set("all")

        self.filter_articles()  # 重新显示所有文章
        self.update_status(f"显示所有文章: {len(self.current_articles)} 篇")



    def create_custom_rss_subscription_tab(self):
        """创建自定义RSS订阅标签页"""
        rss_frame = ttk.Frame(self.subscription_notebook)
        self.subscription_notebook.add(rss_frame, text="自定义RSS")

        # 创建RSS管理器，传入文章回调函数、订阅源选择回调
        self.rss_manager = RSSManager(rss_frame, self.on_rss_articles_loaded, None, self.on_rss_subscription_selected)

    def on_rss_subscription_selected(self, rss_feed):
        """处理RSS订阅源选择事件"""
        # RSS订阅源选择处理
        if rss_feed:
            self.selected_subscription = rss_feed
            print(f"🔄 RSS订阅源已选中: {rss_feed.title}")
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

    def create_score_overview_tab(self, notebook, analysis_record):
        """创建评分概览标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="评分概览")

        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        evaluation = analysis_record.evaluation

        # 总分显示
        total_frame = ttk.LabelFrame(main_frame, text="总体评分", padding="10")
        total_frame.pack(fill=tk.X, pady=(0, 10))

        total_score_label = ttk.Label(total_frame, text=f"{evaluation.total_score}/30",
                                     font=("Arial", 24, "bold"))
        total_score_label.pack()

        confidence_label = ttk.Label(total_frame, text=f"置信度: {evaluation.confidence:.2f}")
        confidence_label.pack()

        # 分项评分
        scores_frame = ttk.LabelFrame(main_frame, text="分项评分", padding="10")
        scores_frame.pack(fill=tk.X, pady=(0, 10))

        scores_data = [
            ("政策相关性", evaluation.relevance_score, 10),
            ("创新影响", evaluation.innovation_impact, 10),
            ("实用性", evaluation.practicality, 10)
        ]

        for i, (name, score, max_score) in enumerate(scores_data):
            score_frame = ttk.Frame(scores_frame)
            score_frame.pack(fill=tk.X, pady=2)

            ttk.Label(score_frame, text=f"{name}:", width=12).pack(side=tk.LEFT)
            ttk.Label(score_frame, text=f"{score}/{max_score}").pack(side=tk.LEFT, padx=(10, 0))

            # 进度条
            progress = ttk.Progressbar(score_frame, length=200, maximum=max_score, value=score)
            progress.pack(side=tk.LEFT, padx=(10, 0))

        # 模型信息
        info_frame = ttk.LabelFrame(main_frame, text="分析信息", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        info_text = f"AI模型: {analysis_record.ai_model}\n"
        info_text += f"分析时间: {analysis_record.created_at}\n"
        info_text += f"处理耗时: {analysis_record.processing_time:.2f}秒\n"
        info_text += f"缓存状态: {'是' if analysis_record.cached else '否'}"

        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)

        # 推理过程
        if evaluation.reasoning:
            reasoning_frame = ttk.LabelFrame(main_frame, text="推理过程", padding="10")
            reasoning_frame.pack(fill=tk.BOTH, expand=True)

            reasoning_text = tk.Text(reasoning_frame, wrap=tk.WORD, height=8, state="disabled")
            reasoning_text.pack(fill=tk.BOTH, expand=True)

            reasoning_text.config(state="normal")
            reasoning_text.insert("1.0", evaluation.reasoning)
            reasoning_text.config(state="disabled")

    def create_raw_response_tab(self, notebook, analysis_record):
        """创建原始响应标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="原始响应")

        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 原始响应文本
        response_text = tk.Text(main_frame, wrap=tk.WORD, state="disabled", font=("Consolas", 10))
        response_text.pack(fill=tk.BOTH, expand=True)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=response_text.yview)
        scrollbar.pack(side="right", fill="y")
        response_text.configure(yscrollcommand=scrollbar.set)

        # 插入原始响应内容
        response_text.config(state="normal")
        response_text.insert("1.0", analysis_record.raw_response or "无原始响应数据")
        response_text.config(state="disabled")

    def show_table_export_dialog(self):
        """显示表格导出对话框"""
        try:
            from .dialogs.table_export_dialog import TableExportDialog

            # 调试信息
            print(f"🔍 检查筛选结果状态:")
            print(f"   filter_result 存在: {self.filter_result is not None}")
            if self.filter_result:
                print(f"   selected_articles 存在: {hasattr(self.filter_result, 'selected_articles')}")
                if hasattr(self.filter_result, 'selected_articles'):
                    print(f"   selected_articles 数量: {len(self.filter_result.selected_articles) if self.filter_result.selected_articles else 0}")
            print(f"   filtered_articles 数量: {len(self.filtered_articles)}")
            print(f"   display_mode: {self.display_mode}")

            # 检查多种可能的筛选结果来源
            filter_result_to_use = None

            # 1. 检查主要的筛选结果
            if self.filter_result and hasattr(self.filter_result, 'selected_articles') and self.filter_result.selected_articles:
                filter_result_to_use = self.filter_result
                print(f"✅ 使用主要筛选结果: {len(self.filter_result.selected_articles)} 篇文章")

            # 2. 如果没有主要筛选结果，但有筛选后的文章列表，创建一个临时的筛选结果
            elif self.filtered_articles:
                print(f"🔄 从筛选文章列表创建临时筛选结果: {len(self.filtered_articles)} 篇文章")
                filter_result_to_use = self._create_temp_filter_result_from_articles(self.filtered_articles)

            # 3. 如果都没有，显示提示
            if not filter_result_to_use:
                msg = "没有可导出的筛选结果。\n\n请先执行智能筛选：\n"
                msg += "1. 点击工具栏的'筛选'按钮\n"
                msg += "2. 或使用菜单'筛选' → '智能筛选'\n"
                msg += "3. 或使用菜单'筛选' → '批量筛选'\n\n"
                msg += f"调试信息:\n"
                msg += f"- filter_result: {self.filter_result is not None}\n"
                msg += f"- filtered_articles: {len(self.filtered_articles)} 篇\n"
                msg += f"- display_mode: {self.display_mode}"
                messagebox.showwarning("提示", msg)
                return

            # 显示导出对话框，传递筛选结果
            dialog = TableExportDialog(self.root, filter_result_to_use)
            dialog.show()

        except ImportError:
            messagebox.showerror("错误", "表格导出功能未安装")
        except Exception as e:
            messagebox.showerror("错误", f"打开导出对话框失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def _create_temp_filter_result_from_articles(self, articles):
        """从文章列表创建临时的筛选结果"""
        try:
            from ..filters.base import FilterChainResult, CombinedFilterResult, ArticleTag
            from datetime import datetime

            # 为每篇文章创建CombinedFilterResult
            combined_results = []
            for article in articles:
                # 创建基本标签
                tags = [ArticleTag("filtered", 1.0, 1.0, "manual")]

                # 创建组合筛选结果
                combined_result = CombinedFilterResult(
                    article=article,
                    keyword_result=None,
                    ai_result=None,
                    final_score=1.0,
                    selected=True,
                    rejection_reason=None,
                    tags=tags
                )
                combined_results.append(combined_result)

            # 创建FilterChainResult
            now = datetime.now()
            filter_result = FilterChainResult(
                total_articles=len(articles),
                processing_start_time=now,
                processing_end_time=now,
                keyword_filtered_count=len(articles),
                ai_filtered_count=len(articles),
                final_selected_count=len(articles),
                selected_articles=combined_results,
                total_processing_time=0.0
            )

            return filter_result

        except Exception as e:
            print(f"❌ 创建临时筛选结果失败: {e}")
            return None

    def save_filter_result_to_cache(self):
        """保存筛选结果到缓存"""
        try:
            if not self.filtered_articles:
                return

            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()
            success = cache.save_filter_result(
                filtered_articles=self.filtered_articles,
                filter_result=self.filter_result,
                session_id="main_window"
            )

            if success:
                print(f"✅ 筛选结果已保存到缓存: {len(self.filtered_articles)}篇文章")
                # 更新缓存状态显示
                self.update_cache_status()

        except Exception as e:
            print(f"❌ 保存筛选结果到缓存失败: {e}")

    def load_cached_filter_result(self):
        """加载缓存的筛选结果"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()
            cached_data = cache.load_filter_result(session_id="main_window")

            if cached_data:
                # 恢复筛选结果
                self.filtered_articles = cached_data["filtered_articles"]
                self.filter_result = cached_data["filter_result"]
                self.display_mode = "filtered"

                # 启用筛选选项并切换到筛选视图
                self.filtered_radio.config(state=tk.NORMAL)
                self.filter_var.set("filtered")

                # 更新文章列表显示
                self.update_filtered_article_list()

                # 更新缓存状态显示
                self.update_cache_status()

                return True
            else:
                return False

        except Exception as e:
            print(f"❌ 加载筛选结果缓存失败: {e}")
            return False

    def clear_filter_result_cache(self):
        """清除筛选结果缓存"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()
            success = cache.clear_cache(session_id="main_window")

            if success:
                print("🗑️ 筛选结果缓存已清除")
                self.update_status("筛选结果缓存已清除")
                # 更新缓存状态显示
                self.update_cache_status()

            return success

        except Exception as e:
            print(f"❌ 清除筛选结果缓存失败: {e}")
            return False

    def load_filter_cache_menu(self):
        """从菜单加载筛选缓存"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache
            import tkinter.messagebox as messagebox

            cache = get_filter_result_cache()

            # 检查是否有有效的缓存
            if not cache.has_cached_result(session_id="main_window"):
                messagebox.showinfo("提示", "没有找到有效的筛选结果缓存")
                return

            cache_info = cache.get_cache_info()
            if not cache_info:
                messagebox.showwarning("警告", "无法获取缓存信息")
                return

            if cache_info['is_expired']:
                messagebox.showwarning("警告", "筛选结果缓存已过期")
                return

            # 显示缓存信息并询问是否加载
            age_hours = cache_info['age_hours']
            article_count = cache_info['article_count']

            # 格式化时间显示
            if age_hours < 1:
                time_str = f"{age_hours * 60:.0f}分钟前"
            elif age_hours < 24:
                time_str = f"{age_hours:.1f}小时前"
            else:
                time_str = f"{age_hours / 24:.1f}天前"

            message = f"找到筛选结果缓存：\n\n" \
                     f"📄 文章数量：{article_count}篇\n" \
                     f"⏰ 缓存时间：{time_str}\n" \
                     f"📊 文件大小：{cache_info['file_size'] / 1024:.1f} KB\n\n" \
                     f"是否要加载这些筛选结果？"

            if messagebox.askyesno("加载筛选缓存", message, icon='question'):
                success = self.load_cached_filter_result()
                if success:
                    messagebox.showinfo("成功", f"已成功加载筛选结果：{article_count}篇文章")
                    self.update_status(f"已从缓存加载筛选结果：{article_count}篇文章")
                else:
                    messagebox.showerror("失败", "缓存加载失败")

        except Exception as e:
            print(f"❌ 加载筛选缓存失败: {e}")
            messagebox.showerror("错误", f"加载筛选缓存失败: {e}")

    def show_cache_info(self):
        """显示缓存信息对话框"""
        try:
            from ..utils.filter_result_cache import get_filter_result_cache

            cache = get_filter_result_cache()
            cache_info = cache.get_cache_info()

            # 创建信息对话框
            dialog = tk.Toplevel(self.root)
            dialog.title("筛选结果缓存信息")
            dialog.geometry("500x400")
            dialog.resizable(True, True)
            dialog.transient(self.root)

            # 居中显示
            dialog.update_idletasks()
            x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
            y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
            dialog.geometry(f"+{x}+{y}")

            # 主框架
            main_frame = ttk.Frame(dialog)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # 缓存信息
            info_frame = ttk.LabelFrame(main_frame, text="缓存信息", padding=10)
            info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            if cache_info:
                # 显示缓存详情
                ttk.Label(info_frame, text=f"会话ID: {cache_info['session_id']}").pack(anchor=tk.W)
                ttk.Label(info_frame, text=f"保存时间: {cache_info['saved_at'].strftime('%Y-%m-%d %H:%M:%S')}").pack(anchor=tk.W)
                ttk.Label(info_frame, text=f"缓存时长: {cache_info['age_hours']:.1f} 小时").pack(anchor=tk.W)
                ttk.Label(info_frame, text=f"文章数量: {cache_info['article_count']} 篇").pack(anchor=tk.W)
                ttk.Label(info_frame, text=f"文件大小: {cache_info['file_size'] / 1024:.1f} KB").pack(anchor=tk.W)
                ttk.Label(info_frame, text=f"文件路径: {cache_info['file_path']}").pack(anchor=tk.W)

                status_text = "已过期" if cache_info['is_expired'] else "有效"
                status_color = "red" if cache_info['is_expired'] else "green"
                status_label = ttk.Label(info_frame, text=f"状态: {status_text}")
                status_label.pack(anchor=tk.W)

                # 添加操作按钮
                button_frame = ttk.Frame(info_frame)
                button_frame.pack(fill=tk.X, pady=(10, 0))

                def reload_cache():
                    """重新加载缓存"""
                    success = self.load_cached_filter_result()
                    if success:
                        messagebox.showinfo("成功", "缓存已重新加载")
                        dialog.destroy()
                    else:
                        messagebox.showwarning("失败", "缓存加载失败")

                def clear_cache():
                    """清除缓存"""
                    if messagebox.askyesno("确认", "确定要清除筛选结果缓存吗？"):
                        success = self.clear_filter_result_cache()
                        if success:
                            messagebox.showinfo("成功", "缓存已清除")
                            dialog.destroy()
                        else:
                            messagebox.showerror("失败", "缓存清除失败")

                ttk.Button(button_frame, text="重新加载", command=reload_cache).pack(side=tk.LEFT, padx=(0, 5))
                ttk.Button(button_frame, text="清除缓存", command=clear_cache).pack(side=tk.LEFT, padx=(5, 0))

            else:
                ttk.Label(info_frame, text="没有找到筛选结果缓存", foreground="gray").pack(anchor=tk.W)

            # 关闭按钮
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)

            ttk.Button(button_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT)

        except Exception as e:
            print(f"❌ 显示缓存信息失败: {e}")
            messagebox.showerror("错误", f"显示缓存信息失败: {str(e)}")

    def show_batch_export_dialog(self):
        """显示批量导出对话框"""
        try:
            from .dialogs.batch_export_dialog import BatchExportDialog

            # 调试信息
            print(f"🔍 检查批量导出数据状态:")
            print(f"   filter_result 存在: {self.filter_result is not None}")
            print(f"   filtered_articles 数量: {len(self.filtered_articles)}")

            # 优先使用筛选结果
            data_to_export = None

            if self.filter_result and hasattr(self.filter_result, 'selected_articles') and self.filter_result.selected_articles:
                data_to_export = self.filter_result
                print(f"✅ 使用筛选结果: {len(self.filter_result.selected_articles)} 篇文章")
            elif self.filtered_articles:
                # 从筛选文章创建临时结果
                data_to_export = self._create_temp_filter_result_from_articles(self.filtered_articles)
                print(f"🔄 使用筛选文章列表: {len(self.filtered_articles)} 篇文章")
            else:
                # 获取当前显示的文章
                articles = self.get_current_articles()
                if articles:
                    data_to_export = self._create_temp_filter_result_from_articles(articles)
                    print(f"🔄 使用当前文章: {len(articles)} 篇文章")

            if not data_to_export:
                msg = "没有可导出的文章。\n\n请先执行以下操作之一：\n"
                msg += "1. 使用RSS管理功能加载文章\n"
                msg += "2. 执行智能筛选获取筛选结果\n"
                msg += "3. 从订阅源加载新闻文章\n\n"
                msg += f"调试信息:\n"
                msg += f"- filter_result: {self.filter_result is not None}\n"
                msg += f"- filtered_articles: {len(self.filtered_articles)} 篇\n"
                msg += f"- current_articles: {len(self.current_articles)} 篇"
                messagebox.showwarning("提示", msg)
                return

            # 显示批量导出对话框
            dialog = BatchExportDialog(self.root, data_to_export)
            dialog.show()

        except ImportError:
            messagebox.showerror("错误", "批量导出功能未安装")
        except Exception as e:
            messagebox.showerror("错误", f"打开批量导出对话框失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def get_current_articles(self):
        """获取当前显示的文章列表"""
        # 根据当前显示模式返回相应的文章列表
        if self.display_mode == "filtered" and self.filtered_articles:
            print(f"📋 获取当前文章: 筛选结果 ({len(self.filtered_articles)} 篇)")
            return self.filtered_articles
        elif self.current_articles:
            print(f"📋 获取当前文章: 所有文章 ({len(self.current_articles)} 篇)")
            return self.current_articles
        else:
            # 如果内存中没有文章，尝试从文章树中获取
            articles = self._get_articles_from_tree()
            if articles:
                print(f"📋 获取当前文章: 从文章树获取 ({len(articles)} 篇)")
                return articles
            else:
                print(f"📋 获取当前文章: 无文章")
                return []

    def _get_articles_from_tree(self):
        """从文章树中获取文章对象"""
        articles = []

        # 检查是否有文章树项目
        tree_items = self.article_tree.get_children()
        if not tree_items:
            return articles

        # 根据当前显示模式获取文章
        if self.display_mode == "filtered" and self.filtered_articles:
            # 如果是筛选模式，直接返回筛选结果
            return self.filtered_articles
        elif self.current_articles:
            # 如果有当前文章列表，返回对应的文章
            for i in range(min(len(tree_items), len(self.current_articles))):
                articles.append(self.current_articles[i])

        return articles

    def import_rss_feeds(self):
        """导入RSS源"""
        try:
            from tkinter import filedialog
            import json
            
            # 选择导入文件
            filepath = filedialog.askopenfilename(
                title="选择RSS源文件",
                filetypes=[
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ]
            )
            
            if not filepath:
                return
            
            # 读取文件
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证文件格式
            if not isinstance(data, dict) or 'feeds' not in data:
                messagebox.showerror("错误", "无效的RSS源文件格式")
                return
            
            feeds_data = data['feeds']
            if not isinstance(feeds_data, list):
                messagebox.showerror("错误", "无效的RSS源数据格式")
                return
            
            # 获取RSS管理器
            if not hasattr(self, 'rss_manager'):
                messagebox.showerror("错误", "RSS管理器未初始化")
                return
            
            # 导入RSS源
            success_count = 0
            error_count = 0
            duplicate_count = 0
            
            for feed_data in feeds_data:
                try:
                    # 检查必要字段
                    if 'url' not in feed_data or 'title' not in feed_data:
                        error_count += 1
                        continue
                    
                    url = feed_data['url']
                    category = feed_data.get('category', '默认')
                    
                    # 尝试添加订阅
                    success, message = self.rss_manager.custom_rss_service.add_subscription(url, category)
                    
                    if success:
                        success_count += 1
                    elif "已存在" in message:
                        duplicate_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    print(f"导入RSS源失败: {e}")
                    error_count += 1
            
            # 刷新RSS源列表
            if hasattr(self.rss_manager, 'refresh_rss_feed_list'):
                self.rss_manager.refresh_rss_feed_list()
            
            # 显示结果
            result_msg = f"导入完成！\n\n"
            result_msg += f"成功导入: {success_count} 个RSS源\n"
            result_msg += f"重复跳过: {duplicate_count} 个RSS源\n"
            result_msg += f"导入失败: {error_count} 个RSS源"
            
            messagebox.showinfo("导入结果", result_msg)
            
        except Exception as e:
            messagebox.showerror("错误", f"导入RSS源失败: {str(e)}")
    
    def export_rss_feeds(self):
        """导出RSS源"""
        try:
            from tkinter import filedialog
            from datetime import datetime
            import json
            
            # 获取RSS管理器
            if not hasattr(self, 'rss_manager'):
                messagebox.showerror("错误", "RSS管理器未初始化")
                return
            
            # 获取所有RSS源
            feeds = self.rss_manager.custom_rss_service.get_all_subscriptions()
            
            if not feeds:
                messagebox.showinfo("提示", "没有可导出的RSS源")
                return
            
            # 选择保存路径
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rss_feeds_{timestamp}.json"
            
            filepath = filedialog.asksaveasfilename(
                title="保存RSS源文件",
                defaultextension=".json",
                filetypes=[
                    ("JSON文件", "*.json"),
                    ("所有文件", "*.*")
                ],
                initialvalue=filename
            )
            
            if not filepath:
                return
            
            # 准备导出数据
            export_data = {
                'exported_at': datetime.now().isoformat(),
                'version': '1.0',
                'total_feeds': len(feeds),
                'feeds': [feed.to_dict() for feed in feeds]
            }
            
            # 写入文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"导出完成！\n\n文件: {filepath}\n导出数量: {len(feeds)} 个RSS源")
            
        except Exception as e:
            messagebox.showerror("错误", f"导出RSS源失败: {str(e)}")

    def show_translation_test_dialog(self):
        """显示翻译测试对话框"""
        try:
            from .dialogs.translation_test_dialog import TranslationTestDialog
            dialog = TranslationTestDialog(self.root)
            dialog.show()
        except ImportError:
            # 如果没有专门的翻译测试对话框，使用简单的测试
            self._simple_translation_test()
        except Exception as e:
            messagebox.showerror("错误", f"打开翻译测试对话框失败: {str(e)}")
    
    def show_translation_settings_dialog(self):
        """显示翻译设置对话框"""
        try:
            from .dialogs.translation_settings_dialog import TranslationSettingsDialog
            dialog = TranslationSettingsDialog(self.root)
            dialog.show()
        except ImportError:
            # 如果没有专门的翻译设置对话框，显示简单信息
            self._show_translation_info()
        except Exception as e:
            messagebox.showerror("错误", f"打开翻译设置对话框失败: {str(e)}")
    
    def translate_selected_article(self):
        """翻译选中的文章"""
        try:
            # 获取选中的文章
            selected_items = self.article_tree.selection()
            if not selected_items:
                messagebox.showwarning("提示", "请先选择要翻译的文章")
                return
            
            # 获取文章索引
            item = selected_items[0]
            item_index = self.article_tree.index(item)
            
            # 获取对应的文章对象
            current_articles = self.get_current_articles()
            if item_index >= len(current_articles):
                messagebox.showerror("错误", "无法获取文章信息")
                return
            
            article = current_articles[item_index]
            
            # 执行翻译
            self._translate_article_content(article)
            
        except Exception as e:
            messagebox.showerror("错误", f"翻译文章失败: {str(e)}")
    
    def _simple_translation_test(self):
        """简单的翻译测试"""
        try:
            from ..services.translation_service import get_translation_service
            
            # 创建测试窗口
            test_window = tk.Toplevel(self.root)
            test_window.title("翻译测试")
            test_window.geometry("600x400")
            test_window.transient(self.root)
            test_window.grab_set()
            
            # 输入区域
            input_frame = ttk.LabelFrame(test_window, text="输入文本", padding="10")
            input_frame.pack(fill=tk.X, padx=10, pady=5)
            
            input_text = tk.Text(input_frame, height=4, wrap=tk.WORD)
            input_text.pack(fill=tk.X)
            input_text.insert(tk.END, "Hello, this is a test for translation service.")
            
            # 按钮区域
            button_frame = ttk.Frame(test_window)
            button_frame.pack(fill=tk.X, padx=10, pady=5)
            
            def translate_to_chinese():
                text = input_text.get("1.0", tk.END).strip()
                if text:
                    service = get_translation_service()
                    result = service.translate_to_chinese(text)
                    result_text.delete("1.0", tk.END)
                    result_text.insert(tk.END, result)
            
            def translate_to_english():
                text = input_text.get("1.0", tk.END).strip()
                if text:
                    service = get_translation_service()
                    result = service.translate_to_english(text)
                    result_text.delete("1.0", tk.END)
                    result_text.insert(tk.END, result)
            
            ttk.Button(button_frame, text="翻译为中文", command=translate_to_chinese).pack(side=tk.LEFT, padx=(0, 5))
            ttk.Button(button_frame, text="翻译为英文", command=translate_to_english).pack(side=tk.LEFT, padx=(5, 0))
            
            # 结果区域
            result_frame = ttk.LabelFrame(test_window, text="翻译结果", padding="10")
            result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            result_text = tk.Text(result_frame, height=6, wrap=tk.WORD, state=tk.NORMAL)
            result_text.pack(fill=tk.BOTH, expand=True)
            
        except Exception as e:
            messagebox.showerror("错误", f"翻译测试失败: {str(e)}")
    
    def _show_translation_info(self):
        """显示翻译信息"""
        try:
            from ..services.translation_service import get_translation_service
            
            service = get_translation_service()
            translator_type = type(service.translator).__name__
            
            info_msg = f"当前翻译服务信息:\n\n"
            info_msg += f"翻译器类型: {translator_type}\n"
            info_msg += f"支持语言: 中文 ⇄ 英文\n\n"
            
            if "DeepTranslator" in translator_type:
                info_msg += "✅ 使用 AI大模型翻译服务\n"
                info_msg += "• 免费使用，无需API密钥\n"
                info_msg += "• 支持多种翻译引擎\n"
                info_msg += "• 自动缓存翻译结果\n"
            elif "Mock" in translator_type:
                info_msg += "⚠️ 使用模拟翻译器\n"
                info_msg += "• 仅用于测试和降级\n"
                info_msg += "• 不提供真实翻译功能\n"
            
            info_msg += "\n使用方法:\n"
            info_msg += "1. 在文章列表中选择文章，点击'🌐 翻译'按钮\n"
            info_msg += "2. 在导出对话框中启用翻译功能\n"
            info_msg += "3. 使用'翻译测试'功能测试翻译服务"
            
            messagebox.showinfo("翻译服务信息", info_msg)
            
        except Exception as e:
            messagebox.showerror("错误", f"获取翻译信息失败: {str(e)}")
    
    def _translate_article_content(self, article):
        """翻译文章内容"""
        try:
            from ..services.translation_service import get_translation_service
            
            # 创建翻译结果窗口
            result_window = tk.Toplevel(self.root)
            result_window.title(f"翻译结果 - {article.title[:50]}...")
            result_window.geometry("800x600")
            result_window.transient(self.root)
            
            # 创建笔记本控件
            notebook = ttk.Notebook(result_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 标题翻译标签页
            title_frame = ttk.Frame(notebook)
            notebook.add(title_frame, text="标题翻译")
            
            # 原标题
            ttk.Label(title_frame, text="原标题:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
            original_title = tk.Text(title_frame, height=3, wrap=tk.WORD)
            original_title.pack(fill=tk.X, padx=10, pady=(0, 10))
            original_title.insert(tk.END, article.title)
            original_title.config(state=tk.DISABLED)
            
            # 翻译标题
            ttk.Label(title_frame, text="翻译标题:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
            translated_title = tk.Text(title_frame, height=3, wrap=tk.WORD)
            translated_title.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # 摘要翻译标签页
            summary_frame = ttk.Frame(notebook)
            notebook.add(summary_frame, text="摘要翻译")
            
            # 原摘要
            ttk.Label(summary_frame, text="原摘要:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
            original_summary = tk.Text(summary_frame, height=6, wrap=tk.WORD)
            original_summary.pack(fill=tk.X, padx=10, pady=(0, 10))
            original_summary.insert(tk.END, getattr(article, 'summary', '无摘要'))
            original_summary.config(state=tk.DISABLED)
            
            # 翻译摘要
            ttk.Label(summary_frame, text="翻译摘要:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
            translated_summary = tk.Text(summary_frame, height=6, wrap=tk.WORD)
            translated_summary.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            # 执行翻译
            def do_translation():
                try:
                    service = get_translation_service()
                    
                    # 翻译标题
                    title_result = service.detect_and_translate(article.title, "zh" if self._is_english(article.title) else "en")
                    translated_title.delete("1.0", tk.END)
                    translated_title.insert(tk.END, title_result.get("translated", "翻译失败"))
                    
                    # 翻译摘要
                    if hasattr(article, 'summary') and article.summary:
                        summary_result = service.detect_and_translate(article.summary, "zh" if self._is_english(article.summary) else "en")
                        translated_summary.delete("1.0", tk.END)
                        translated_summary.insert(tk.END, summary_result.get("translated", "翻译失败"))
                    else:
                        translated_summary.delete("1.0", tk.END)
                        translated_summary.insert(tk.END, "无摘要内容")
                    
                    messagebox.showinfo("完成", "翻译完成！")
                    
                except Exception as e:
                    messagebox.showerror("错误", f"翻译失败: {str(e)}")
            
            # 按钮区域
            button_frame = ttk.Frame(result_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            
            ttk.Button(button_frame, text="开始翻译", command=do_translation).pack(side=tk.LEFT)
            ttk.Button(button_frame, text="关闭", command=result_window.destroy).pack(side=tk.RIGHT)
            
            # 自动执行翻译
            result_window.after(500, do_translation)
            
        except Exception as e:
            messagebox.showerror("错误", f"创建翻译窗口失败: {str(e)}")
    
    def _is_english(self, text):
        """简单判断文本是否为英文"""
        if not text:
            return False
        # 统计英文字符比例
        english_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total_chars = sum(1 for c in text if c.isalpha())
        return total_chars > 0 and english_chars / total_chars > 0.5

    def run(self):
        """运行主循环"""
        self.root.mainloop()
