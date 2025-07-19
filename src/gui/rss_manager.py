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

    def __init__(self, parent_frame: ttk.Frame, article_callback=None):
        self.parent_frame = parent_frame
        self.custom_rss_service = CustomRSSService()
        self.article_callback = article_callback  # 回调函数，用于通知主窗口更新文章列表

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

        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="添加RSS", command=self.add_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="预设源", command=self.show_preset_feeds).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="编辑", command=self.edit_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="启用/停用", command=self.toggle_feed_status).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="删除", command=self.remove_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="刷新选中", command=self.refresh_selected_feed).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="全部刷新", command=self.refresh_all_feeds).pack(side=tk.LEFT)
        
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
        feed_id = self.feed_tree.item(item)["values"][0] if self.feed_tree.item(item)["values"] else None
        
        if not feed_id:
            return
        
        # 获取订阅源信息
        feed = self.custom_rss_service.subscription_manager.get_feed_by_id(feed_id)
        if not feed:
            return
        
        # 确认删除
        if messagebox.askyesno("确认删除", f"确定要删除RSS订阅源 '{feed.title}' 吗？"):
            success, message = self.custom_rss_service.remove_subscription(feed_id)
            
            if success:
                messagebox.showinfo("成功", message)
                self.refresh_rss_feed_list()
                self.current_rss_articles.clear()
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

    def on_feed_select(self, event):
        """RSS订阅源选择事件"""
        selection = self.feed_tree.selection()
        if not selection:
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
                # 通过回调通知主窗口更新文章列表
                if self.article_callback:
                    self.article_callback(feed.articles, f"RSS: {feed.title}")
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

        # 添加订阅源
        for feed in self.current_rss_feeds:
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

    def show_preset_feeds(self):
        """显示预设RSS源选择对话框"""
        PresetFeedsDialog(self.parent_frame, self.custom_rss_service, self.refresh_rss_feed_list)

    def show_feed_context_menu(self, event):
        """显示订阅源右键菜单"""
        # TODO: 实现右键菜单
        pass


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


class PresetFeedsDialog:
    """预设RSS源选择对话框"""

    def __init__(self, parent, rss_service, refresh_callback):
        self.rss_service = rss_service
        self.refresh_callback = refresh_callback
        self.selected_feeds = []

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("添加预设RSS源")
        self.dialog.geometry("800x600")
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

        # 标题
        ttk.Label(main_frame, text="选择要添加的RSS源", font=("Arial", 14, "bold")).pack(pady=(0, 15))

        # 创建左右分割面板
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # 左侧：分类列表
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)

        ttk.Label(left_frame, text="分类", font=("Arial", 12, "bold")).pack(pady=(0, 5))

        # 分类列表
        self.category_listbox = tk.Listbox(left_frame, width=20)
        self.category_listbox.pack(fill=tk.BOTH, expand=True)

        # 加载分类
        from ..data.preset_rss_feeds import get_all_categories
        categories = get_all_categories()
        for category in categories:
            self.category_listbox.insert(tk.END, category)

        # 绑定分类选择事件
        self.category_listbox.bind("<<ListboxSelect>>", self.on_category_select)

        # 右侧：RSS源列表
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=2)

        ttk.Label(right_frame, text="RSS源", font=("Arial", 12, "bold")).pack(pady=(0, 5))

        # RSS源树形视图
        columns = ("name", "description")
        self.feeds_tree = ttk.Treeview(right_frame, columns=columns, show="tree headings")
        self.feeds_tree.heading("#0", text="选择")
        self.feeds_tree.heading("name", text="名称")
        self.feeds_tree.heading("description", text="描述")

        self.feeds_tree.column("#0", width=50)
        self.feeds_tree.column("name", width=150)
        self.feeds_tree.column("description", width=300)

        # 滚动条
        feeds_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.feeds_tree.yview)
        self.feeds_tree.configure(yscrollcommand=feeds_scrollbar.set)

        self.feeds_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        feeds_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        ttk.Button(button_frame, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="全不选", command=self.deselect_all).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="添加选中", command=self.add_selected).pack(side=tk.RIGHT)

        # 默认选择第一个分类
        if categories:
            self.category_listbox.selection_set(0)
            self.on_category_select(None)

    def on_category_select(self, event):
        """分类选择事件"""
        selection = self.category_listbox.curselection()
        if not selection:
            return

        category = self.category_listbox.get(selection[0])

        # 清空RSS源列表
        for item in self.feeds_tree.get_children():
            self.feeds_tree.delete(item)

        # 清空数据映射
        if hasattr(self, 'feed_data_map'):
            self.feed_data_map.clear()

        # 加载该分类的RSS源
        from ..data.preset_rss_feeds import get_feeds_by_category
        feeds = get_feeds_by_category(category)

        # 存储feed数据的字典
        self.feed_data_map = {}

        for feed in feeds:
            # 检查是否已存在
            existing_feed = self.rss_service.subscription_manager.get_feed_by_url(feed["url"])

            item_id = self.feeds_tree.insert("", tk.END, values=(
                feed["name"],
                feed["description"]
            ), tags=("existing" if existing_feed else "new",))

            # 存储feed数据到字典中
            self.feed_data_map[item_id] = feed

        # 设置标签样式
        self.feeds_tree.tag_configure("existing", foreground="gray")
        self.feeds_tree.tag_configure("new", foreground="black")

    def select_all(self):
        """全选当前分类的RSS源"""
        for item in self.feeds_tree.get_children():
            tags = self.feeds_tree.item(item)["tags"]
            if "new" in tags:  # 只选择未添加的
                self.feeds_tree.selection_add(item)

    def deselect_all(self):
        """取消全选"""
        self.feeds_tree.selection_remove(self.feeds_tree.selection())

    def add_selected(self):
        """添加选中的RSS源"""
        selection = self.feeds_tree.selection()
        if not selection:
            messagebox.showwarning("提示", "请选择要添加的RSS源", parent=self.dialog)
            return

        added_count = 0
        failed_feeds = []

        for item_id in selection:
            # 检查是否已存在
            tags = self.feeds_tree.item(item_id)["tags"]
            if "existing" in tags:
                continue

            # 获取feed数据
            feed_data = self.feed_data_map.get(item_id)
            if not feed_data:
                continue

            # 添加RSS源
            success, message = self.rss_service.add_subscription(
                feed_data["url"],
                feed_data["category"]
            )

            if success:
                added_count += 1
            else:
                failed_feeds.append(f"{feed_data['name']}: {message}")

        # 显示结果
        if added_count > 0:
            messagebox.showinfo("成功", f"成功添加 {added_count} 个RSS源", parent=self.dialog)
            # 刷新主界面
            if self.refresh_callback:
                self.refresh_callback()

        if failed_feeds:
            error_msg = "以下RSS源添加失败:\n" + "\n".join(failed_feeds)
            messagebox.showerror("部分失败", error_msg, parent=self.dialog)

        if added_count == 0 and not failed_feeds:
            messagebox.showinfo("提示", "所选RSS源已存在", parent=self.dialog)

        # 关闭对话框
        self.dialog.destroy()

    def cancel(self):
        """取消按钮"""
        self.dialog.destroy()
