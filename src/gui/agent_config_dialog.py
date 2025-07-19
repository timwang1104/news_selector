"""
AI Agent配置对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import Dict, Any, Optional
from ..config.agent_config import agent_config_manager, AgentConfig, AgentAPIConfig, AgentPromptConfig


class AgentConfigDialog:
    """AI Agent配置对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        self.current_config: Optional[AgentConfig] = None
        self.config_vars = {}
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("AI Agent配置")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 初始化变量
        self.init_variables()

        # 创建界面
        self.create_widgets()
        self.load_current_config()
        self.center_window()
        
        # 等待对话框关闭
        self.dialog.wait_window()

    def init_variables(self):
        """初始化界面变量"""
        # 初始化所有配置变量
        self.config_vars = {
            'api_name': tk.StringVar(),
            'api_description': tk.StringVar(),
            'api_key': tk.StringVar(),
            'base_url': tk.StringVar(),
            'model_name': tk.StringVar(),
            'provider': tk.StringVar(value="openai"),
            'temperature': tk.DoubleVar(value=0.3),
            'max_tokens': tk.IntVar(value=1000),
            'timeout': tk.IntVar(value=30),
            'retry_times': tk.IntVar(value=3),
            'proxy': tk.StringVar(),
            'verify_ssl': tk.BooleanVar(value=True),
            'prompt_name': tk.StringVar(),
            'prompt_version': tk.StringVar(value="1.0"),
            'prompt_description': tk.StringVar()
        }

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
        
        # 配置选择区域
        self.create_config_selection(main_frame)
        
        # 创建笔记本控件（标签页）
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # API配置标签页
        self.create_api_config_tab()
        
        # 提示词配置标签页
        self.create_prompt_config_tab()
        
        # 高级设置标签页
        self.create_advanced_config_tab()
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 左侧按钮
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side=tk.LEFT)
        
        ttk.Button(left_buttons, text="新建配置", command=self.new_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_buttons, text="复制配置", command=self.copy_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(left_buttons, text="删除配置", command=self.delete_config).pack(side=tk.LEFT, padx=(0, 5))
        
        # 右侧按钮
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side=tk.RIGHT)
        
        ttk.Button(right_buttons, text="测试连接", command=self.test_connection).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_buttons, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_buttons, text="取消", command=self.cancel).pack(side=tk.LEFT)
    
    def create_config_selection(self, parent):
        """创建配置选择区域"""
        selection_frame = ttk.LabelFrame(parent, text="配置管理")
        selection_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 配置选择
        config_frame = ttk.Frame(selection_frame)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(config_frame, text="当前配置:").pack(side=tk.LEFT)
        
        self.config_var = tk.StringVar()
        self.config_combo = ttk.Combobox(config_frame, textvariable=self.config_var, 
                                        values=agent_config_manager.get_config_list(),
                                        state="readonly", width=30)
        self.config_combo.pack(side=tk.LEFT, padx=(5, 10))
        self.config_combo.bind("<<ComboboxSelected>>", self.on_config_changed)
        
        # 配置信息
        info_frame = ttk.Frame(selection_frame)
        info_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.config_info_label = ttk.Label(info_frame, text="", foreground="gray")
        self.config_info_label.pack(anchor=tk.W)
    
    def create_api_config_tab(self):
        """创建API配置标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="API配置")
        
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
        
        # 基础设置
        basic_frame = ttk.LabelFrame(scrollable_frame, text="基础设置")
        basic_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        # 配置名称
        ttk.Label(basic_frame, text="配置名称:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(basic_frame, textvariable=self.config_vars['api_name'], width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 描述
        ttk.Label(basic_frame, text="描述:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(basic_frame, textvariable=self.config_vars['api_description'], width=40).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # API设置
        api_frame = ttk.LabelFrame(scrollable_frame, text="API设置")
        api_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        # API Key
        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        api_key_entry = ttk.Entry(api_frame, textvariable=self.config_vars['api_key'],
                                 width=50, show="*")
        api_key_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 显示/隐藏API Key按钮
        self.show_api_key = tk.BooleanVar()
        show_button = ttk.Checkbutton(api_frame, text="显示", variable=self.show_api_key,
                                     command=lambda: api_key_entry.config(show="" if self.show_api_key.get() else "*"))
        show_button.grid(row=0, column=2, padx=5, pady=5)

        # Base URL
        ttk.Label(api_frame, text="Base URL:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(api_frame, textvariable=self.config_vars['base_url'], width=50).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 服务提供商
        ttk.Label(api_frame, text="服务提供商:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        provider_combo = ttk.Combobox(api_frame, textvariable=self.config_vars['provider'],
                                     values=["openai", "siliconflow", "anthropic", "custom"],
                                     width=20, state="readonly")
        provider_combo.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)
        provider_combo.bind("<<ComboboxSelected>>", self.on_provider_changed)

        # 模型名称
        ttk.Label(api_frame, text="模型名称:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.model_combo = ttk.Combobox(api_frame, textvariable=self.config_vars['model_name'],
                                       width=40)
        self.model_combo.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)

        # 快速模型选择（仅在硅基流动时显示）
        self.quick_model_frame = ttk.Frame(api_frame)
        self.quick_model_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        ttk.Label(self.quick_model_frame, text="快速选择:").pack(side=tk.LEFT)
        ttk.Button(self.quick_model_frame, text="Qwen2.5-72B",
                  command=lambda: self.set_quick_model("Qwen/Qwen2.5-72B-Instruct")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.quick_model_frame, text="Kimi",
                  command=lambda: self.set_quick_model("moonshotai/Kimi-K2-Instruct")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.quick_model_frame, text="DeepSeek",
                  command=lambda: self.set_quick_model("deepseek-ai/DeepSeek-V2.5")).pack(side=tk.LEFT, padx=2)
        ttk.Button(self.quick_model_frame, text="Llama3.1-70B",
                  command=lambda: self.set_quick_model("meta-llama/Meta-Llama-3.1-70B-Instruct")).pack(side=tk.LEFT, padx=2)

        # 初始隐藏快速选择
        self.quick_model_frame.grid_remove()
        
        # 请求参数
        params_frame = ttk.LabelFrame(scrollable_frame, text="请求参数")
        params_frame.pack(fill=tk.X, pady=(0, 10), padx=10)
        
        # Temperature
        ttk.Label(params_frame, text="Temperature (0.0-2.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        temp_scale = ttk.Scale(params_frame, from_=0.0, to=2.0,
                              variable=self.config_vars['temperature'],
                              orient=tk.HORIZONTAL, length=200)
        temp_scale.grid(row=0, column=1, padx=5, pady=5)

        self.temp_label = ttk.Label(params_frame, text="0.3")
        self.temp_label.grid(row=0, column=2, padx=5, pady=5)

        def update_temp_label(*args):
            self.temp_label.config(text=f"{self.config_vars['temperature'].get():.1f}")
        self.config_vars['temperature'].trace('w', update_temp_label)

        # Max Tokens
        ttk.Label(params_frame, text="Max Tokens:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(params_frame, from_=100, to=4000, textvariable=self.config_vars['max_tokens'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # Timeout
        ttk.Label(params_frame, text="超时时间(秒):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(params_frame, from_=5, to=300, textvariable=self.config_vars['timeout'],
                   width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # 重试设置
        ttk.Label(params_frame, text="重试次数:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Spinbox(params_frame, from_=0, to=10, textvariable=self.config_vars['retry_times'],
                   width=10).grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_prompt_config_tab(self):
        """创建提示词配置标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="提示词配置")
        
        # 提示词基础信息
        info_frame = ttk.LabelFrame(frame, text="基础信息")
        info_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # 提示词名称
        ttk.Label(info_frame, text="提示词名称:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(info_frame, textvariable=self.config_vars['prompt_name'], width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 版本
        ttk.Label(info_frame, text="版本:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        ttk.Entry(info_frame, textvariable=self.config_vars['prompt_version'], width=10).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

        # 描述
        ttk.Label(info_frame, text="描述:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(info_frame, textvariable=self.config_vars['prompt_description'], width=60).grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        # 提示词内容
        content_frame = ttk.LabelFrame(frame, text="提示词内容")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 创建标签页用于不同类型的提示词
        prompt_notebook = ttk.Notebook(content_frame)
        prompt_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 系统提示词
        system_frame = ttk.Frame(prompt_notebook)
        prompt_notebook.add(system_frame, text="系统提示词")
        
        self.system_prompt_text = scrolledtext.ScrolledText(system_frame, height=8, wrap=tk.WORD)
        self.system_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 评估提示词
        eval_frame = ttk.Frame(prompt_notebook)
        prompt_notebook.add(eval_frame, text="评估提示词")
        
        self.eval_prompt_text = scrolledtext.ScrolledText(eval_frame, height=8, wrap=tk.WORD)
        self.eval_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 批量评估提示词
        batch_frame = ttk.Frame(prompt_notebook)
        prompt_notebook.add(batch_frame, text="批量评估提示词")
        
        self.batch_prompt_text = scrolledtext.ScrolledText(batch_frame, height=8, wrap=tk.WORD)
        self.batch_prompt_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def create_advanced_config_tab(self):
        """创建高级设置标签页"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="高级设置")
        
        # 网络设置
        network_frame = ttk.LabelFrame(frame, text="网络设置")
        network_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        # 代理设置
        ttk.Label(network_frame, text="代理地址:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(network_frame, textvariable=self.config_vars['proxy'], width=40).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # SSL验证
        ttk.Checkbutton(network_frame, text="启用SSL验证",
                       variable=self.config_vars['verify_ssl']).grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 自定义请求头
        headers_frame = ttk.LabelFrame(frame, text="自定义请求头")
        headers_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 请求头编辑器
        headers_edit_frame = ttk.Frame(headers_frame)
        headers_edit_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(headers_edit_frame, text="键:").pack(side=tk.LEFT)
        self.header_key_var = tk.StringVar()
        ttk.Entry(headers_edit_frame, textvariable=self.header_key_var, width=20).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(headers_edit_frame, text="值:").pack(side=tk.LEFT)
        self.header_value_var = tk.StringVar()
        ttk.Entry(headers_edit_frame, textvariable=self.header_value_var, width=30).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Button(headers_edit_frame, text="添加", command=self.add_header).pack(side=tk.LEFT, padx=5)
        
        # 请求头列表
        self.headers_tree = ttk.Treeview(headers_frame, columns=("key", "value"), show="headings", height=6)
        self.headers_tree.heading("key", text="键")
        self.headers_tree.heading("value", text="值")
        self.headers_tree.column("key", width=150)
        self.headers_tree.column("value", width=300)
        self.headers_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        # 删除按钮
        ttk.Button(headers_frame, text="删除选中", command=self.remove_header).pack(pady=5)

        # 添加预设配置按钮
        preset_frame = ttk.Frame(headers_frame)
        preset_frame.pack(fill=tk.X, pady=5)

        ttk.Button(preset_frame, text="加载OpenAI预设", command=self.load_openai_preset).pack(side=tk.LEFT, padx=5)
        ttk.Button(preset_frame, text="加载硅基流动预设", command=self.load_siliconflow_preset).pack(side=tk.LEFT, padx=5)

    def on_provider_changed(self, event=None):
        """服务提供商变更事件"""
        provider = self.config_vars['provider'].get()

        # 根据提供商更新模型列表
        if provider == "openai":
            models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]
            base_url = "https://api.openai.com/v1"
        elif provider == "siliconflow":
            models = [
                "Qwen/Qwen2.5-72B-Instruct",
                "Qwen/Qwen2.5-32B-Instruct",
                "Qwen/Qwen2.5-14B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "deepseek-ai/DeepSeek-V2.5",
                "meta-llama/Meta-Llama-3.1-70B-Instruct",
                "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "THUDM/glm-4-9b-chat",
                "01-ai/Yi-1.5-34B-Chat-16K",
                "moonshotai/Kimi-K2-Instruct"
            ]
            base_url = "https://api.siliconflow.cn/v1"
        elif provider == "anthropic":
            models = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-sonnet-20240229"]
            base_url = "https://api.anthropic.com"
        else:  # custom
            models = ["custom-model"]
            base_url = ""

        # 更新模型下拉列表
        self.model_combo['values'] = models
        if models:
            self.config_vars['model_name'].set(models[0])

        # 更新Base URL
        if base_url:
            self.config_vars['base_url'].set(base_url)

        # 显示/隐藏快速模型选择
        if provider == "siliconflow":
            self.quick_model_frame.grid()
        else:
            self.quick_model_frame.grid_remove()

    def set_quick_model(self, model_name: str):
        """快速设置模型"""
        self.config_vars['model_name'].set(model_name)

        # 根据模型调整参数
        if "Kimi" in model_name:
            # Kimi模型优化参数
            self.config_vars['max_tokens'].set(2000)
            self.config_vars['timeout'].set(90)
            # 更新系统提示词
            kimi_prompt = "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。你擅长分析科技新闻的政策价值和实用性。"
            self.system_prompt_text.delete(1.0, tk.END)
            self.system_prompt_text.insert(1.0, kimi_prompt)
        elif "DeepSeek" in model_name:
            # DeepSeek模型优化参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(60)
        elif "Llama" in model_name:
            # Llama模型优化参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(75)
        else:
            # Qwen等默认参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(60)
            # 恢复默认系统提示词
            default_prompt = "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。"
            self.system_prompt_text.delete(1.0, tk.END)
            self.system_prompt_text.insert(1.0, default_prompt)

    def set_quick_model(self, model_name: str):
        """快速设置模型"""
        self.config_vars['model_name'].set(model_name)

        # 根据模型调整参数
        if "Kimi" in model_name:
            # Kimi模型优化参数
            self.config_vars['max_tokens'].set(2000)
            self.config_vars['timeout'].set(90)
            # 更新系统提示词
            kimi_prompt = "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。你擅长分析科技新闻的政策价值和实用性。"
            self.system_prompt_text.delete(1.0, tk.END)
            self.system_prompt_text.insert(1.0, kimi_prompt)
        elif "DeepSeek" in model_name:
            # DeepSeek模型优化参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(60)
        elif "Llama" in model_name:
            # Llama模型优化参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(75)
        else:
            # Qwen等默认参数
            self.config_vars['max_tokens'].set(1500)
            self.config_vars['timeout'].set(60)
            # 恢复默认系统提示词
            default_prompt = "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。"
            self.system_prompt_text.delete(1.0, tk.END)
            self.system_prompt_text.insert(1.0, default_prompt)

    def load_openai_preset(self):
        """加载OpenAI预设配置"""
        self.config_vars['provider'].set("openai")
        self.config_vars['api_name'].set("OpenAI GPT")
        self.config_vars['api_description'].set("OpenAI官方API配置")
        self.config_vars['base_url'].set("https://api.openai.com/v1")
        self.config_vars['model_name'].set("gpt-3.5-turbo")
        self.config_vars['temperature'].set(0.3)
        self.config_vars['max_tokens'].set(1000)
        self.config_vars['timeout'].set(30)
        self.config_vars['retry_times'].set(3)
        self.on_provider_changed()

    def load_siliconflow_preset(self):
        """加载硅基流动预设配置"""
        self.config_vars['provider'].set("siliconflow")
        self.config_vars['api_name'].set("硅基流动平台")
        self.config_vars['api_description'].set("硅基流动平台多模型服务，支持Qwen、Kimi、DeepSeek等模型")
        self.config_vars['base_url'].set("https://api.siliconflow.cn/v1")
        self.config_vars['model_name'].set("Qwen/Qwen2.5-72B-Instruct")  # 默认模型
        self.config_vars['temperature'].set(0.3)
        self.config_vars['max_tokens'].set(2000)  # 增加以支持Kimi等长输出模型
        self.config_vars['timeout'].set(90)       # 增加以支持复杂模型
        self.config_vars['retry_times'].set(3)
        self.on_provider_changed()

        # 加载硅基流动优化的提示词
        siliconflow_system_prompt = "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。"
        self.system_prompt_text.delete(1.0, tk.END)
        self.system_prompt_text.insert(1.0, siliconflow_system_prompt)

        # 设置提示词配置信息
        self.config_vars['prompt_name'].set("硅基流动科技政策评估")
        self.config_vars['prompt_description'].set("适用于硅基流动平台多种模型的科技政策评估提示词")

    def load_current_config(self):
        """加载当前配置"""
        try:
            # 更新配置列表
            self.config_combo['values'] = agent_config_manager.get_config_list()

            # 设置当前配置
            current_config = agent_config_manager.get_current_config()
            if current_config:
                self.config_var.set(current_config.config_name)
                self.load_config_data(current_config)
            elif agent_config_manager.get_config_list():
                # 如果没有当前配置，选择第一个
                first_config_name = agent_config_manager.get_config_list()[0]
                self.config_var.set(first_config_name)
                config = agent_config_manager.load_config(first_config_name)
                if config:
                    self.load_config_data(config)
        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")

    def load_config_data(self, config: AgentConfig):
        """加载配置数据到界面"""
        self.current_config = config

        # 更新配置信息显示
        info_text = f"创建时间: {config.created_at[:19]} | 更新时间: {config.updated_at[:19]}"
        if config.is_default:
            info_text += " | 默认配置"
        self.config_info_label.config(text=info_text)

        # 加载API配置
        api_config = config.api_config
        self.config_vars['api_name'].set(api_config.name)
        self.config_vars['api_description'].set(api_config.description)
        self.config_vars['api_key'].set(api_config.api_key)
        self.config_vars['base_url'].set(api_config.base_url)
        self.config_vars['model_name'].set(api_config.model_name)
        self.config_vars['temperature'].set(api_config.temperature)
        self.config_vars['max_tokens'].set(api_config.max_tokens)
        self.config_vars['timeout'].set(api_config.timeout)
        self.config_vars['retry_times'].set(api_config.retry_times)
        self.config_vars['proxy'].set(api_config.proxy)
        self.config_vars['verify_ssl'].set(api_config.verify_ssl)

        # 加载服务提供商
        provider = getattr(api_config, 'provider', 'openai')
        self.config_vars['provider'].set(provider)
        self.on_provider_changed()  # 更新模型列表

        # 加载提示词配置
        prompt_config = config.prompt_config
        self.config_vars['prompt_name'].set(prompt_config.name)
        self.config_vars['prompt_version'].set(prompt_config.version)
        self.config_vars['prompt_description'].set(prompt_config.description)

        # 加载提示词内容
        self.system_prompt_text.delete(1.0, tk.END)
        self.system_prompt_text.insert(1.0, prompt_config.system_prompt)

        self.eval_prompt_text.delete(1.0, tk.END)
        self.eval_prompt_text.insert(1.0, prompt_config.evaluation_prompt)

        self.batch_prompt_text.delete(1.0, tk.END)
        self.batch_prompt_text.insert(1.0, prompt_config.batch_evaluation_prompt)

        # 加载自定义请求头
        self.load_headers(api_config.headers)

    def load_headers(self, headers: Dict[str, str]):
        """加载请求头到列表"""
        # 清空现有项目
        for item in self.headers_tree.get_children():
            self.headers_tree.delete(item)

        # 添加请求头
        for key, value in headers.items():
            self.headers_tree.insert("", tk.END, values=(key, value))

    def on_config_changed(self, event=None):
        """配置选择改变事件"""
        config_name = self.config_var.get()
        if config_name:
            config = agent_config_manager.load_config(config_name)
            if config:
                self.load_config_data(config)

    def add_header(self):
        """添加请求头"""
        key = self.header_key_var.get().strip()
        value = self.header_value_var.get().strip()

        if not key:
            messagebox.showwarning("警告", "请输入请求头键名")
            return

        # 检查是否已存在
        for item in self.headers_tree.get_children():
            if self.headers_tree.item(item)['values'][0] == key:
                messagebox.showwarning("警告", f"请求头 '{key}' 已存在")
                return

        # 添加到列表
        self.headers_tree.insert("", tk.END, values=(key, value))

        # 清空输入框
        self.header_key_var.set("")
        self.header_value_var.set("")

    def remove_header(self):
        """删除选中的请求头"""
        selected = self.headers_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请选择要删除的请求头")
            return

        for item in selected:
            self.headers_tree.delete(item)

    def get_headers_dict(self) -> Dict[str, str]:
        """获取请求头字典"""
        headers = {}
        for item in self.headers_tree.get_children():
            key, value = self.headers_tree.item(item)['values']
            headers[key] = value
        return headers

    def new_config(self):
        """新建配置"""
        try:
            # 创建新的配置对象
            new_api_config = AgentAPIConfig(
                name="新配置",
                description="",
                api_key="",
                base_url="",
                model_name="gpt-3.5-turbo"
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
            self.config_combo['values'] = agent_config_manager.get_config_list()
            self.config_var.set(config_name)
            self.load_config_data(new_config)

            messagebox.showinfo("成功", f"已创建新配置: {config_name}")

        except Exception as e:
            messagebox.showerror("错误", f"创建配置失败: {e}")

    def copy_config(self):
        """复制当前配置"""
        if not self.current_config:
            messagebox.showwarning("警告", "没有可复制的配置")
            return

        try:
            # 复制当前配置
            import copy
            new_config = copy.deepcopy(self.current_config)
            new_config.config_name = f"{self.current_config.config_name}_副本"
            new_config.is_default = False

            # 创建配置
            config_name = agent_config_manager.create_config(new_config)

            # 更新界面
            self.config_combo['values'] = agent_config_manager.get_config_list()
            self.config_var.set(config_name)
            self.load_config_data(new_config)

            messagebox.showinfo("成功", f"已复制配置: {config_name}")

        except Exception as e:
            messagebox.showerror("错误", f"复制配置失败: {e}")

    def delete_config(self):
        """删除当前配置"""
        config_name = self.config_var.get()
        if not config_name:
            messagebox.showwarning("警告", "请选择要删除的配置")
            return

        if len(agent_config_manager.get_config_list()) <= 1:
            messagebox.showwarning("警告", "至少需要保留一个配置")
            return

        if messagebox.askyesno("确认", f"确定要删除配置 '{config_name}' 吗？"):
            try:
                agent_config_manager.delete_config(config_name)

                # 更新界面
                self.config_combo['values'] = agent_config_manager.get_config_list()
                if agent_config_manager.get_config_list():
                    first_config = agent_config_manager.get_config_list()[0]
                    self.config_var.set(first_config)
                    config = agent_config_manager.load_config(first_config)
                    if config:
                        self.load_config_data(config)

                messagebox.showinfo("成功", f"已删除配置: {config_name}")

            except Exception as e:
                messagebox.showerror("错误", f"删除配置失败: {e}")

    def test_connection(self):
        """测试API连接"""
        try:
            # 获取当前配置
            api_key = self.config_vars['api_key'].get()
            base_url = self.config_vars['base_url'].get()
            model_name = self.config_vars['model_name'].get()

            if not api_key:
                messagebox.showwarning("警告", "请输入API Key")
                return

            # 创建测试客户端
            from ..ai.client import AIClient
            from ..config.filter_config import AIFilterConfig

            test_config = AIFilterConfig(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                timeout=10  # 测试时使用较短的超时时间
            )

            client = AIClient(test_config)

            # 创建测试文章
            from ..models.news import NewsArticle
            from datetime import datetime

            test_article = NewsArticle(
                id="test",
                title="Test Article for API Connection",
                summary="This is a test article to verify API connectivity",
                content="",
                url="http://example.com",
                published=datetime.now(),
                updated=datetime.now(),
                feed_title="Test Feed"
            )

            # 测试评估
            messagebox.showinfo("测试中", "正在测试API连接，请稍候...")
            evaluation = client.evaluate_article(test_article)

            if evaluation:
                messagebox.showinfo("成功", f"API连接测试成功！\n模型: {model_name}\n测试评分: {evaluation.total_score}")
            else:
                messagebox.showerror("失败", "API连接测试失败，请检查配置")

        except Exception as e:
            messagebox.showerror("错误", f"API连接测试失败: {e}")

    def save_config(self):
        """保存配置"""
        try:
            config_name = self.config_var.get()
            if not config_name:
                messagebox.showwarning("警告", "请选择或创建一个配置")
                return

            # 构建API配置
            api_config = AgentAPIConfig(
                name=self.config_vars['api_name'].get(),
                description=self.config_vars['api_description'].get(),
                api_key=self.config_vars['api_key'].get(),
                base_url=self.config_vars['base_url'].get(),
                model_name=self.config_vars['model_name'].get(),
                temperature=self.config_vars['temperature'].get(),
                max_tokens=self.config_vars['max_tokens'].get(),
                timeout=self.config_vars['timeout'].get(),
                retry_times=self.config_vars['retry_times'].get(),
                proxy=self.config_vars['proxy'].get(),
                verify_ssl=self.config_vars['verify_ssl'].get(),
                headers=self.get_headers_dict(),
                provider=self.config_vars['provider'].get()
            )

            # 构建提示词配置
            prompt_config = AgentPromptConfig(
                name=self.config_vars['prompt_name'].get(),
                version=self.config_vars['prompt_version'].get(),
                description=self.config_vars['prompt_description'].get(),
                system_prompt=self.system_prompt_text.get(1.0, tk.END).strip(),
                evaluation_prompt=self.eval_prompt_text.get(1.0, tk.END).strip(),
                batch_evaluation_prompt=self.batch_prompt_text.get(1.0, tk.END).strip()
            )

            # 构建完整配置
            config = AgentConfig(
                config_name=config_name,
                api_config=api_config,
                prompt_config=prompt_config,
                is_active=True,
                is_default=self.current_config.is_default if self.current_config else False
            )

            # 保存配置
            agent_config_manager.update_config(config_name, config)

            # 设置为当前配置
            agent_config_manager.set_current_config(config_name)

            self.result = True
            messagebox.showinfo("成功", "配置已保存")
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")

    def cancel(self):
        """取消"""
        self.dialog.destroy()
