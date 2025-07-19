"""
筛选配置对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from ..services.filter_service import filter_service


class FilterConfigDialog:
    """筛选配置对话框"""
    
    def __init__(self, parent):
        self.parent = parent
        self.result = False
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("筛选配置")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 配置变量
        self.config_vars = {}
        self.keywords_data = {}  # 存储关键词数据
        
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
        self.config_vars['max_results'] = tk.IntVar()
        ttk.Spinbox(basic_frame, from_=10, to=500, textvariable=self.config_vars['max_results'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 最少匹配关键词数
        ttk.Label(basic_frame, text="最少匹配关键词数:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['min_matches'] = tk.IntVar()
        ttk.Spinbox(basic_frame, from_=1, to=10, textvariable=self.config_vars['min_matches'],
                   width=10).grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 高级设置
        advanced_frame = ttk.LabelFrame(scrollable_frame, text="高级设置")
        advanced_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 大小写敏感
        self.config_vars['case_sensitive'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="大小写敏感", 
                       variable=self.config_vars['case_sensitive']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 模糊匹配
        self.config_vars['fuzzy_match'] = tk.BooleanVar()
        ttk.Checkbutton(advanced_frame, text="启用模糊匹配", 
                       variable=self.config_vars['fuzzy_match']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 单词边界检查
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
        
        # AI服务设置
        ai_frame = ttk.LabelFrame(frame, text="AI服务设置")
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        # API Key
        ttk.Label(ai_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['api_key'] = tk.StringVar()
        api_key_entry = ttk.Entry(ai_frame, textvariable=self.config_vars['api_key'], 
                                 width=40, show="*")
        api_key_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 模型名称
        ttk.Label(ai_frame, text="模型名称:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['model_name'] = tk.StringVar()
        model_combo = ttk.Combobox(ai_frame, textvariable=self.config_vars['model_name'],
                                  values=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], width=20)
        model_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Base URL
        ttk.Label(ai_frame, text="Base URL (可选):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['base_url'] = tk.StringVar()
        ttk.Entry(ai_frame, textvariable=self.config_vars['base_url'], width=40).grid(row=2, column=1, padx=5, pady=5)
        
        # 筛选设置
        filter_frame = ttk.LabelFrame(frame, text="筛选设置")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI阈值
        ttk.Label(filter_frame, text="AI评分阈值 (0-30):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['ai_threshold'] = tk.IntVar()
        ttk.Spinbox(filter_frame, from_=0, to=30, textvariable=self.config_vars['ai_threshold'],
                   width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 最大请求数
        ttk.Label(filter_frame, text="最大请求数:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['max_requests'] = tk.IntVar()
        ttk.Spinbox(filter_frame, from_=1, to=200, textvariable=self.config_vars['max_requests'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 性能设置
        perf_frame = ttk.LabelFrame(frame, text="性能设置")
        perf_frame.pack(fill=tk.X)
        
        # 启用缓存
        self.config_vars['enable_cache'] = tk.BooleanVar()
        ttk.Checkbutton(perf_frame, text="启用缓存", 
                       variable=self.config_vars['enable_cache']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 启用降级策略
        self.config_vars['fallback_enabled'] = tk.BooleanVar()
        ttk.Checkbutton(perf_frame, text="启用降级策略", 
                       variable=self.config_vars['fallback_enabled']).pack(anchor=tk.W, padx=5, pady=2)
    
    def create_chain_config_tab(self, notebook):
        """创建筛选链配置标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="筛选链")
        
        # 筛选流程设置
        flow_frame = ttk.LabelFrame(frame, text="筛选流程")
        flow_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 启用关键词筛选
        self.config_vars['enable_keyword_filter'] = tk.BooleanVar()
        ttk.Checkbutton(flow_frame, text="启用关键词筛选", 
                       variable=self.config_vars['enable_keyword_filter']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 启用AI筛选
        self.config_vars['enable_ai_filter'] = tk.BooleanVar()
        ttk.Checkbutton(flow_frame, text="启用AI筛选", 
                       variable=self.config_vars['enable_ai_filter']).pack(anchor=tk.W, padx=5, pady=2)
        
        # 结果设置
        result_frame = ttk.LabelFrame(frame, text="结果设置")
        result_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 最终分数阈值
        ttk.Label(result_frame, text="最终分数阈值 (0.0-1.0):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
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
        self.config_vars['max_final_results'] = tk.IntVar()
        ttk.Spinbox(result_frame, from_=1, to=100, textvariable=self.config_vars['max_final_results'],
                   width=10).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # 排序方式
        ttk.Label(result_frame, text="排序方式:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.config_vars['sort_by'] = tk.StringVar()
        sort_combo = ttk.Combobox(result_frame, textvariable=self.config_vars['sort_by'],
                                 values=["final_score", "relevance", "timestamp"], width=15)
        sort_combo.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
    
    def load_current_config(self):
        """加载当前配置"""
        try:
            # 加载关键词配置
            keyword_config = filter_service.get_config("keyword")
            self.config_vars['keyword_threshold'].set(keyword_config.get('threshold', 0.65))
            self.config_vars['max_results'].set(keyword_config.get('max_results', 150))
            self.config_vars['min_matches'].set(keyword_config.get('min_matches', 2))
            self.config_vars['case_sensitive'].set(keyword_config.get('case_sensitive', False))
            self.config_vars['fuzzy_match'].set(keyword_config.get('fuzzy_match', True))
            self.config_vars['word_boundary'].set(keyword_config.get('word_boundary', True))
            
            # 加载AI配置
            ai_config = filter_service.get_config("ai")
            self.config_vars['api_key'].set(ai_config.get('api_key', ''))
            self.config_vars['model_name'].set(ai_config.get('model_name', 'gpt-3.5-turbo'))
            self.config_vars['base_url'].set(ai_config.get('base_url', ''))
            self.config_vars['ai_threshold'].set(ai_config.get('threshold', 20))
            self.config_vars['max_requests'].set(ai_config.get('max_requests', 50))
            self.config_vars['enable_cache'].set(ai_config.get('enable_cache', True))
            self.config_vars['fallback_enabled'].set(ai_config.get('fallback_enabled', True))
            
            # 加载筛选链配置
            chain_config = filter_service.get_config("chain")
            self.config_vars['enable_keyword_filter'].set(chain_config.get('enable_keyword_filter', True))
            self.config_vars['enable_ai_filter'].set(chain_config.get('enable_ai_filter', True))
            self.config_vars['final_score_threshold'].set(chain_config.get('final_score_threshold', 0.7))
            self.config_vars['max_final_results'].set(chain_config.get('max_final_results', 30))
            self.config_vars['sort_by'].set(chain_config.get('sort_by', 'final_score'))

            # 加载关键词信息
            self.update_keyword_info()

        except Exception as e:
            messagebox.showerror("错误", f"加载配置失败: {e}")
    
    def save_config(self):
        """保存配置"""
        try:
            # 保存关键词配置
            filter_service.update_config("keyword",
                threshold=self.config_vars['keyword_threshold'].get(),
                max_results=self.config_vars['max_results'].get(),
                min_matches=self.config_vars['min_matches'].get(),
                case_sensitive=self.config_vars['case_sensitive'].get(),
                fuzzy_match=self.config_vars['fuzzy_match'].get(),
                word_boundary=self.config_vars['word_boundary'].get()
            )
            
            # 保存AI配置
            filter_service.update_config("ai",
                api_key=self.config_vars['api_key'].get(),
                model_name=self.config_vars['model_name'].get(),
                base_url=self.config_vars['base_url'].get(),
                threshold=self.config_vars['ai_threshold'].get(),
                max_requests=self.config_vars['max_requests'].get(),
                enable_cache=self.config_vars['enable_cache'].get(),
                fallback_enabled=self.config_vars['fallback_enabled'].get()
            )
            
            # 保存筛选链配置
            filter_service.update_config("chain",
                enable_keyword_filter=self.config_vars['enable_keyword_filter'].get(),
                enable_ai_filter=self.config_vars['enable_ai_filter'].get(),
                final_score_threshold=self.config_vars['final_score_threshold'].get(),
                max_final_results=self.config_vars['max_final_results'].get(),
                sort_by=self.config_vars['sort_by'].get()
            )
            
            self.result = True
            messagebox.showinfo("成功", "配置已保存")
            self.dialog.destroy()
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
    
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
