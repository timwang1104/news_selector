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

    def __init__(self, parent_frame: ttk.Frame, article_callback=None, auth=None, subscription_callback=None):
        self.parent_frame = parent_frame
        self.custom_rss_service = CustomRSSService()
        self.article_callback = article_callback  # 回调函数，用于通知主窗口更新文章列表
        self.auth = auth  # 认证信息
        self.subscription_callback = subscription_callback  # 回调函数，用于通知主窗口订阅源选择变化

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

        # 使用提示
        tip_frame = ttk.Frame(main_frame)
        tip_frame.pack(fill=tk.X, pady=(0, 5))

        tip_label = ttk.Label(tip_frame,
                             text="💡 提示：选择RSS订阅源后，在右侧文章列表中右键点击文章进行筛选测试",
                             font=("Arial", 9),
                             foreground="gray")
        tip_label.pack(anchor=tk.W)

        # 搜索栏
        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(search_frame, text="清除", command=self.clear_search).pack(side=tk.LEFT, padx=(0, 10))
        
        # 搜索提示
        search_tip = ttk.Label(search_frame, text="💡 支持按标题、分类、URL搜索", 
                              font=("Arial", 8), foreground="gray")
        search_tip.pack(side=tk.LEFT, padx=(10, 0))
        
        # 工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="添加RSS", command=self.add_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="导入预设源", command=self.import_preset_feeds).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="编辑", command=self.edit_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="启用/停用", command=self.toggle_feed_status).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="删除", command=self.remove_rss_subscription).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="刷新选中", command=self.refresh_selected_feed).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="全部刷新", command=self.refresh_all_feeds).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(toolbar, text="清理旧文章", command=self.cleanup_old_articles).pack(side=tk.LEFT)
        
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
        self.feed_tree.bind("<Button-1>", self.on_main_header_click)
        
        # 主列表排序状态
        self.main_sort_column = None
        self.main_sort_reverse = False
    

    
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
        values = self.feed_tree.item(item)["values"]
        if not values:
            return
        
        # 通过标题查找对应的feed对象
        feed_title = values[0]  # 第一列是标题
        feed = None
        for f in self.current_rss_feeds:
            if f.title == feed_title:
                feed = f
                break
        
        if not feed:
            messagebox.showerror("错误", "未找到对应的RSS订阅源")
            return
        
        # 确认删除
        if messagebox.askyesno("确认删除", f"确定要删除RSS订阅源 '{feed.title}' 吗？"):
            success, message = self.custom_rss_service.remove_subscription(feed.id)
            
            if success:
                messagebox.showinfo("成功", message)
                self.refresh_rss_feed_list()
                # 清除选中状态
                self.selected_feed = None
                if hasattr(self, 'current_rss_articles'):
                    self.current_rss_articles.clear()
                if hasattr(self, 'update_article_list'):
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

    def cleanup_old_articles(self):
        """清理旧的未读文章"""
        from tkinter import simpledialog

        # 询问保留天数
        days = simpledialog.askinteger(
            "清理设置",
            "请输入要保留的天数（默认7天）：",
            initialvalue=7,
            minvalue=1,
            maxvalue=365
        )

        if days is None:  # 用户取消
            return

        # 确认清理
        if not messagebox.askyesno(
            "确认清理",
            f"确定要删除 {days} 天前的所有未读文章吗？\n\n"
            "注意：此操作不可撤销！"
        ):
            return

        def cleanup():
            try:
                removed_count, feeds_count = self.custom_rss_service.cleanup_old_unread_articles(days)

                # 在主线程中更新UI
                self.parent_frame.after(0, lambda: self._handle_cleanup_result(removed_count, feeds_count, days))
            except Exception as e:
                self.parent_frame.after(0, lambda: messagebox.showerror("错误", f"清理失败: {e}"))

        # 在后台线程中执行
        threading.Thread(target=cleanup, daemon=True).start()

    def _handle_cleanup_result(self, removed_count: int, feeds_count: int, days: int):
        """处理清理结果"""
        if removed_count > 0:
            message = f"清理完成！\n\n从 {feeds_count} 个订阅源中删除了 {removed_count} 篇 {days} 天前的未读文章。"
            messagebox.showinfo("清理完成", message)

            # 刷新界面
            self.refresh_rss_feed_list()
            if self.selected_feed:
                self.load_feed_articles(self.selected_feed)
        else:
            messagebox.showinfo("清理完成", f"没有找到需要清理的 {days} 天前的未读文章。")

    def on_feed_select(self, event):
        """RSS订阅源选择事件"""
        selection = self.feed_tree.selection()
        if not selection:
            self.selected_feed = None
            # 通知主窗口清除订阅源选择
            if self.subscription_callback:
                self.subscription_callback(None)
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
                # 通过回调通知主窗口更新订阅源选择
                if self.subscription_callback:
                    self.subscription_callback(feed)
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

        # 获取搜索关键词
        search_keyword = getattr(self, 'search_var', None)
        search_text = search_keyword.get().lower().strip() if search_keyword else ""
        
        # 筛选订阅源（根据搜索条件过滤）
        filtered_feeds = []
        for feed in self.current_rss_feeds:
            # 如果有搜索条件，进行过滤
            if search_text:
                if not self._match_search_criteria(feed, search_text):
                    continue
            filtered_feeds.append(feed)
        
        # 排序
        if self.main_sort_column:
            if self.main_sort_column == "title":
                filtered_feeds.sort(key=lambda x: x.title.lower(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "category":
                filtered_feeds.sort(key=lambda x: x.category.lower(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "unread":
                filtered_feeds.sort(key=lambda x: x.get_unread_count(), reverse=self.main_sort_reverse)
            elif self.main_sort_column == "status":
                filtered_feeds.sort(key=lambda x: x.is_active, reverse=self.main_sort_reverse)
        
        # 添加订阅源到树形控件
        for feed in filtered_feeds:
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

    def show_feed_context_menu(self, event):
        """显示订阅源右键菜单"""
        # TODO: 实现右键菜单
        pass
    
    def on_main_header_click(self, event):
        """主列表列标题点击事件"""
        region = self.feed_tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.feed_tree.identify_column(event.x)
            self.sort_main_list_by_column(column)
    
    def sort_main_list_by_column(self, column):
        """主列表按列排序"""
        # 确定排序列和对应的属性
        if column == "#1":  # 标题列
            sort_key = "title"
            column_name = "title"
        elif column == "#2":  # 分类列
            sort_key = "category"
            column_name = "category"
        elif column == "#3":  # 未读列
            sort_key = "unread"
            column_name = "unread"
        elif column == "#4":  # 状态列
            sort_key = "status"
            column_name = "status"
        else:
            return
        
        # 如果点击的是同一列，则反转排序
        if self.main_sort_column == sort_key:
            self.main_sort_reverse = not self.main_sort_reverse
        else:
            self.main_sort_column = sort_key
            self.main_sort_reverse = False
        
        # 更新主列表列标题显示排序指示器
        self.update_main_column_headers()
        
        # 重新更新列表（带排序）
        self.update_feed_list()
    
    def update_main_column_headers(self):
        """更新主列表列标题显示排序指示器"""
        # 清除所有列的排序指示器
        self.feed_tree.heading("title", text="标题")
        self.feed_tree.heading("category", text="分类")
        self.feed_tree.heading("unread", text="未读")
        self.feed_tree.heading("status", text="状态")
        
        # 为当前排序列添加指示器
        if self.main_sort_column:
            arrow = " ↓" if self.main_sort_reverse else " ↑"
            if self.main_sort_column == "title":
                self.feed_tree.heading("title", text="标题" + arrow)
            elif self.main_sort_column == "category":
                self.feed_tree.heading("category", text="分类" + arrow)
            elif self.main_sort_column == "unread":
                self.feed_tree.heading("unread", text="未读" + arrow)
            elif self.main_sort_column == "status":
                self.feed_tree.heading("status", text="状态" + arrow)
    
    def on_search_change(self, *args):
        """搜索框内容变化事件"""
        self.update_feed_list()
    
    def clear_search(self):
        """清除搜索"""
        self.search_var.set("")
    
    def _match_search_criteria(self, feed, search_text):
        """检查RSS订阅源是否匹配搜索条件"""
        # 在标题中搜索
        if search_text in feed.title.lower():
            return True
        
        # 在分类中搜索
        if search_text in feed.category.lower():
            return True
        
        # 在URL中搜索
        if search_text in feed.url.lower():
            return True
        
        # 在描述中搜索（如果有）
        if hasattr(feed, 'description') and feed.description:
            if search_text in feed.description.lower():
                return True
        
        return False
    
    def import_preset_feeds(self):
        """导入预设RSS源"""
        dialog = PresetRSSDialog(self.parent_frame)
        if dialog.result:
            selected_feeds = dialog.result
            
            def add_feeds():
                try:
                    success_count = 0
                    total_count = len(selected_feeds)
                    
                    for feed_data in selected_feeds:
                        success, message = self.custom_rss_service.add_subscription(
                            feed_data['url'], 
                            feed_data['category']
                        )
                        if success:
                            success_count += 1
                    
                    # 在主线程中更新UI
                    self.parent_frame.after(0, lambda: self._handle_import_result(success_count, total_count))
                except Exception as e:
                    self.parent_frame.after(0, lambda: messagebox.showerror("错误", f"导入预设RSS源失败: {e}"))
            
            # 在后台线程中执行
            threading.Thread(target=add_feeds, daemon=True).start()
    
    def _handle_import_result(self, success_count: int, total_count: int):
        """处理导入结果"""
        if success_count > 0:
            messagebox.showinfo("导入完成", f"成功导入 {success_count}/{total_count} 个RSS源")
            self.refresh_rss_feed_list()
        else:
            messagebox.showwarning("导入失败", "没有成功导入任何RSS源，可能已存在相同的源")


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


class PresetRSSDialog:
    """预设RSS源选择对话框"""

    def __init__(self, parent):
        self.result = None
        
        # 导入预设RSS源数据
        from ..data.preset_rss_feeds import PRESET_RSS_FEEDS, RSS_CATEGORIES
        self.preset_feeds = PRESET_RSS_FEEDS
        self.categories = RSS_CATEGORIES

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("导入预设RSS源")
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
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(title_frame, text="选择要导入的预设RSS源", font=("Arial", 14, "bold")).pack(side=tk.LEFT)
        
        # 统计信息
        total_feeds = len(self.preset_feeds)
        ttk.Label(title_frame, text=f"共 {total_feeds} 个预设源", 
                 font=("Arial", 10), foreground="gray").pack(side=tk.RIGHT)

        # 分类筛选
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="分类筛选:").pack(side=tk.LEFT, padx=(0, 5))
        self.category_var = tk.StringVar(value="全部")
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, 
                                     values=["全部"] + list(self.categories.keys()),
                                     state="readonly", width=15)
        category_combo.pack(side=tk.LEFT, padx=(0, 10))
        category_combo.bind("<<ComboboxSelected>>", self.on_category_change)
        
        # 全选/全不选按钮
        ttk.Button(filter_frame, text="全选", command=self.select_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(filter_frame, text="全不选", command=self.select_none).pack(side=tk.LEFT)

        # RSS源列表
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 创建Treeview
        self.feed_tree = ttk.Treeview(list_frame, columns=("name", "category", "description"), 
                                     show="tree headings", height=15)
        self.feed_tree.heading("#0", text="选择")
        self.feed_tree.heading("name", text="名称")
        self.feed_tree.heading("category", text="分类")
        self.feed_tree.heading("description", text="描述")
        
        # 设置列宽
        self.feed_tree.column("#0", width=60)
        self.feed_tree.column("name", width=200)
        self.feed_tree.column("category", width=100)
        self.feed_tree.column("description", width=300)
        
        # 滚动条
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.feed_tree.yview)
        self.feed_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.feed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.feed_tree.bind("<Button-1>", self.on_tree_click)
        self.feed_tree.bind("<Button-1>", self.on_header_click, add="+")
        
        # 排序状态
        self.sort_column = None
        self.sort_reverse = False
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="取消", command=self.cancel).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="导入选中", command=self.import_selected).pack(side=tk.RIGHT)
        
        # 初始化数据
        self.populate_feeds()

    def populate_feeds(self):
        """填充RSS源列表"""
        # 清空现有项目
        for item in self.feed_tree.get_children():
            self.feed_tree.delete(item)
        
        # 获取当前选择的分类
        selected_category = self.category_var.get()
        
        # 筛选RSS源
        filtered_feeds = []
        for feed in self.preset_feeds:
            # 分类筛选
            if selected_category != "全部" and feed["category"] != selected_category:
                continue
            filtered_feeds.append(feed)
        
        # 排序
        if self.sort_column:
            filtered_feeds.sort(
                key=lambda x: x[self.sort_column].lower() if isinstance(x[self.sort_column], str) else str(x[self.sort_column]).lower(),
                reverse=self.sort_reverse
            )
        
        # 添加RSS源到树形控件
        for feed in filtered_feeds:
            item_id = self.feed_tree.insert("", "end", 
                                            text="☐",  # 未选中状态
                                            values=(feed["name"], feed["category"], feed["description"]))

    def on_category_change(self, event=None):
        """分类选择变化事件"""
        self.populate_feeds()

    def on_tree_click(self, event):
        """树形控件点击事件"""
        region = self.feed_tree.identify_region(event.x, event.y)
        if region == "tree":
            item = self.feed_tree.identify_row(event.y)
            if item:
                self.toggle_selection(item)
    
    def on_header_click(self, event):
        """列标题点击事件"""
        region = self.feed_tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.feed_tree.identify_column(event.x)
            self.sort_by_column(column)
    
    def sort_by_column(self, column):
        """按列排序"""
        # 确定排序列
        if column == "#1":  # 名称列
            sort_key = "name"
        elif column == "#2":  # 分类列
            sort_key = "category"
        elif column == "#3":  # 描述列
            sort_key = "description"
        else:
            return
        
        # 如果点击的是同一列，则反转排序
        if self.sort_column == sort_key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = sort_key
            self.sort_reverse = False
        
        # 更新列标题显示排序指示器
        self.update_column_headers()
        
        # 重新填充列表（带排序）
        self.populate_feeds()
    
    def update_column_headers(self):
        """更新列标题显示排序指示器"""
        # 清除所有列的排序指示器
        self.feed_tree.heading("name", text="名称")
        self.feed_tree.heading("category", text="分类")
        self.feed_tree.heading("description", text="描述")
        
        # 为当前排序列添加指示器
        if self.sort_column:
            arrow = " ↓" if self.sort_reverse else " ↑"
            if self.sort_column == "name":
                self.feed_tree.heading("name", text="名称" + arrow)
            elif self.sort_column == "category":
                self.feed_tree.heading("category", text="分类" + arrow)
            elif self.sort_column == "description":
                self.feed_tree.heading("description", text="描述" + arrow)

    def toggle_selection(self, item):
        """切换选择状态"""
        current_text = self.feed_tree.item(item, "text")
        if current_text == "☐":
            self.feed_tree.item(item, text="☑")
        else:
            self.feed_tree.item(item, text="☐")

    def select_all(self):
        """全选"""
        for item in self.feed_tree.get_children():
            self.feed_tree.item(item, text="☑")

    def select_none(self):
        """全不选"""
        for item in self.feed_tree.get_children():
            self.feed_tree.item(item, text="☐")

    def import_selected(self):
         """导入选中的RSS源"""
         selected_feeds = []
         
         for item in self.feed_tree.get_children():
             if self.feed_tree.item(item, "text") == "☑":
                 values = self.feed_tree.item(item, "values")
                 # 从原始数据中获取完整信息
                 for feed in self.preset_feeds:
                     if (feed["name"] == values[0] and 
                         feed["category"] == values[1] and 
                         feed["description"] == values[2]):
                         selected_feeds.append(feed)
                         break
         
         if not selected_feeds:
             messagebox.showwarning("警告", "请至少选择一个RSS源", parent=self.dialog)
             return
         
         self.result = selected_feeds
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
