"""
关键词编辑器对话框
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from typing import Dict, List


class KeywordEditorDialog:
    """关键词编辑器对话框"""
    
    def __init__(self, parent, keywords_data: Dict[str, List[str]]):
        self.parent = parent
        self.keywords_data = keywords_data
        self.result = False
        
        # 如果没有关键词数据，加载默认的
        if not self.keywords_data:
            from ..config.default_keywords import INTERNATIONAL_TECH_KEYWORDS
            # 转换格式：从 {category: {keywords: [...], weight: ...}} 到 {category: [...]}
            for category, data in INTERNATIONAL_TECH_KEYWORDS.items():
                self.keywords_data[category] = data.get("keywords", [])
        
        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("关键词编辑器")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 创建界面
        self.create_widgets()
        self.load_keywords()
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
        
        # 说明标签
        info_label = ttk.Label(main_frame, 
                              text="编辑科技政策关键词库。左侧选择分类，右侧编辑该分类的关键词。",
                              foreground="gray")
        info_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 主要内容区域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左侧分类列表
        left_frame = ttk.LabelFrame(content_frame, text="关键词分类")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 分类列表
        self.category_listbox = tk.Listbox(left_frame, width=25, height=20)
        self.category_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.category_listbox.bind("<<ListboxSelect>>", self.on_category_select)
        
        # 分类操作按钮
        category_buttons = ttk.Frame(left_frame)
        category_buttons.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(category_buttons, text="新增分类", 
                  command=self.add_category).pack(fill=tk.X, pady=1)
        ttk.Button(category_buttons, text="重命名分类", 
                  command=self.rename_category).pack(fill=tk.X, pady=1)
        ttk.Button(category_buttons, text="删除分类", 
                  command=self.delete_category).pack(fill=tk.X, pady=1)
        
        # 右侧关键词编辑区域
        right_frame = ttk.LabelFrame(content_frame, text="关键词编辑")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 当前分类显示
        self.current_category_label = ttk.Label(right_frame, text="请选择一个分类", 
                                               font=("", 10, "bold"))
        self.current_category_label.pack(anchor=tk.W, padx=5, pady=5)
        
        # 关键词编辑区域
        edit_frame = ttk.Frame(right_frame)
        edit_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 关键词文本编辑器
        ttk.Label(edit_frame, text="关键词列表（每行一个）:").pack(anchor=tk.W)
        
        self.keywords_text = scrolledtext.ScrolledText(edit_frame, height=15, wrap=tk.WORD)
        self.keywords_text.pack(fill=tk.BOTH, expand=True, pady=(5, 10))
        
        # 关键词操作按钮
        keyword_buttons = ttk.Frame(edit_frame)
        keyword_buttons.pack(fill=tk.X)
        
        ttk.Button(keyword_buttons, text="保存关键词", 
                  command=self.save_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons, text="排序关键词", 
                  command=self.sort_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons, text="去重关键词", 
                  command=self.deduplicate_keywords).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(keyword_buttons, text="清空关键词", 
                  command=self.clear_keywords).pack(side=tk.LEFT)
        
        # 统计信息
        self.stats_label = ttk.Label(edit_frame, text="", foreground="gray")
        self.stats_label.pack(anchor=tk.W, pady=(5, 0))
        
        # 底部按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="保存并关闭", 
                  command=self.save_and_close).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", 
                  command=self.cancel).pack(side=tk.RIGHT)
        
        # 左侧额外功能
        ttk.Button(button_frame, text="导入分类", 
                  command=self.import_category).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="导出分类", 
                  command=self.export_category).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="重置为默认", 
                  command=self.reset_to_default).pack(side=tk.LEFT)
    
    def load_keywords(self):
        """加载关键词到界面"""
        # 清空分类列表
        self.category_listbox.delete(0, tk.END)
        
        # 添加分类
        for category in sorted(self.keywords_data.keys()):
            self.category_listbox.insert(tk.END, category)
        
        # 选择第一个分类
        if self.category_listbox.size() > 0:
            self.category_listbox.selection_set(0)
            self.on_category_select()
    
    def on_category_select(self, event=None):
        """分类选择事件"""
        selection = self.category_listbox.curselection()
        if selection:
            category = self.category_listbox.get(selection[0])
            self.current_category_label.config(text=f"当前分类: {category}")
            
            # 加载该分类的关键词
            keywords = self.keywords_data.get(category, [])
            self.keywords_text.delete(1.0, tk.END)
            self.keywords_text.insert(1.0, "\n".join(keywords))
            
            # 更新统计信息
            self.update_stats(len(keywords))
        else:
            self.current_category_label.config(text="请选择一个分类")
            self.keywords_text.delete(1.0, tk.END)
            self.update_stats(0)
    
    def update_stats(self, count: int):
        """更新统计信息"""
        total_categories = len(self.keywords_data)
        total_keywords = sum(len(keywords) for keywords in self.keywords_data.values())
        
        stats_text = f"当前分类: {count} 个关键词 | 总计: {total_categories} 个分类，{total_keywords} 个关键词"
        self.stats_label.config(text=stats_text)
    
    def add_category(self):
        """添加新分类"""
        category_name = tk.simpledialog.askstring("新增分类", "请输入分类名称:")
        if category_name:
            category_name = category_name.strip()
            if category_name in self.keywords_data:
                messagebox.showwarning("警告", "分类已存在")
                return
            
            self.keywords_data[category_name] = []
            self.load_keywords()
            
            # 选择新添加的分类
            for i in range(self.category_listbox.size()):
                if self.category_listbox.get(i) == category_name:
                    self.category_listbox.selection_clear(0, tk.END)
                    self.category_listbox.selection_set(i)
                    self.on_category_select()
                    break
    
    def rename_category(self):
        """重命名分类"""
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要重命名的分类")
            return
        
        old_name = self.category_listbox.get(selection[0])
        new_name = tk.simpledialog.askstring("重命名分类", f"请输入新的分类名称:", initialvalue=old_name)
        
        if new_name and new_name.strip() != old_name:
            new_name = new_name.strip()
            if new_name in self.keywords_data:
                messagebox.showwarning("警告", "分类名称已存在")
                return
            
            # 重命名
            self.keywords_data[new_name] = self.keywords_data.pop(old_name)
            self.load_keywords()
    
    def delete_category(self):
        """删除分类"""
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的分类")
            return
        
        category = self.category_listbox.get(selection[0])
        if messagebox.askyesno("确认删除", f"确定要删除分类 '{category}' 吗？"):
            del self.keywords_data[category]
            self.load_keywords()
    
    def save_keywords(self):
        """保存当前分类的关键词"""
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个分类")
            return
        
        category = self.category_listbox.get(selection[0])
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        
        # 解析关键词
        keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        self.keywords_data[category] = keywords
        
        # 更新统计信息
        self.update_stats(len(keywords))
        messagebox.showinfo("成功", f"已保存 {len(keywords)} 个关键词到分类 '{category}'")
    
    def sort_keywords(self):
        """排序关键词"""
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        
        # 排序
        keywords.sort()
        
        # 更新文本
        self.keywords_text.delete(1.0, tk.END)
        self.keywords_text.insert(1.0, '\n'.join(keywords))
    
    def deduplicate_keywords(self):
        """去重关键词"""
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        keywords = [kw.strip() for kw in keywords_text.split('\n') if kw.strip()]
        
        # 去重并保持顺序
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw.lower() not in seen:
                seen.add(kw.lower())
                unique_keywords.append(kw)
        
        # 更新文本
        self.keywords_text.delete(1.0, tk.END)
        self.keywords_text.insert(1.0, '\n'.join(unique_keywords))
        
        removed_count = len(keywords) - len(unique_keywords)
        if removed_count > 0:
            messagebox.showinfo("去重完成", f"已移除 {removed_count} 个重复关键词")
    
    def clear_keywords(self):
        """清空关键词"""
        if messagebox.askyesno("确认清空", "确定要清空当前分类的所有关键词吗？"):
            self.keywords_text.delete(1.0, tk.END)
    
    def import_category(self):
        """导入分类"""
        from tkinter import filedialog
        
        file_path = filedialog.askopenfilename(
            title="导入分类文件",
            filetypes=[("JSON文件", "*.json"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        imported_data = json.load(f)
                    
                    if isinstance(imported_data, dict):
                        self.keywords_data.update(imported_data)
                        self.load_keywords()
                        messagebox.showinfo("成功", "分类导入成功")
                    else:
                        messagebox.showerror("错误", "JSON文件格式不正确")
                
                elif file_path.endswith('.txt'):
                    category_name = tk.simpledialog.askstring("分类名称", "请输入导入的分类名称:")
                    if category_name:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            keywords = [line.strip() for line in f if line.strip()]
                        
                        self.keywords_data[category_name] = keywords
                        self.load_keywords()
                        messagebox.showinfo("成功", f"已导入 {len(keywords)} 个关键词到分类 '{category_name}'")
                
            except Exception as e:
                messagebox.showerror("错误", f"导入失败: {e}")
    
    def export_category(self):
        """导出当前分类"""
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要导出的分类")
            return
        
        category = self.category_listbox.get(selection[0])
        keywords = self.keywords_data.get(category, [])
        
        from tkinter import filedialog
        
        file_path = filedialog.asksaveasfilename(
            title="导出分类",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({category: keywords}, f, ensure_ascii=False, indent=2)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write('\n'.join(keywords))
                
                messagebox.showinfo("成功", f"分类 '{category}' 导出成功")
            except Exception as e:
                messagebox.showerror("错误", f"导出失败: {e}")
    
    def reset_to_default(self):
        """重置为默认关键词"""
        if messagebox.askyesno("确认重置", "确定要重置为默认关键词库吗？这将覆盖所有自定义关键词。"):
            from ..config.default_keywords import INTERNATIONAL_TECH_KEYWORDS
            self.keywords_data.clear()
            # 转换格式：从 {category: {keywords: [...], weight: ...}} 到 {category: [...]}
            for category, data in INTERNATIONAL_TECH_KEYWORDS.items():
                self.keywords_data[category] = data.get("keywords", [])
            self.load_keywords()
            messagebox.showinfo("成功", "已重置为默认关键词库")
    
    def save_and_close(self):
        """保存并关闭"""
        # 保存当前编辑的关键词
        selection = self.category_listbox.curselection()
        if selection:
            self.save_keywords()
        
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """取消"""
        self.dialog.destroy()


# 导入simpledialog
import tkinter.simpledialog
