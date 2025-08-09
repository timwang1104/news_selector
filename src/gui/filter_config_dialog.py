"""
筛选配置对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any, Optional
from ..services.filter_service import get_filter_service
from ..config.agent_config import agent_config_manager, AgentConfig, AgentAPIConfig, AgentPromptConfig


class FilterConfigDialog:
    """筛选配置对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("筛选配置")
        self.dialog.geometry("850x700")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # 配置变量
        self.config_vars = {}
        self.keywords_data = {}  # 存储关键词数据
        self.current_agent_config: Optional[AgentConfig] = None

        # 创建界面
        self.create_widgets()
        self.load_current_config()
        self.center_window()

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
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 关键词筛选配置
        self.create_keyword_config_tab(notebook)
        
        # AI筛选配置
        self.create_ai_config_tab(notebook)
        
        # 筛选链配置
        self.create_chain_config_tab(notebook)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="确定", command=self.save_config).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="重置", command=self.reset_config).pack(side=tk.LEFT)
    
    def create_keyword_config_tab(self, notebook):
        """创建关键词筛选配置标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="关键词筛选")
        
        # 滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 基本设置
        basic_frame = ttk.LabelFrame(scrollable_frame, text="基本设置")
        basic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 筛选阈值
        ttk.Label(basic_frame, text="筛选阈值 (0.0-1.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'keyword_threshold' not in self.config_vars:
            self.config_vars['keyword_threshold'] = tk.DoubleVar()
        threshold_scale = ttk.Scale(basic_frame, from_=0.0, to=1.0,
                                  variable=self.config_vars['keyword_threshold'],
                                  orient=tk.HORIZONTAL, length=200)
        threshold_scale.grid(row=0, column=1, padx=5, pady=5)

        threshold_label = ttk.Label(basic_frame, text="0.65")
        threshold_label.grid(row=0, column=2, padx=5, pady=5)

        # 更新标签显示
        def update_threshold_label(*args):
            threshold_label.config(text=f"{self.config_vars['keyword_threshold'].get():.2f}")
        self.config_vars['keyword_threshold'].trace('w', update_threshold_label)

        # 最大结果数
        ttk.Label(basic_frame, text="最大结果数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'max_results' not in self.config_vars:
            self.config_vars['max_results'] = tk.IntVar()
        ttk.Spinbox(basic_frame, from_=10, to=500, textvariable=self.config_vars['max_results'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 最少匹配关键词数
        ttk.Label(basic_frame, text="最少匹配关键词数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        if 'min_matches' not in self.config_vars:
            self.config_vars['min_matches'] = tk.IntVar()
        ttk.Spinbox(basic_frame, from_=1, to=10, textvariable=self.config_vars['min_matches'],
                   width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 高级设置
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="高级设置")
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 大小写敏感
        if 'case_sensitive' not in self.config_vars:
            self.config_vars['case_sensitive'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="大小写敏感",
                       variable=self.config_vars['case_sensitive']).pack(anchor=tk.W, padx=5, pady=2)

        # 模糊匹配
        if 'fuzzy_match' not in self.config_vars:
            self.config_vars['fuzzy_match'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用模糊匹配",
                       variable=self.config_vars['fuzzy_match']).pack(anchor=tk.W, padx=5, pady=2)

        # 单词边界检查
        if 'word_boundary' not in self.config_vars:
            self.config_vars['word_boundary'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="单词边界检查",
                       variable=self.config_vars['word_boundary']).pack(anchor=tk.W, padx=5, pady=2)

        # 关键词管理
        keywords_frame = ttk.LabelFrame(scrollable_frame, text="关键词管理")
        keywords_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 关键词编辑按钮
        keyword_buttons_frame = ttk.Frame(keywords_frame)
        keyword_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(keyword_buttons_frame, text="编辑关键词",
                  command=self.open_keyword_editor).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons_frame, text="导入关键词",
                  command=self.import_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons_frame, text="导出关键词",
                  command=self.export_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons_frame, text="重置为默认",
                  command=self.reset_keywords).pack(side=tk.LEFT)

        # 关键词统计信息
        self.keyword_info_label = ttk.Label(keywords_frame, text="", foreground="gray")
        self.keyword_info_label.pack(anchor=tk.W, padx=5, pady=2)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_ai_config_tab(self, notebook):
        """创建AI筛选配置标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="AI筛选")

        # 创建滚动框架
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # AI配置管理
        self.create_ai_config_management(scrollable_frame)

        # AI服务设置
        self.create_ai_service_settings(scrollable_frame)

        # 筛选设置
        self.create_ai_filter_settings(scrollable_frame)

        # 高级设置
        self.create_ai_advanced_settings(scrollable_frame)

        # 提示词设置
        self.create_ai_prompt_settings(scrollable_frame)

        # 性能设置
        self.create_ai_performance_settings(scrollable_frame)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_ai_config_management(self, parent):
        """创建AI配置管理区域"""
        config_frame = ttk.LabelFrame(parent, text="配置管理")
        config_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # 配置选择
        ttk.Label(config_frame, text="当前配置:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'current_agent_config' not in self.config_vars:
            self.config_vars['current_agent_config'] = tk.StringVar()
        self.agent_config_combo = ttk.Combobox(config_frame, textvariable=self.config_vars['current_agent_config'],
                                              width=25, state="readonly")
        self.agent_config_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        self.agent_config_combo.bind("<<ComboboxSelected>>", self.on_agent_config_change)

        # 配置管理按钮
        button_frame = ttk.Frame(config_frame)
        button_frame.grid(row=0, column=2, padx=(10, 5), pady=5)

        ttk.Button(button_frame, text="新建", command=self.new_agent_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="编辑", command=self.edit_agent_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="删除", command=self.delete_agent_config, width=8).pack(side=tk.LEFT, padx=2)

        # 加载配置列表
        self.load_agent_config_list()

        # 配置网格权重
        config_frame.grid_columnconfigure(1, weight=1)

    def create_ai_service_settings(self, parent):
        """创建AI服务设置区域"""
        ai_frame = ttk.LabelFrame(parent, text="AI服务设置")
        ai_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # 服务提供商
        ttk.Label(ai_frame, text="服务提供商:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'provider' not in self.config_vars:
            self.config_vars['provider'] = tk.StringVar()
        provider_combo = ttk.Combobox(ai_frame, textvariable=self.config_vars['provider'],
                                     values=["openai", "siliconflow", "volcengine", "moonshot", "custom"],
                                     width=18, state="readonly")
        provider_combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        provider_combo.bind("<<ComboboxSelected>>", self.on_provider_change)

        # API Key
        ttk.Label(ai_frame, text="API Key:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'api_key' not in self.config_vars:
            self.config_vars['api_key'] = tk.StringVar()
        api_key_entry = ttk.Entry(ai_frame, textvariable=self.config_vars['api_key'],
                                 width=35, show="*")
        api_key_entry.grid(row=1, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)

        # Base URL
        ttk.Label(ai_frame, text="Base URL:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        if 'base_url' not in self.config_vars:
            self.config_vars['base_url'] = tk.StringVar()
        ttk.Entry(ai_frame, textvariable=self.config_vars['base_url'], width=35).grid(
            row=2, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)

        # 模型名称
        ttk.Label(ai_frame, text="模型名称:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        if 'model_name' not in self.config_vars:
            self.config_vars['model_name'] = tk.StringVar()
        self.model_combo = ttk.Combobox(ai_frame, textvariable=self.config_vars['model_name'], width=28)
        self.model_combo.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # 根据提供商更新模型列表
        self.update_model_list()

        # 配置网格权重
        ai_frame.grid_columnconfigure(1, weight=1)

    def create_ai_filter_settings(self, parent):
        """创建AI筛选设置区域"""
        filter_frame = ttk.LabelFrame(parent, text="筛选设置")
        filter_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # 最大请求数
        ttk.Label(filter_frame, text="最大请求数:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'max_requests' not in self.config_vars:
            self.config_vars['max_requests'] = tk.IntVar()
        ttk.Spinbox(filter_frame, from_=1, to=200, textvariable=self.config_vars['max_requests'],
                   width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # 分数阈值筛选
        ttk.Label(filter_frame, text="最低分数阈值:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'min_score_threshold' not in self.config_vars:
            self.config_vars['min_score_threshold'] = tk.IntVar()
        ttk.Spinbox(filter_frame, from_=0, to=30, textvariable=self.config_vars['min_score_threshold'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 分数阈值说明
        ttk.Label(filter_frame, text="(只选择超过此分数的文章)", font=("TkDefaultFont", 8)).grid(
            row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # 批量筛选最大文章数
        ttk.Label(filter_frame, text="批量最大文章数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        if 'batch_max_articles' not in self.config_vars:
            self.config_vars['batch_max_articles'] = tk.IntVar()
        ttk.Spinbox(filter_frame, from_=1, to=200, textvariable=self.config_vars['batch_max_articles'],
                   width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # 批量筛选说明
        ttk.Label(filter_frame, text="(批量筛选时达到此数量自动停止)", font=("TkDefaultFont", 8)).grid(
            row=2, column=2, sticky=tk.W, padx=5, pady=5)

    def create_ai_advanced_settings(self, parent):
        """创建AI高级设置区域"""
        advanced_frame = ttk.LabelFrame(parent, text="高级设置")
        advanced_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # Temperature
        ttk.Label(advanced_frame, text="Temperature (0.0-2.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'temperature' not in self.config_vars:
            self.config_vars['temperature'] = tk.DoubleVar()
        ttk.Spinbox(advanced_frame, from_=0.0, to=2.0, increment=0.1,
                   textvariable=self.config_vars['temperature'], width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        # Max Tokens
        ttk.Label(advanced_frame, text="Max Tokens:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'max_tokens' not in self.config_vars:
            self.config_vars['max_tokens'] = tk.IntVar()
        ttk.Spinbox(advanced_frame, from_=100, to=4000, textvariable=self.config_vars['max_tokens'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Timeout
        ttk.Label(advanced_frame, text="超时时间(秒):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        if 'timeout' not in self.config_vars:
            self.config_vars['timeout'] = tk.IntVar()
        ttk.Spinbox(advanced_frame, from_=10, to=120, textvariable=self.config_vars['timeout'],
                   width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Retry Times
        ttk.Label(advanced_frame, text="重试次数:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        if 'retry_times' not in self.config_vars:
            self.config_vars['retry_times'] = tk.IntVar()
        ttk.Spinbox(advanced_frame, from_=0, to=5, textvariable=self.config_vars['retry_times'],
                   width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Proxy
        ttk.Label(advanced_frame, text="代理设置:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        if 'proxy' not in self.config_vars:
            self.config_vars['proxy'] = tk.StringVar()
        ttk.Entry(advanced_frame, textvariable=self.config_vars['proxy'], width=28).grid(
            row=4, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)

        # SSL验证
        if 'verify_ssl' not in self.config_vars:
            self.config_vars['verify_ssl'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用SSL验证",
                       variable=self.config_vars['verify_ssl']).grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # 配置网格权重
        advanced_frame.grid_columnconfigure(1, weight=1)

    def create_ai_performance_settings(self, parent):
        """创建AI性能设置区域"""
        perf_frame = ttk.LabelFrame(parent, text="性能设置")
        perf_frame.pack(fill=tk.X, padx=5)

        # 启用缓存
        if 'enable_cache' not in self.config_vars:
            self.config_vars['enable_cache'] = tk.BooleanVar()
        ttk.Checkbutton(perf_frame, text="启用缓存",
                       variable=self.config_vars['enable_cache']).pack(anchor=tk.W, padx=5, pady=2)

        # 启用降级策略
        if 'fallback_enabled' not in self.config_vars:
            self.config_vars['fallback_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(perf_frame, text="启用降级策略",
                       variable=self.config_vars['fallback_enabled']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 测试模式设置
        test_frame = ttk.Frame(perf_frame)
        test_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 启用测试模式
        if 'test_mode' not in self.config_vars:
            self.config_vars['test_mode'] = tk.BooleanVar()
        ttk.Checkbutton(test_frame, text="启用测试模式 (使用模拟数据，不调用AI API)",
                       variable=self.config_vars['test_mode']).pack(anchor=tk.W)
        
        # 测试模式延迟设置
        delay_frame = ttk.Frame(test_frame)
        delay_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(delay_frame, text="测试模式延迟(秒):").pack(side=tk.LEFT)
        if 'test_mode_delay' not in self.config_vars:
            self.config_vars['test_mode_delay'] = tk.DoubleVar()
        ttk.Spinbox(delay_frame, from_=0.0, to=5.0, increment=0.1,
                   textvariable=self.config_vars['test_mode_delay'], width=8).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Label(delay_frame, text="(模拟AI处理时间)", font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=(5, 0))

    def create_ai_prompt_settings(self, parent):
        """创建AI提示词设置区域"""
        prompt_frame = ttk.LabelFrame(parent, text="提示词配置")
        prompt_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # 提示词配置选择
        config_select_frame = ttk.Frame(prompt_frame)
        config_select_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(config_select_frame, text="提示词配置:").pack(side=tk.LEFT)
        self.config_vars['prompt_config_name'] = tk.StringVar()
        self.prompt_config_combo = ttk.Combobox(config_select_frame,
                                               textvariable=self.config_vars['prompt_config_name'],
                                               width=25, state="readonly")
        self.prompt_config_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.prompt_config_combo.bind("<<ComboboxSelected>>", self.on_prompt_config_change)

        # 提示词管理按钮
        prompt_button_frame = ttk.Frame(config_select_frame)
        prompt_button_frame.pack(side=tk.LEFT)

        ttk.Button(prompt_button_frame, text="编辑", command=self.edit_prompt_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(prompt_button_frame, text="新建", command=self.new_prompt_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(prompt_button_frame, text="删除", command=self.delete_prompt_config, width=8).pack(side=tk.LEFT, padx=2)

        # 提示词预览区域
        preview_frame = ttk.Frame(prompt_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 系统提示词预览
        ttk.Label(preview_frame, text="系统提示词预览:").pack(anchor=tk.W)
        self.system_prompt_preview = tk.Text(preview_frame, height=3, width=70, state="disabled", wrap=tk.WORD)
        self.system_prompt_preview.pack(fill=tk.BOTH, pady=(2, 5))

        # 评估提示词预览
        ttk.Label(preview_frame, text="评估提示词预览:").pack(anchor=tk.W)
        self.eval_prompt_preview = tk.Text(preview_frame, height=4, width=70, state="disabled", wrap=tk.WORD)
        self.eval_prompt_preview.pack(fill=tk.BOTH, expand=True, pady=(2, 5))

        # 加载提示词配置列表
        self.load_prompt_config_list()

    def create_ai_prompt_settings(self, parent):
        """创建AI提示词设置区域"""
        prompt_frame = ttk.LabelFrame(parent, text="提示词配置")
        prompt_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        # 提示词配置选择
        config_select_frame = ttk.Frame(prompt_frame)
        config_select_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(config_select_frame, text="提示词配置:").pack(side=tk.LEFT)
        self.config_vars['prompt_config_name'] = tk.StringVar()
        self.prompt_config_combo = ttk.Combobox(config_select_frame,
                                               textvariable=self.config_vars['prompt_config_name'],
                                               width=25, state="readonly")
        self.prompt_config_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.prompt_config_combo.bind("<<ComboboxSelected>>", self.on_prompt_config_change)

        # 提示词管理按钮
        prompt_button_frame = ttk.Frame(config_select_frame)
        prompt_button_frame.pack(side=tk.LEFT)

        ttk.Button(prompt_button_frame, text="编辑", command=self.edit_prompt_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(prompt_button_frame, text="新建", command=self.new_prompt_config, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(prompt_button_frame, text="删除", command=self.delete_prompt_config, width=8).pack(side=tk.LEFT, padx=2)

        # 提示词预览区域
        preview_frame = ttk.Frame(prompt_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 系统提示词预览
        ttk.Label(preview_frame, text="系统提示词预览:").pack(anchor=tk.W)
        self.system_prompt_preview = tk.Text(preview_frame, height=3, width=80, state="disabled", wrap=tk.WORD)
        self.system_prompt_preview.pack(fill=tk.X, pady=(2, 5))

        # 评估提示词预览
        ttk.Label(preview_frame, text="评估提示词预览:").pack(anchor=tk.W)
        self.eval_prompt_preview = tk.Text(preview_frame, height=4, width=80, state="disabled", wrap=tk.WORD)
        self.eval_prompt_preview.pack(fill=tk.X, pady=(2, 5))

        # 加载提示词配置列表
        self.load_prompt_config_list()
    
    def create_chain_config_tab(self, notebook):
        """创建筛选链配置标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="筛选链")
        
        # 筛选流程设置
        flow_frame = ttk.LabelFrame(frame, text="筛选流程")
        flow_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 启用关键词筛选
        if 'enable_keyword_filter' not in self.config_vars:
            self.config_vars['enable_keyword_filter'] = tk.BooleanVar()
        ttk.Checkbutton(flow_frame, text="启用关键词筛选",
                       variable=self.config_vars['enable_keyword_filter']).pack(anchor=tk.W, padx=5, pady=2)

        # 启用AI筛选
        if 'enable_ai_filter' not in self.config_vars:
            self.config_vars['enable_ai_filter'] = tk.BooleanVar()
        ttk.Checkbutton(flow_frame, text="启用AI筛选",
                       variable=self.config_vars['enable_ai_filter']).pack(anchor=tk.W, padx=5, pady=2)

        # 启用去重功能
        if 'enable_deduplication' not in self.config_vars:
            self.config_vars['enable_deduplication'] = tk.BooleanVar()
        ttk.Checkbutton(flow_frame, text="启用新闻去重",
                       variable=self.config_vars['enable_deduplication']).pack(anchor=tk.W, padx=5, pady=2)

        # 去重设置
        dedup_frame = ttk.LabelFrame(frame, text="去重设置")
        dedup_frame.pack(fill=tk.X, pady=(0, 10))

        # 相似度阈值
        ttk.Label(dedup_frame, text="相似度阈值 (0.0-1.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'dedup_threshold' not in self.config_vars:
            self.config_vars['dedup_threshold'] = tk.DoubleVar()
        dedup_scale = ttk.Scale(dedup_frame, from_=0.5, to=1.0,
                              variable=self.config_vars['dedup_threshold'],
                              orient=tk.HORIZONTAL, length=200)
        dedup_scale.grid(row=0, column=1, padx=5, pady=5)

        dedup_label = ttk.Label(dedup_frame, text="0.80")
        dedup_label.grid(row=0, column=2, padx=5, pady=5)

        def update_dedup_label(*args):
            dedup_label.config(text=f"{self.config_vars['dedup_threshold'].get():.2f}")
        self.config_vars['dedup_threshold'].trace('w', update_dedup_label)

        # 时间窗口
        ttk.Label(dedup_frame, text="时间窗口 (小时):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'dedup_time_window' not in self.config_vars:
            self.config_vars['dedup_time_window'] = tk.IntVar()
        ttk.Spinbox(dedup_frame, from_=12, to=168, textvariable=self.config_vars['dedup_time_window'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(dedup_frame, text="(12-168小时)").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)

        # AI语义去重设置
        ttk.Separator(dedup_frame, orient='horizontal').grid(row=2, column=0, columnspan=3, sticky='ew', pady=10)

        # AI语义去重开关
        if 'enable_ai_semantic_dedup' not in self.config_vars:
            self.config_vars['enable_ai_semantic_dedup'] = tk.BooleanVar()
        ttk.Checkbutton(dedup_frame, text="启用AI语义去重（筛选后深度去重）",
                       variable=self.config_vars['enable_ai_semantic_dedup']).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        # AI语义相似度阈值
        ttk.Label(dedup_frame, text="AI语义阈值 (0.7-1.0):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        if 'ai_semantic_threshold' not in self.config_vars:
            self.config_vars['ai_semantic_threshold'] = tk.DoubleVar()
        ai_semantic_scale = ttk.Scale(dedup_frame, from_=0.7, to=1.0,
                                    variable=self.config_vars['ai_semantic_threshold'],
                                    orient=tk.HORIZONTAL, length=200)
        ai_semantic_scale.grid(row=4, column=1, padx=5, pady=5)

        ai_semantic_label = ttk.Label(dedup_frame, text="0.85")
        ai_semantic_label.grid(row=4, column=2, padx=5, pady=5)

        def update_ai_semantic_label(*args):
            ai_semantic_label.config(text=f"{self.config_vars['ai_semantic_threshold'].get():.2f}")
        self.config_vars['ai_semantic_threshold'].trace('w', update_ai_semantic_label)

        # AI语义时间窗口
        ttk.Label(dedup_frame, text="AI语义时间窗口 (小时):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        if 'ai_semantic_time_window' not in self.config_vars:
            self.config_vars['ai_semantic_time_window'] = tk.IntVar()
        ttk.Spinbox(dedup_frame, from_=12, to=72, textvariable=self.config_vars['ai_semantic_time_window'],
                   width=10).grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(dedup_frame, text="(12-72小时)").grid(row=5, column=2, sticky=tk.W, padx=5, pady=5)

        # 结果设置
        result_frame = ttk.LabelFrame(frame, text="结果设置")
        result_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 最终分数阈值
        ttk.Label(result_frame, text="最终分数阈值 (0.0-1.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        if 'final_score_threshold' not in self.config_vars:
            self.config_vars['final_score_threshold'] = tk.DoubleVar()
        final_scale = ttk.Scale(result_frame, from_=0.0, to=1.0,
                              variable=self.config_vars['final_score_threshold'],
                              orient=tk.HORIZONTAL, length=200)
        final_scale.grid(row=0, column=1, padx=5, pady=5)

        final_label = ttk.Label(result_frame, text="0.70")
        final_label.grid(row=0, column=2, padx=5, pady=5)

        def update_final_label(*args):
            final_label.config(text=f"{self.config_vars['final_score_threshold'].get():.2f}")
        self.config_vars['final_score_threshold'].trace('w', update_final_label)

        # 最大最终结果数
        ttk.Label(result_frame, text="最大最终结果数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        if 'max_final_results' not in self.config_vars:
            self.config_vars['max_final_results'] = tk.IntVar()
        ttk.Spinbox(result_frame, from_=1, to=100, textvariable=self.config_vars['max_final_results'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 排序方式
        ttk.Label(result_frame, text="排序方式:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        if 'sort_by' not in self.config_vars:
            self.config_vars['sort_by'] = tk.StringVar()
        sort_combo = ttk.Combobox(result_frame, textvariable=self.config_vars['sort_by'],
                                 values=["final_score", "relevance", "timestamp"], width=15)
        sort_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
    
    def load_current_config(self):
        """加载当前配置"""
        try:
            # 直接从配置文件加载
            self.load_config_from_file()

            # 加载Agent配置列表（但不覆盖API设置）
            self.load_agent_config_list_without_overriding()

            # 加载关键词信息
            self.update_keyword_info()

        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def load_config_from_file(self):
        """直接从配置文件加载配置"""
        import json
        from pathlib import Path

        config_file = Path("config/filter_config.json")

        # 默认配置
        default_config = {
            "keyword": {
                "threshold": 0.65,
                "max_results": 150,
                "min_matches": 2,
                "case_sensitive": False,
                "fuzzy_match": True,
                "word_boundary": True
            },
            "ai": {
                "model_name": "gpt-3.5-turbo",
                "api_key": "",
                "base_url": "",
                "max_requests": 50,
                "max_selected": 3,
                "enable_cache": True,
                "fallback_enabled": True
            },
            "chain": {
                "enable_keyword_filter": True,
                "enable_ai_filter": True,
                "enable_deduplication": True,
                "final_score_threshold": 0.7,
                "max_final_results": 30,
                "sort_by": "final_score"
            },
            "deduplication": {
                "threshold": 0.8,
                "time_window_hours": 72
            },
            "ai_semantic_deduplication": {
                "enabled": True,
                "threshold": 0.85,
                "time_window_hours": 48
            }
        }

        # 如果配置文件存在，加载配置
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)

                # 合并配置（保存的配置覆盖默认配置）
                for section in default_config:
                    if section in saved_config:
                        default_config[section].update(saved_config[section])

                print(f"✅ 已从配置文件加载设置: {config_file}")
            except Exception as e:
                print(f"⚠️  读取配置文件失败，使用默认配置: {e}")
        else:
            print("📝 配置文件不存在，使用默认配置")

        # 加载关键词配置
        keyword_config = default_config["keyword"]
        self.config_vars['keyword_threshold'].set(keyword_config.get('threshold', 0.65))
        self.config_vars['max_results'].set(keyword_config.get('max_results', 150))
        self.config_vars['min_matches'].set(keyword_config.get('min_matches', 2))
        self.config_vars['case_sensitive'].set(keyword_config.get('case_sensitive', False))
        self.config_vars['fuzzy_match'].set(keyword_config.get('fuzzy_match', True))
        self.config_vars['word_boundary'].set(keyword_config.get('word_boundary', True))

        # 加载AI配置
        ai_config = default_config["ai"]
        self.config_vars['max_requests'].set(ai_config.get('max_requests', 50))
        self.config_vars['min_score_threshold'].set(ai_config.get('min_score_threshold', 20))
        self.config_vars['batch_max_articles'].set(ai_config.get('batch_max_articles', 30))
        self.config_vars['enable_cache'].set(ai_config.get('enable_cache', True))
        self.config_vars['fallback_enabled'].set(ai_config.get('fallback_enabled', True))
        self.config_vars['test_mode'].set(ai_config.get('test_mode', False))
        self.config_vars['test_mode_delay'].set(ai_config.get('test_mode_delay', 0.5))
        self.config_vars['api_key'].set(ai_config.get('api_key', ''))
        self.config_vars['model_name'].set(ai_config.get('model_name', 'gpt-3.5-turbo'))
        self.config_vars['base_url'].set(ai_config.get('base_url', ''))

        # 加载筛选链配置
        chain_config = default_config["chain"]
        self.config_vars['enable_keyword_filter'].set(chain_config.get('enable_keyword_filter', True))
        self.config_vars['enable_ai_filter'].set(chain_config.get('enable_ai_filter', True))
        self.config_vars['enable_deduplication'].set(chain_config.get('enable_deduplication', True))
        self.config_vars['final_score_threshold'].set(chain_config.get('final_score_threshold', 0.7))
        self.config_vars['max_final_results'].set(chain_config.get('max_final_results', 30))
        self.config_vars['sort_by'].set(chain_config.get('sort_by', 'final_score'))

        # 加载去重配置
        dedup_config = default_config["deduplication"]
        self.config_vars['dedup_threshold'].set(dedup_config.get('threshold', 0.8))
        self.config_vars['dedup_time_window'].set(dedup_config.get('time_window_hours', 72))

        # 加载AI语义去重配置
        ai_dedup_config = default_config["ai_semantic_deduplication"]
        self.config_vars['enable_ai_semantic_dedup'].set(ai_dedup_config.get('enabled', True))
        self.config_vars['ai_semantic_threshold'].set(ai_dedup_config.get('threshold', 0.85))
        self.config_vars['ai_semantic_time_window'].set(ai_dedup_config.get('time_window_hours', 48))

    def sync_agent_config_to_filter_service(self):
        """同步Agent配置到FilterService"""
        if not self.current_agent_config:
            return

        try:
            # 同步API配置到FilterService
            get_filter_service().update_config("ai",
                api_key=self.current_agent_config.api_config.api_key,
                model_name=self.current_agent_config.api_config.model_name,
                base_url=self.current_agent_config.api_config.base_url
            )
            print(f"✅ 已同步Agent配置 '{self.current_agent_config.config_name}' 到FilterService")
        except Exception as e:
            print(f"❌ 同步Agent配置失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            # 直接保存到配置文件
            self.save_config_to_file()

            # 保存AI Agent配置（如果有的话）
            if self.current_agent_config:
                self.save_current_agent_config()

            # 通知FilterService重新加载配置（保持兼容性）
            try:
                get_filter_service().reload_config()
            except:
                pass  # 如果reload_config方法不存在，忽略错误

            self.result = True
            messagebox.showinfo("成功", "配置已保存")
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def save_config_to_file(self):
        """直接保存配置到文件"""
        import json
        from pathlib import Path

        config_file = Path("config/filter_config.json")
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # 构建配置数据
        config_data = {
            "keyword": {
                "keywords": {},
                "weights": {},
                "threshold": self.config_vars['keyword_threshold'].get(),
                "max_results": self.config_vars['max_results'].get(),
                "case_sensitive": self.config_vars['case_sensitive'].get(),
                "fuzzy_match": self.config_vars['fuzzy_match'].get(),
                "word_boundary": self.config_vars['word_boundary'].get(),
                "phrase_matching": True,
                "min_keyword_length": 2,
                "min_matches": self.config_vars['min_matches'].get()
            },
            "ai": {
                "model_name": self.config_vars['model_name'].get(),
                "api_key": self.config_vars['api_key'].get(),
                "base_url": self.config_vars['base_url'].get(),
                "temperature": 0.3,
                "max_tokens": 1000,
                "max_requests": self.config_vars['max_requests'].get(),
                "min_score_threshold": self.config_vars['min_score_threshold'].get(),
                "batch_max_articles": self.config_vars['batch_max_articles'].get(),
                "batch_size": 5,
                "timeout": 30,
                "retry_times": 3,
                "retry_delay": 1,
                "enable_cache": self.config_vars['enable_cache'].get(),
                "cache_ttl": 3600,
                "cache_size": 1000,
                "fallback_enabled": self.config_vars['fallback_enabled'].get(),
                "fallback_threshold": 0.7,
                "min_confidence": 0.5,
                "test_mode": self.config_vars['test_mode'].get(),
                "test_mode_delay": self.config_vars['test_mode_delay'].get()
            },
            "chain": {
                "enable_keyword_filter": self.config_vars['enable_keyword_filter'].get(),
                "enable_ai_filter": self.config_vars['enable_ai_filter'].get(),
                "enable_deduplication": self.config_vars['enable_deduplication'].get(),
                "keyword_threshold": self.config_vars['keyword_threshold'].get(),
                "final_score_threshold": self.config_vars['final_score_threshold'].get(),
                "max_keyword_results": self.config_vars['max_results'].get(),
                "max_ai_requests": self.config_vars['max_requests'].get(),
                "max_final_results": self.config_vars['max_final_results'].get(),
                "fail_fast": False,
                "enable_parallel": True,
                "batch_size": 10,
                "sort_by": self.config_vars['sort_by'].get(),
                "include_rejected": False,
                "include_metrics": True
            },
            "deduplication": {
                "threshold": self.config_vars['dedup_threshold'].get(),
                "time_window_hours": self.config_vars['dedup_time_window'].get()
            },
            "ai_semantic_deduplication": {
                "enabled": self.config_vars['enable_ai_semantic_dedup'].get(),
                "threshold": self.config_vars['ai_semantic_threshold'].get(),
                "time_window_hours": self.config_vars['ai_semantic_time_window'].get()
            }
        }

        # 保存到文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 配置已保存到: {config_file}")
    
    def reset_config(self):
        """重置配置"""
        if messagebox.askyesno("确认", "确定要重置所有配置到默认值吗？"):
            self.load_current_config()
    
    def cancel(self):
        """取消"""
        self.dialog.destroy()

    def open_keyword_editor(self):
        """打开关键词编辑器"""
        from .keyword_editor_dialog import KeywordEditorDialog
        from ..config.keyword_config import keyword_config_manager

        # 获取当前关键词数据
        self.keywords_data = keyword_config_manager.get_keywords()

        # 打开编辑器
        editor = KeywordEditorDialog(self.dialog, self.keywords_data)

        # 如果用户保存了更改，更新配置管理器
        if editor.result:
            keyword_config_manager.update_keywords(self.keywords_data)

        self.update_keyword_info()

    def import_keywords(self):
        """导入关键词"""
        from tkinter import filedialog, messagebox
        from ..config.keyword_config import keyword_config_manager

        file_path = filedialog.askopenfilename(
            title="导入关键词文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if file_path:
            if keyword_config_manager.import_keywords(file_path, merge=True):
                self.update_keyword_info()
                messagebox.showinfo("成功", "关键词导入成功")
            else:
                messagebox.showerror("错误", "关键词导入失败")

    def export_keywords(self):
        """导出关键词"""
        from tkinter import filedialog, messagebox
        from ..config.keyword_config import keyword_config_manager

        file_path = filedialog.asksaveasfilename(
            title="导出关键词文件",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if file_path:
            if keyword_config_manager.export_keywords(file_path):
                messagebox.showinfo("成功", "关键词导出成功")
            else:
                messagebox.showerror("错误", "关键词导出失败")

    def reset_keywords(self):
        """重置为默认关键词"""
        from tkinter import messagebox
        from ..config.keyword_config import keyword_config_manager

        if messagebox.askyesno("确认", "确定要重置为默认关键词吗？这将覆盖当前的自定义关键词。"):
            keyword_config_manager.reset_to_default()
            self.update_keyword_info()
            messagebox.showinfo("成功", "已重置为默认关键词")

    def update_keyword_info(self):
        """更新关键词统计信息"""
        from ..config.keyword_config import keyword_config_manager

        stats = keyword_config_manager.get_statistics()
        total_keywords = stats['total_keywords']
        categories = stats['total_categories']

        info_text = f"共 {categories} 个分类，{total_keywords} 个关键词"
        self.keyword_info_label.config(text=info_text)

    # AI配置管理相关方法
    def load_agent_config_list(self):
        """加载AI Agent配置列表"""
        try:
            # 确保agent_config_combo存在
            if not hasattr(self, 'agent_config_combo'):
                print("agent_config_combo 不存在，跳过AI配置加载")
                return

            # 确保current_agent_config变量存在
            if 'current_agent_config' not in self.config_vars:
                self.config_vars['current_agent_config'] = tk.StringVar()

            config_list = agent_config_manager.get_config_list()
            self.agent_config_combo['values'] = config_list

            # 设置当前配置
            current_config = agent_config_manager.get_current_config()
            if current_config:
                self.config_vars['current_agent_config'].set(current_config.config_name)
                self.current_agent_config = current_config
                self.load_agent_config_to_ui(current_config)
            elif config_list:
                # 如果没有当前配置，选择第一个
                first_config = agent_config_manager.load_config(config_list[0])
                if first_config:
                    self.config_vars['current_agent_config'].set(config_list[0])
                    self.current_agent_config = first_config
                    self.load_agent_config_to_ui(first_config)
        except Exception as e:
            print(f"加载AI配置列表失败: {e}")
            import traceback
            traceback.print_exc()

    def load_agent_config_list_without_overriding(self):
        """加载AI Agent配置列表但不覆盖API设置"""
        try:
            # 确保agent_config_combo存在
            if not hasattr(self, 'agent_config_combo'):
                print("agent_config_combo 不存在，跳过AI配置加载")
                return

            # 确保current_agent_config变量存在
            if 'current_agent_config' not in self.config_vars:
                self.config_vars['current_agent_config'] = tk.StringVar()

            config_list = agent_config_manager.get_config_list()
            self.agent_config_combo['values'] = config_list

            # 设置当前配置但不加载到UI（避免覆盖API设置）
            current_config = agent_config_manager.get_current_config()
            if current_config:
                self.config_vars['current_agent_config'].set(current_config.config_name)
                self.current_agent_config = current_config
                # 不调用 load_agent_config_to_ui，避免覆盖API设置
            elif config_list:
                # 如果没有当前配置，选择第一个但不加载到UI
                first_config = agent_config_manager.load_config(config_list[0])
                if first_config:
                    self.config_vars['current_agent_config'].set(config_list[0])
                    self.current_agent_config = first_config
                    # 不调用 load_agent_config_to_ui，避免覆盖API设置
        except Exception as e:
            print(f"加载AI配置列表失败: {e}")
            import traceback
            traceback.print_exc()

    def on_agent_config_change(self, event=None):
        """AI配置选择变化事件"""
        config_name = self.config_vars['current_agent_config'].get()
        if config_name:
            try:
                config = agent_config_manager.load_config(config_name)
                if config:
                    self.current_agent_config = config
                    self.load_agent_config_to_ui(config)
                    # 设置为当前配置（这会自动保存到文件）
                    agent_config_manager.set_current_config(config_name)
                    # 同步配置到FilterService
                    self.sync_agent_config_to_filter_service()
            except Exception as e:
                messagebox.showerror("错误", f"加载配置失败: {e}")

    def load_agent_config_to_ui(self, config: AgentConfig):
        """将AI配置加载到界面"""
        try:
            # 确保所有变量都已初始化
            required_vars = {
                'provider': tk.StringVar,
                'api_key': tk.StringVar,
                'base_url': tk.StringVar,
                'model_name': tk.StringVar,
                'temperature': tk.DoubleVar,
                'max_tokens': tk.IntVar,
                'timeout': tk.IntVar,
                'retry_times': tk.IntVar,
                'proxy': tk.StringVar,
                'verify_ssl': tk.BooleanVar
            }

            for var_name, var_type in required_vars.items():
                if var_name not in self.config_vars:
                    self.config_vars[var_name] = var_type()

            # API配置
            self.config_vars['provider'].set(config.api_config.provider)
            self.config_vars['api_key'].set(config.api_config.api_key)
            self.config_vars['base_url'].set(config.api_config.base_url)
            self.config_vars['model_name'].set(config.api_config.model_name)

            # 高级设置
            self.config_vars['temperature'].set(config.api_config.temperature)
            self.config_vars['max_tokens'].set(config.api_config.max_tokens)
            self.config_vars['timeout'].set(config.api_config.timeout)
            self.config_vars['retry_times'].set(config.api_config.retry_times)
            self.config_vars['proxy'].set(config.api_config.proxy)
            self.config_vars['verify_ssl'].set(config.api_config.verify_ssl)

            # 更新模型列表
            self.update_model_list()

            # 更新提示词配置
            if hasattr(self, 'config_vars') and 'prompt_config_name' in self.config_vars:
                if config.prompt_config and config.prompt_config.name:
                    self.config_vars['prompt_config_name'].set(config.prompt_config.name)
                    self.update_prompt_preview()
                else:
                    # 如果没有提示词配置，清空选择
                    self.config_vars['prompt_config_name'].set("")
                    if hasattr(self, 'system_prompt_preview'):
                        self.system_prompt_preview.config(state="normal")
                        self.system_prompt_preview.delete("1.0", tk.END)
                        self.system_prompt_preview.config(state="disabled")
                    if hasattr(self, 'eval_prompt_preview'):
                        self.eval_prompt_preview.config(state="normal")
                        self.eval_prompt_preview.delete("1.0", tk.END)
                        self.eval_prompt_preview.config(state="disabled")

        except Exception as e:
            print(f"加载AI配置到界面失败: {e}")
            import traceback
            traceback.print_exc()

    def on_provider_change(self, event=None):
        """服务提供商变化事件"""
        self.update_model_list()

    def update_model_list(self):
        """根据服务提供商更新模型列表"""
        try:
            # 确保必要的变量和组件存在
            if 'provider' not in self.config_vars:
                return
            if not hasattr(self, 'model_combo'):
                return

            provider = self.config_vars['provider'].get()

            model_lists = {
                "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"],
                "siliconflow": ["Qwen/Qwen2.5-72B-Instruct", "Qwen/Qwen2.5-32B-Instruct",
                               "meta-llama/Meta-Llama-3.1-70B-Instruct", "deepseek-ai/DeepSeek-V2.5"],
                "volcengine": ["ep-20241219105006-xxxxx", "自定义Endpoint"],
                "moonshot": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
                "custom": ["自定义模型"]
            }

            models = model_lists.get(provider, ["gpt-3.5-turbo"])
            self.model_combo['values'] = models

            # 如果当前模型不在列表中，设置为第一个
            if 'model_name' in self.config_vars:
                current_model = self.config_vars['model_name'].get()
                if current_model not in models and models:
                    self.config_vars['model_name'].set(models[0])
        except Exception as e:
            print(f"更新模型列表失败: {e}")

    def new_agent_config(self):
        """新建AI配置"""
        try:
            # 创建新的配置对象
            new_api_config = AgentAPIConfig(
                name="新配置",
                description="",
                api_key="",
                base_url="",
                model_name="gpt-3.5-turbo",
                provider="openai"
            )

            new_prompt_config = AgentPromptConfig(
                name="新提示词",
                description="",
                system_prompt="",
                evaluation_prompt="",
                batch_evaluation_prompt=""
            )

            new_config = AgentConfig(
                config_name="新配置",
                api_config=new_api_config,
                prompt_config=new_prompt_config,
                is_default=False
            )

            # 创建配置
            config_name = agent_config_manager.create_config(new_config)

            # 更新界面
            self.load_agent_config_list()
            self.config_vars['current_agent_config'].set(config_name)
            self.current_agent_config = new_config

            messagebox.showinfo("成功", f"已创建新配置: {config_name}")

        except Exception as e:
            messagebox.showerror("错误", f"创建配置失败: {e}")

    def edit_agent_config(self):
        """编辑AI配置"""
        if not self.current_agent_config:
            messagebox.showwarning("提示", "请先选择要编辑的配置")
            return

        # 这里可以打开一个简化的编辑对话框，或者直接在当前界面编辑
        messagebox.showinfo("提示", "请在当前界面直接修改配置参数，保存时会自动更新")

    def delete_agent_config(self):
        """删除AI配置"""
        if not self.current_agent_config:
            messagebox.showwarning("提示", "请先选择要删除的配置")
            return

        if self.current_agent_config.is_default:
            messagebox.showwarning("提示", "不能删除默认配置")
            return

        if messagebox.askyesno("确认删除", f"确定要删除配置 '{self.current_agent_config.config_name}' 吗？"):
            try:
                agent_config_manager.delete_config(self.current_agent_config.config_name)
                self.load_agent_config_list()
                messagebox.showinfo("成功", "配置已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除配置失败: {e}")

    def load_prompt_config_list(self):
        """加载提示词配置列表"""
        try:
            # 获取所有提示词配置
            prompt_configs = agent_config_manager.get_all_prompt_configs()
            config_names = list(prompt_configs.keys())

            # 更新下拉框
            self.prompt_config_combo['values'] = config_names

            # 设置当前选中的配置
            if self.current_agent_config and self.current_agent_config.prompt_config:
                current_name = self.current_agent_config.prompt_config.name
                if current_name in config_names:
                    self.config_vars['prompt_config_name'].set(current_name)
                    self.update_prompt_preview()
            elif config_names:
                # 默认选择第一个
                self.config_vars['prompt_config_name'].set(config_names[0])
                self.update_prompt_preview()

        except Exception as e:
            print(f"加载提示词配置列表失败: {e}")

    def on_prompt_config_change(self, event=None):
        """提示词配置选择变化事件"""
        self.update_prompt_preview()

    def update_prompt_preview(self):
        """更新提示词预览"""
        try:
            prompt_name = self.config_vars['prompt_config_name'].get()
            if not prompt_name:
                return

            # 获取提示词配置
            prompt_configs = agent_config_manager.get_all_prompt_configs()
            prompt_config = prompt_configs.get(prompt_name)

            if prompt_config:
                # 更新系统提示词预览
                self.system_prompt_preview.config(state="normal")
                self.system_prompt_preview.delete("1.0", tk.END)
                self.system_prompt_preview.insert("1.0", prompt_config.system_prompt[:200] + "..." if len(prompt_config.system_prompt) > 200 else prompt_config.system_prompt)
                self.system_prompt_preview.config(state="disabled")

                # 更新评估提示词预览
                self.eval_prompt_preview.config(state="normal")
                self.eval_prompt_preview.delete("1.0", tk.END)
                self.eval_prompt_preview.insert("1.0", prompt_config.evaluation_prompt[:300] + "..." if len(prompt_config.evaluation_prompt) > 300 else prompt_config.evaluation_prompt)
                self.eval_prompt_preview.config(state="disabled")

        except Exception as e:
            print(f"更新提示词预览失败: {e}")

    def edit_prompt_config(self):
        """编辑提示词配置"""
        prompt_name = self.config_vars['prompt_config_name'].get()
        if not prompt_name:
            messagebox.showwarning("提示", "请先选择要编辑的提示词配置")
            return

        try:
            # 获取提示词配置
            prompt_configs = agent_config_manager.get_all_prompt_configs()
            prompt_config = prompt_configs.get(prompt_name)

            if prompt_config:
                # 打开提示词编辑对话框
                dialog = PromptConfigDialog(self.dialog, prompt_config)
                if dialog.result:
                    # 更新配置
                    agent_config_manager.update_prompt_config(prompt_name, dialog.result)
                    self.update_prompt_preview()
                    messagebox.showinfo("成功", "提示词配置已更新")

        except Exception as e:
            messagebox.showerror("错误", f"编辑提示词配置失败: {e}")

    def new_prompt_config(self):
        """新建提示词配置"""
        try:
            # 创建新的提示词配置
            new_prompt_config = AgentPromptConfig(
                name="新提示词配置",
                description="",
                system_prompt="",
                evaluation_prompt="",
                batch_evaluation_prompt=""
            )

            # 打开编辑对话框
            dialog = PromptConfigDialog(self.dialog, new_prompt_config, is_new=True)
            if dialog.result:
                # 保存新配置
                config_name = agent_config_manager.create_prompt_config(dialog.result)
                self.load_prompt_config_list()
                self.config_vars['prompt_config_name'].set(config_name)
                self.update_prompt_preview()
                messagebox.showinfo("成功", f"已创建新提示词配置: {config_name}")

        except Exception as e:
            messagebox.showerror("错误", f"创建提示词配置失败: {e}")

    def delete_prompt_config(self):
        """删除提示词配置"""
        prompt_name = self.config_vars['prompt_config_name'].get()
        if not prompt_name:
            messagebox.showwarning("提示", "请先选择要删除的提示词配置")
            return

        if messagebox.askyesno("确认删除", f"确定要删除提示词配置 '{prompt_name}' 吗？"):
            try:
                agent_config_manager.delete_prompt_config(prompt_name)
                self.load_prompt_config_list()
                messagebox.showinfo("成功", "提示词配置已删除")
            except Exception as e:
                messagebox.showerror("错误", f"删除提示词配置失败: {e}")

    def save_current_agent_config(self):
        """保存当前AI Agent配置"""
        if not self.current_agent_config:
            return

        try:
            # 更新API配置
            self.current_agent_config.api_config.provider = self.config_vars['provider'].get()
            self.current_agent_config.api_config.api_key = self.config_vars['api_key'].get()
            self.current_agent_config.api_config.base_url = self.config_vars['base_url'].get()
            self.current_agent_config.api_config.model_name = self.config_vars['model_name'].get()
            self.current_agent_config.api_config.temperature = self.config_vars['temperature'].get()
            self.current_agent_config.api_config.max_tokens = self.config_vars['max_tokens'].get()
            self.current_agent_config.api_config.timeout = self.config_vars['timeout'].get()
            self.current_agent_config.api_config.retry_times = self.config_vars['retry_times'].get()
            self.current_agent_config.api_config.proxy = self.config_vars['proxy'].get()
            self.current_agent_config.api_config.verify_ssl = self.config_vars['verify_ssl'].get()

            # 更新提示词配置
            if 'prompt_config_name' in self.config_vars:
                prompt_name = self.config_vars['prompt_config_name'].get()
                if prompt_name:
                    # 获取选中的提示词配置
                    prompt_configs = agent_config_manager.get_all_prompt_configs()
                    if prompt_name in prompt_configs:
                        self.current_agent_config.prompt_config = prompt_configs[prompt_name]

            # 保存配置
            agent_config_manager.update_config(
                self.current_agent_config.config_name,
                self.current_agent_config
            )

            # 设置为当前配置
            agent_config_manager.set_current_config(self.current_agent_config.config_name)

        except Exception as e:
            print(f"保存AI Agent配置失败: {e}")


class PromptConfigDialog:
    """提示词配置编辑对话框"""

    def __init__(self, parent, prompt_config, is_new=False):
        self.result = None
        self.prompt_config = prompt_config
        self.is_new = is_new

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("编辑提示词配置" if not is_new else "新建提示词配置")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
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

        # 基本信息
        info_frame = ttk.LabelFrame(main_frame, text="基本信息")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 名称
        ttk.Label(info_frame, text="名称:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.name_var = tk.StringVar(value=self.prompt_config.name)
        ttk.Entry(info_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # 描述
        ttk.Label(info_frame, text="描述:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.desc_var = tk.StringVar(value=self.prompt_config.description)
        ttk.Entry(info_frame, textvariable=self.desc_var, width=40).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)

        # 配置网格权重
        info_frame.grid_columnconfigure(1, weight=1)

        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # 系统提示词标签页
        self.create_system_prompt_tab(notebook)

        # 评估提示词标签页
        self.create_evaluation_prompt_tab(notebook)

        # 批量评估提示词标签页
        self.create_batch_prompt_tab(notebook)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="保存", command=self.save).pack(side=tk.RIGHT)

    def create_system_prompt_tab(self, notebook):
        """创建系统提示词标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="系统提示词")

        # 说明
        ttk.Label(frame, text="系统提示词定义AI的角色和基本行为规范:",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)

        # 文本编辑区域
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.system_prompt_text = tk.Text(text_frame, wrap=tk.WORD, height=15, width=60)
        system_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.system_prompt_text.yview)
        self.system_prompt_text.configure(yscrollcommand=system_scrollbar.set)

        self.system_prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        system_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入现有内容
        self.system_prompt_text.insert("1.0", self.prompt_config.system_prompt)

    def create_evaluation_prompt_tab(self, notebook):
        """创建评估提示词标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="评估提示词")

        # 说明
        ttk.Label(frame, text="评估提示词用于单篇文章的评估，支持变量: {title}, {summary}, {content_preview}",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)

        # 文本编辑区域
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.eval_prompt_text = tk.Text(text_frame, wrap=tk.WORD, height=15, width=60)
        eval_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.eval_prompt_text.yview)
        self.eval_prompt_text.configure(yscrollcommand=eval_scrollbar.set)

        self.eval_prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        eval_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入现有内容
        self.eval_prompt_text.insert("1.0", self.prompt_config.evaluation_prompt)

    def create_batch_prompt_tab(self, notebook):
        """创建批量评估提示词标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="批量评估提示词")

        # 说明
        ttk.Label(frame, text="批量评估提示词用于多篇文章的批量评估，支持变量: {articles_json}",
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=5, pady=5)

        # 文本编辑区域
        text_frame = ttk.Frame(frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.batch_prompt_text = tk.Text(text_frame, wrap=tk.WORD, height=15, width=60)
        batch_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.batch_prompt_text.yview)
        self.batch_prompt_text.configure(yscrollcommand=batch_scrollbar.set)

        self.batch_prompt_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        batch_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 插入现有内容
        self.batch_prompt_text.insert("1.0", self.prompt_config.batch_evaluation_prompt)

    def save(self):
        """保存提示词配置"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("错误", "请输入配置名称", parent=self.dialog)
            return

        # 创建新的提示词配置对象
        new_config = AgentPromptConfig(
            name=name,
            description=self.desc_var.get().strip(),
            system_prompt=self.system_prompt_text.get("1.0", tk.END).strip(),
            evaluation_prompt=self.eval_prompt_text.get("1.0", tk.END).strip(),
            batch_evaluation_prompt=self.batch_prompt_text.get("1.0", tk.END).strip(),
            version="1.0"
        )

        self.result = new_config
        self.dialog.destroy()

    def cancel(self):
        """取消编辑"""
        self.dialog.destroy()
