"""
订阅源导出导入对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import threading
from typing import List, Dict, Any, Optional

from ..services.subscription_export_service import SubscriptionExportService
from .subscription_import_dialog import SubscriptionImportProgressDialog


class SubscriptionExportDialog:
    """订阅源导出导入对话框"""
    
    def __init__(self, parent, auth=None, import_callback=None):
        self.parent = parent
        self.auth = auth
        self.export_service = SubscriptionExportService(auth)
        self.export_data = []
        self.import_callback = import_callback  # 导入完成后的回调函数
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Inoreader订阅源导出导入")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self.create_widgets()
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
        
        # 标题
        title_label = ttk.Label(main_frame, text="📡 Inoreader订阅源导出导入", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 说明文字
        desc_label = ttk.Label(main_frame, 
                              text="将Inoreader中的订阅源导出并批量添加到自定义RSS中，避免API访问限制",
                              font=("Arial", 10), foreground="gray")
        desc_label.pack(pady=(0, 20))
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 导出标签页
        self.create_export_tab(notebook)
        
        # 导入标签页
        self.create_import_tab(notebook)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT)
    
    def create_export_tab(self, notebook):
        """创建导出标签页"""
        export_frame = ttk.Frame(notebook)
        notebook.add(export_frame, text="📤 导出订阅源")
        
        # 导出说明
        export_desc = ttk.Label(export_frame, 
                               text="从Inoreader导出所有订阅源，保存为JSON文件",
                               font=("Arial", 12, "bold"))
        export_desc.pack(pady=(20, 10))
        
        # 导出按钮框架
        export_button_frame = ttk.Frame(export_frame)
        export_button_frame.pack(pady=(10, 20))
        
        self.export_button = ttk.Button(export_button_frame, text="🔄 从Inoreader导出订阅源", 
                                       command=self.export_subscriptions)
        self.export_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.save_button = ttk.Button(export_button_frame, text="💾 保存到文件", 
                                     command=self.save_to_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT)
        
        # 导出结果显示
        result_frame = ttk.LabelFrame(export_frame, text="导出结果", padding="10")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 创建树形视图显示导出的订阅源
        columns = ("title", "category", "url")
        self.export_tree = ttk.Treeview(result_frame, columns=columns, show="tree headings")
        self.export_tree.heading("#0", text="")
        self.export_tree.heading("title", text="标题")
        self.export_tree.heading("category", text="分类")
        self.export_tree.heading("url", text="RSS URL")
        
        self.export_tree.column("#0", width=30)
        self.export_tree.column("title", width=250)
        self.export_tree.column("category", width=100)
        self.export_tree.column("url", width=300)
        
        # 滚动条
        export_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.export_tree.yview)
        self.export_tree.configure(yscrollcommand=export_scrollbar.set)
        
        self.export_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        export_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 状态标签
        self.export_status_label = ttk.Label(export_frame, text="点击上方按钮开始导出", 
                                           foreground="gray")
        self.export_status_label.pack(pady=(10, 0))
    
    def create_import_tab(self, notebook):
        """创建导入标签页"""
        import_frame = ttk.Frame(notebook)
        notebook.add(import_frame, text="📥 导入到自定义RSS")
        
        # 导入说明
        import_desc = ttk.Label(import_frame, 
                               text="将导出的订阅源批量添加到自定义RSS系统中",
                               font=("Arial", 12, "bold"))
        import_desc.pack(pady=(20, 10))
        
        # 导入选项框架
        import_option_frame = ttk.LabelFrame(import_frame, text="导入选项", padding="10")
        import_option_frame.pack(fill=tk.X, pady=(10, 0))
        
        # 数据源选择
        source_frame = ttk.Frame(import_option_frame)
        source_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(source_frame, text="数据源:").pack(side=tk.LEFT)
        
        self.import_source_var = tk.StringVar(value="current")
        ttk.Radiobutton(source_frame, text="使用当前导出的数据", 
                       variable=self.import_source_var, value="current").pack(side=tk.LEFT, padx=(10, 0))
        ttk.Radiobutton(source_frame, text="从文件加载", 
                       variable=self.import_source_var, value="file").pack(side=tk.LEFT, padx=(10, 0))
        
        # 文件选择框架
        file_frame = ttk.Frame(import_option_frame)
        file_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(file_frame, text="文件:").pack(side=tk.LEFT)
        self.file_path_var = tk.StringVar()
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, width=50)
        file_entry.pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)
        
        ttk.Button(file_frame, text="浏览", command=self.browse_file).pack(side=tk.LEFT, padx=(10, 0))
        
        # 导入按钮框架
        import_button_frame = ttk.Frame(import_frame)
        import_button_frame.pack(pady=(20, 10))
        
        self.preview_button = ttk.Button(import_button_frame, text="🔍 预览导入", 
                                        command=self.preview_import)
        self.preview_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.import_button = ttk.Button(import_button_frame, text="📥 开始导入", 
                                       command=self.start_import, state=tk.DISABLED)
        self.import_button.pack(side=tk.LEFT)
        
        # 预览结果显示
        preview_frame = ttk.LabelFrame(import_frame, text="导入预览", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.preview_text = tk.Text(preview_frame, height=10, wrap=tk.WORD, 
                                   font=("Consolas", 9), state=tk.DISABLED)
        
        preview_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scrollbar.set)
        
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        preview_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def export_subscriptions(self):
        """导出订阅源"""
        def export_task():
            try:
                # 更新UI状态
                self.dialog.after(0, lambda: self.export_button.config(state=tk.DISABLED))
                self.dialog.after(0, lambda: self.export_status_label.config(text="正在从Inoreader获取订阅源..."))
                
                # 执行导出
                success, message, export_data = self.export_service.export_inoreader_subscriptions()
                
                # 在主线程中更新UI
                self.dialog.after(0, lambda: self._handle_export_result(success, message, export_data))
                
            except Exception as e:
                self.dialog.after(0, lambda: self._handle_export_error(str(e)))
        
        # 启动导出线程
        threading.Thread(target=export_task, daemon=True).start()
    
    def _handle_export_result(self, success: bool, message: str, export_data: List[Dict[str, Any]]):
        """处理导出结果"""
        self.export_button.config(state=tk.NORMAL)
        
        if success:
            self.export_data = export_data
            self.export_status_label.config(text=message, foreground="green")
            self.save_button.config(state=tk.NORMAL)
            
            # 更新树形视图
            self.update_export_tree()
            
            messagebox.showinfo("导出成功", message)
        else:
            self.export_status_label.config(text=f"导出失败: {message}", foreground="red")
            messagebox.showerror("导出失败", message)
    
    def _handle_export_error(self, error: str):
        """处理导出错误"""
        self.export_button.config(state=tk.NORMAL)
        self.export_status_label.config(text=f"导出错误: {error}", foreground="red")
        messagebox.showerror("导出错误", f"导出过程中发生错误:\n{error}")
    
    def update_export_tree(self):
        """更新导出结果树形视图"""
        # 清空现有项目
        for item in self.export_tree.get_children():
            self.export_tree.delete(item)
        
        # 按分类分组
        categories = {}
        for item in self.export_data:
            category = item.get('category', '默认')
            if category not in categories:
                categories[category] = []
            categories[category].append(item)
        
        # 添加到树形视图
        for category, items in categories.items():
            # 添加分类节点
            category_node = self.export_tree.insert("", "end", text=f"📁 {category} ({len(items)})", 
                                                   values=("", "", ""))
            
            # 添加订阅源
            for item in items:
                self.export_tree.insert(category_node, "end", 
                                      values=(item.get('title', ''), 
                                             item.get('category', ''), 
                                             item.get('url', '')))
        
        # 展开所有节点
        for item in self.export_tree.get_children():
            self.export_tree.item(item, open=True)

    def save_to_file(self):
        """保存导出数据到文件"""
        if not self.export_data:
            messagebox.showwarning("警告", "没有可保存的数据")
            return

        # 选择保存文件
        filename = filedialog.asksaveasfilename(
            title="保存导出数据",
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if filename:
            success, message = self.export_service.save_export_to_file(self.export_data, filename)
            if success:
                messagebox.showinfo("保存成功", message)
            else:
                messagebox.showerror("保存失败", message)

    def browse_file(self):
        """浏览选择导入文件"""
        filename = filedialog.askopenfilename(
            title="选择导入文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )

        if filename:
            self.file_path_var.set(filename)

    def preview_import(self):
        """预览导入"""
        # 获取导入数据
        import_data = self._get_import_data()
        if not import_data:
            return

        # 验证数据
        valid, message, errors = self.export_service.validate_export_data(import_data)
        if not valid:
            error_text = f"数据验证失败:\n{message}\n\n详细错误:\n" + "\n".join(errors)
            messagebox.showerror("数据验证失败", error_text)
            return

        # 获取预览信息
        preview_info = self.export_service.get_import_preview(import_data)

        # 显示预览
        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete(1.0, tk.END)

        preview_text = f"""导入预览
{'='*50}

总订阅源数量: {preview_info['total_count']}
将要添加: {preview_info['new_count']} 个
将要跳过: {preview_info['existing_count']} 个 (已存在)

分类分布:
"""

        for category in preview_info['categories']:
            count = sum(1 for item in import_data if item.get('category') == category)
            preview_text += f"  • {category}: {count} 个\n"

        if preview_info['existing_count'] > 0:
            preview_text += f"\n跳过的订阅源 (已存在):\n"
            for item in import_data:
                url = item.get('url', '')
                if self.export_service.custom_rss_service.subscription_manager.get_feed_by_url(url):
                    preview_text += f"  • {item.get('title', 'Unknown')}\n"

        self.preview_text.insert(1.0, preview_text)
        self.preview_text.config(state=tk.DISABLED)

        # 启用导入按钮
        if preview_info['new_count'] > 0:
            self.import_button.config(state=tk.NORMAL)
            messagebox.showinfo("预览完成",
                              f"预览完成！\n\n将添加 {preview_info['new_count']} 个新订阅源\n"
                              f"跳过 {preview_info['existing_count']} 个已存在的订阅源")
        else:
            self.import_button.config(state=tk.DISABLED)
            messagebox.showinfo("预览完成", "所有订阅源都已存在，无需导入")

    def _get_import_data(self) -> Optional[List[Dict[str, Any]]]:
        """获取导入数据"""
        source = self.import_source_var.get()

        if source == "current":
            if not self.export_data:
                messagebox.showwarning("警告", "请先导出订阅源数据")
                return None
            return self.export_data

        elif source == "file":
            file_path = self.file_path_var.get().strip()
            if not file_path:
                messagebox.showwarning("警告", "请选择导入文件")
                return None

            success, message, import_data = self.export_service.load_export_from_file(file_path)
            if not success:
                messagebox.showerror("加载失败", message)
                return None

            return import_data

        return None

    def start_import(self):
        """开始导入"""
        # 获取导入数据
        import_data = self._get_import_data()
        if not import_data:
            return

        # 确认导入
        preview_info = self.export_service.get_import_preview(import_data)
        if preview_info['new_count'] == 0:
            messagebox.showinfo("无需导入", "所有订阅源都已存在，无需导入")
            return

        confirm_msg = f"确定要导入 {preview_info['new_count']} 个新订阅源吗？\n\n"
        confirm_msg += f"总数: {preview_info['total_count']}\n"
        confirm_msg += f"新增: {preview_info['new_count']}\n"
        confirm_msg += f"跳过: {preview_info['existing_count']}"

        if not messagebox.askyesno("确认导入", confirm_msg):
            return

        # 启动导入进度对话框
        progress_dialog = SubscriptionImportProgressDialog(self.dialog, import_data)

        # 检查导入结果
        if progress_dialog.result and progress_dialog.completed:
            results = progress_dialog.result
            if results.get('success', 0) > 0:
                messagebox.showinfo("导入完成",
                                  f"导入完成！\n\n"
                                  f"成功添加: {results.get('success', 0)} 个订阅源\n"
                                  f"跳过: {results.get('skipped', 0)} 个\n"
                                  f"失败: {results.get('failed', 0)} 个")

                # 调用导入完成回调
                if self.import_callback:
                    try:
                        self.import_callback()
                    except Exception as e:
                        print(f"导入回调执行失败: {e}")

                # 关闭当前对话框
                self.dialog.destroy()
