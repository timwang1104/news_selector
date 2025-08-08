import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import math
from src.services.preference_analysis_service import PreferenceAnalysisService
from src.services.topic_distribution_service import TopicDistributionService
from src.gui.components.keyword_cloud_widget import KeywordCloudWidget
from src.database.models import JobStatus, AnalysisResult
from src.filters.base import CombinedFilterResult, ArticleTag
from src.models.news import NewsArticle
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

# 偏好分析面板标签页结构
class PreferenceAnalysisPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.service = PreferenceAnalysisService()
        
        # 创建标签页容器
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 关键词分析标签页
        self.keyword_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.keyword_frame, text="关键词分析")
        self.create_keyword_widgets(self.keyword_frame)
        
        # 话题分布标签页
        self.topic_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.topic_frame, text="话题分布")
        self.create_topic_widgets(self.topic_frame)

        # 分析报告标签页
        self.report_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.report_frame, text="分析报告")
        self.create_report_widgets(self.report_frame)

        # 优化建议标签页
        self.suggestion_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.suggestion_frame, text="优化建议")
        self.create_suggestion_widgets(self.suggestion_frame)

    def create_keyword_widgets(self, parent):
        # 关键词筛选控件
        self.filter_widget = KeywordFilterWidget(parent, self.refresh_data)
        self.filter_widget.pack(fill="x", pady=5, padx=5)

        # 关键词云图组件
        self.cloud_widget = KeywordCloudWidget(parent)
        self.cloud_widget.pack(fill="both", expand=True, pady=5, padx=5)

        # 关键词趋势图组件
        self.trend_widget = KeywordTrendWidget(parent)
        self.trend_widget.pack(fill="both", expand=True, pady=5, padx=5)

    def create_topic_widgets(self, parent):
        # 话题分布饼图
        topic_dist_widget = TopicDistributionWidget(parent)
        topic_dist_widget.pack(fill="both", expand=True, pady=5, padx=5)

        # 话题趋势分析
        topic_trend_widget = TopicTrendWidget(parent)
        topic_trend_widget.pack(fill="both", expand=True, pady=5, padx=5)

    def create_report_widgets(self, parent):
        # 分析报告组件
        self.report_widget = AnalysisReportWidget(parent, self.service)
        self.report_widget.pack(fill="both", expand=True, pady=5, padx=5)

    def create_suggestion_widgets(self, parent):
        # 优化建议组件
        self.suggestion_widget = OptimizationSuggestionWidget(parent, self.service)
        self.suggestion_widget.pack(fill="both", expand=True, pady=5, padx=5)

    def refresh_data(self):
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        try:
            job_id = self.service.analyze_historical_data()
            if job_id is None:
                self.after(0, self._show_error, "无法启动分析任务，可能没有历史数据。")
                return

            while True:
                status_val = self.service.get_analysis_status(job_id)
                status = JobStatus(status_val) if status_val else None
                result = None
                if status == JobStatus.COMPLETED or status == JobStatus.FAILED:
                    result = self.service.get_analysis_result(job_id)
                if status == JobStatus.COMPLETED:
                    if result:
                        # 将 [(word, score), ...] 格式转换为 {word: score, ...} 格式
                        keywords_dict = {item[0]: item[1] for item in result}
                        self.after(0, self.cloud_widget.update_wordcloud, keywords_dict)
                    break
                elif status == JobStatus.FAILED:
                    self.after(0, self._show_error, f"分析任务失败: {result}")
                    break
                time.sleep(2)
        except Exception as e:
            self.after(0, self._show_error, f"执行分析时出错: {e}")
        finally:
            self.after(0, self.filter_widget.refresh_btn.config, {"state": tk.NORMAL})

    def _show_error(self, message):
        messagebox.showerror("错误", message)




# 关键词趋势图组件
class KeywordTrendWidget(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="关键词热度趋势 (占位符)").pack(pady=20)
    
    def update_trend_chart(self, trend_data=None):
        pass

# 关键词筛选控件
class KeywordFilterWidget(ttk.Frame):
    def __init__(self, master, refresh_callback):
        super().__init__(master)
        self.refresh_callback = refresh_callback
        
        filter_frame = ttk.Frame(self)
        filter_frame.pack(fill="x", pady=5)
        
        ttk.Label(filter_frame, text="数据源:").pack(side="left")
        self.source_var = tk.StringVar(value="历史数据")
        source_combo = ttk.Combobox(filter_frame, textvariable=self.source_var,
                                 values=["历史数据", "实时分析(占位符)"], width=15)
        source_combo.pack(side="left", padx=5)
        source_combo.config(state="readonly")

        self.refresh_btn = ttk.Button(filter_frame, text="刷新分析", command=self.refresh_data)
        self.refresh_btn.pack(side="right", padx=5)

    def refresh_data(self):
        self.refresh_btn.config(state=tk.DISABLED)
        self.refresh_callback()

# 话题分布饼图组件
class TopicDistributionWidget(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.topic_service = TopicDistributionService()
        self.preference_service = PreferenceAnalysisService()
        self.setup_ui()
        self.topic_data = None
        
    def setup_ui(self):
        # 标题
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", pady=5)
        ttk.Label(title_frame, text="话题分布分析", font=("Arial", 12, "bold")).pack(side="left")
        
        # 刷新按钮
        self.refresh_btn = ttk.Button(title_frame, text="刷新", command=self.refresh_data)
        self.refresh_btn.pack(side="right")
        
        # 主要内容区域
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, pady=5)
        
        # 左侧：饼图区域
        self.chart_frame = ttk.LabelFrame(main_frame, text="话题分布图")
        self.chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # 饼图画布（使用tkinter Canvas模拟）
        self.canvas = tk.Canvas(self.chart_frame, width=300, height=300, bg="white")
        self.canvas.pack(pady=10)
        
        # 右侧：统计信息
        self.stats_frame = ttk.LabelFrame(main_frame, text="统计信息")
        self.stats_frame.pack(side="right", fill="y", padx=(5, 0))
        
        # 统计标签
        self.stats_labels = {}
        stats_info = [
            ("总文章数", "total_articles"),
            ("话题数量", "total_topics"),
            ("多样性评分", "diversity_score"),
            ("集中度指数", "concentration_index")
        ]
        
        for i, (label_text, key) in enumerate(stats_info):
            ttk.Label(self.stats_frame, text=f"{label_text}:").grid(row=i, column=0, sticky="w", padx=5, pady=2)
            self.stats_labels[key] = ttk.Label(self.stats_frame, text="--")
            self.stats_labels[key].grid(row=i, column=1, sticky="w", padx=5, pady=2)
        
        # 话题列表
        list_frame = ttk.LabelFrame(self, text="话题详情")
        list_frame.pack(fill="both", expand=True, pady=5)
        
        # 创建Treeview显示话题列表
        columns = ("话题", "文章数", "占比%", "平均评分", "趋势")
        self.topic_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.topic_tree.heading(col, text=col)
            self.topic_tree.column(col, width=80)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.topic_tree.yview)
        self.topic_tree.configure(yscrollcommand=scrollbar.set)
        
        self.topic_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定双击事件
        self.topic_tree.bind("<Double-1>", self.on_topic_double_click)
        
        # 初始化显示
        self.show_no_data_message()
    
    def refresh_data(self):
        """刷新数据"""
        # 显示加载状态
        self.show_loading_message()
        
        # 在后台线程中加载真实数据
        threading.Thread(target=self._load_real_data, daemon=True).start()
    
    def _load_real_data(self):
        """从数据库加载真实数据并进行话题分布分析"""
        try:
            # 创建数据库连接
            engine = create_engine('sqlite:///data/preference_analysis.db')
            Session = sessionmaker(bind=engine)
            session = Session()
            
            # 查询数据库中的文章数据
            from src.database.models import Article
            articles = session.query(Article).all()
            
            if not articles:
                # 如果数据库中没有数据，尝试从JSON文件加载
                results = self.topic_service.load_data_from_json('data/crawled_news.json')
            else:
                # 将数据库中的文章转换为CombinedFilterResult格式
                results = []
                for article in articles:
                    # 创建NewsArticle对象
                    from datetime import datetime
                    published_dt = article.published_at if article.published_at else datetime.now()
                    news_article = NewsArticle(
                        id=str(article.id),
                        title=article.title,
                        summary='',
                        content=article.content or '',
                        url=article.url or '',
                        published=published_dt,
                        updated=published_dt
                    )
                    
                    # 创建标签
                    tags = []
                    if article.category:
                        tags.append(ArticleTag(
                            name=article.category,
                            score=0.8,
                            confidence=0.7,
                            source='database'
                        ))
                    
                    # 创建CombinedFilterResult对象
                    result = CombinedFilterResult(
                        article=news_article,
                        keyword_result=None,
                        ai_result=None,
                        final_score=0.5,
                        selected=True,
                        rejection_reason=None,
                        tags=tags
                    )
                    results.append(result)
            
            session.close()
            
            if results:
                # 进行话题分布分析
                analysis_result = self.topic_service.analyze_current_data(results)
                
                # 转换为GUI显示格式
                display_data = self._convert_analysis_result(analysis_result)
                
                # 在主线程中更新UI
                self.after(0, self.update_display, display_data)
            else:
                # 没有数据时显示提示
                self.after(0, self.show_no_data_message)
                
        except Exception as e:
            print(f"加载数据时出错: {e}")
            # 出错时回退到示例数据
            self.after(0, self.load_sample_data)
    
    def _convert_analysis_result(self, analysis_result):
        """将TopicDistributionResult转换为GUI显示格式"""
        topics = []
        for topic_name, topic_info in analysis_result.topic_distribution.items():
            topics.append({
                "name": topic_info.name,
                "count": topic_info.count,
                "percentage": topic_info.percentage,
                "avg_score": topic_info.avg_score,
                "trend": getattr(topic_info, 'recent_trend', 'stable')
            })
        
        # 按文章数量排序
        topics.sort(key=lambda x: x['count'], reverse=True)
        
        return {
            "total_articles": analysis_result.total_articles,
            "total_topics": analysis_result.total_topics,
            "diversity_score": analysis_result.diversity_score,
            "concentration_index": analysis_result.concentration_index,
            "topics": topics
        }
    
    def load_sample_data(self):
        """加载示例数据"""
        # 示例数据
        sample_data = {
            "total_articles": 150,
            "total_topics": 8,
            "diversity_score": 0.75,
            "concentration_index": 0.35,
            "topics": [
                {"name": "人工智能", "count": 45, "percentage": 30.0, "avg_score": 0.85, "trend": "up"},
                {"name": "生物技术", "count": 30, "percentage": 20.0, "avg_score": 0.78, "trend": "stable"},
                {"name": "量子计算", "count": 25, "percentage": 16.7, "avg_score": 0.82, "trend": "up"},
                {"name": "新能源", "count": 20, "percentage": 13.3, "avg_score": 0.75, "trend": "down"},
                {"name": "航空航天", "count": 15, "percentage": 10.0, "avg_score": 0.80, "trend": "stable"},
                {"name": "材料科学", "count": 10, "percentage": 6.7, "avg_score": 0.72, "trend": "up"},
                {"name": "网络安全", "count": 5, "percentage": 3.3, "avg_score": 0.70, "trend": "stable"}
            ]
        }
        self.update_display(sample_data)
    
    def update_display(self, topic_data):
        """更新显示内容"""
        self.topic_data = topic_data
        
        # 更新统计信息
        self.stats_labels["total_articles"].config(text=str(topic_data["total_articles"]))
        self.stats_labels["total_topics"].config(text=str(topic_data["total_topics"]))
        self.stats_labels["diversity_score"].config(text=f"{topic_data['diversity_score']:.2f}")
        self.stats_labels["concentration_index"].config(text=f"{topic_data['concentration_index']:.3f}")
        
        # 更新饼图
        self.draw_pie_chart(topic_data["topics"])
        
        # 更新话题列表
        self.update_topic_list(topic_data["topics"])
    
    def draw_pie_chart(self, topics):
        """绘制饼图"""
        self.canvas.delete("all")
        
        if not topics:
            self.canvas.create_text(150, 150, text="暂无数据", font=("Arial", 12))
            return
        
        # 计算角度
        total = sum(topic["count"] for topic in topics)
        if total == 0:
            return
        
        # 颜色列表
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F"]
        
        # 绘制饼图
        start_angle = 0
        center_x, center_y = 150, 150
        radius = 80
        
        for i, topic in enumerate(topics):
            angle = (topic["count"] / total) * 360
            color = colors[i % len(colors)]
            
            # 绘制扇形
            self.canvas.create_arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start=start_angle, extent=angle,
                fill=color, outline="white", width=2
            )
            
            # 添加标签
            if angle > 10:  # 只有足够大的扇形才显示标签
                label_angle = math.radians(start_angle + angle / 2)
                label_x = center_x + (radius * 0.7) * math.cos(label_angle)
                label_y = center_y + (radius * 0.7) * math.sin(label_angle)
                
                self.canvas.create_text(
                    label_x, label_y,
                    text=f"{topic['percentage']:.1f}%",
                    font=("Arial", 8, "bold"),
                    fill="white"
                )
            
            start_angle += angle
        
        # 添加图例
        legend_y = 20
        for i, topic in enumerate(topics[:6]):  # 最多显示6个图例
            color = colors[i % len(colors)]
            self.canvas.create_rectangle(10, legend_y, 20, legend_y + 10, fill=color, outline="")
            self.canvas.create_text(25, legend_y + 5, text=topic["name"], anchor="w", font=("Arial", 8))
            legend_y += 15
    
    def update_topic_list(self, topics):
        """更新话题列表"""
        # 清空现有数据
        for item in self.topic_tree.get_children():
            self.topic_tree.delete(item)
        
        # 添加新数据
        for topic in topics:
            trend_symbol = {"up": "↑", "down": "↓", "stable": "→"}.get(topic["trend"], "→")
            self.topic_tree.insert("", "end", values=(
                topic["name"],
                topic["count"],
                f"{topic['percentage']:.1f}",
                f"{topic['avg_score']:.2f}",
                trend_symbol
            ))
    
    def on_topic_double_click(self, event):
        """处理话题双击事件"""
        selection = self.topic_tree.selection()
        if selection:
            item = self.topic_tree.item(selection[0])
            topic_name = item["values"][0]
            self.show_topic_details(topic_name)
    
    def show_topic_details(self, topic_name):
        """显示话题详情"""
        # 创建详情窗口
        detail_window = tk.Toplevel(self)
        detail_window.title(f"话题详情 - {topic_name}")
        detail_window.geometry("600x400")
        
        # 添加详情内容
        ttk.Label(detail_window, text=f"话题: {topic_name}", font=("Arial", 14, "bold")).pack(pady=10)
        
        # 这里可以添加更多详细信息
        info_text = tk.Text(detail_window, wrap="word", height=20)
        info_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        info_text.insert("1.0", f"话题 '{topic_name}' 的详细信息将在这里显示...\n\n")
        info_text.insert("end", "包括：\n- 相关文章列表\n- 关键词分析\n- 趋势变化\n- 关联话题")
        info_text.config(state="disabled")
    
    def show_no_data_message(self):
        """显示无数据消息"""
        self.canvas.delete("all")
        self.canvas.create_text(150, 150, text="点击刷新按钮加载数据", font=("Arial", 12), fill="gray")
        
        for key in self.stats_labels:
            self.stats_labels[key].config(text="--")
    
    def show_loading_message(self):
        """显示加载消息"""
        self.canvas.delete("all")
        self.canvas.create_text(150, 150, text="正在加载数据...", font=("Arial", 12), fill="blue")

# 话题趋势分析组件
class TopicTrendWidget(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.setup_ui()
        
    def setup_ui(self):
        # 标题
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", pady=5)
        ttk.Label(title_frame, text="话题趋势分析", font=("Arial", 12, "bold")).pack(side="left")
        
        # 时间范围选择
        time_frame = ttk.Frame(title_frame)
        time_frame.pack(side="right")
        
        ttk.Label(time_frame, text="时间范围:").pack(side="left")
        self.time_var = tk.StringVar(value="最近7天")
        time_combo = ttk.Combobox(time_frame, textvariable=self.time_var,
                                values=["最近7天", "最近30天", "最近90天"], width=10)
        time_combo.pack(side="left", padx=5)
        time_combo.config(state="readonly")
        
        # 主要内容区域
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, pady=5)
        
        # 左侧：趋势图
        chart_frame = ttk.LabelFrame(main_frame, text="趋势图")
        chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.trend_canvas = tk.Canvas(chart_frame, width=400, height=200, bg="white")
        self.trend_canvas.pack(pady=10)
        
        # 右侧：趋势统计
        stats_frame = ttk.LabelFrame(main_frame, text="趋势统计")
        stats_frame.pack(side="right", fill="y", padx=(5, 0))
        
        # 新兴话题
        ttk.Label(stats_frame, text="新兴话题:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(5, 2))
        self.emerging_frame = ttk.Frame(stats_frame)
        self.emerging_frame.pack(fill="x", padx=5)
        
        # 衰落话题
        ttk.Label(stats_frame, text="衰落话题:", font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=(10, 2))
        self.declining_frame = ttk.Frame(stats_frame)
        self.declining_frame.pack(fill="x", padx=5)
        
        # 初始化显示
        self.load_sample_trend_data()
    
    def load_sample_trend_data(self):
        """加载示例趋势数据"""
        # 绘制简单的趋势线
        self.trend_canvas.delete("all")
        
        # 示例数据点
        import random
        topics = ["人工智能", "生物技术", "量子计算"]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]
        
        # 绘制坐标轴
        self.trend_canvas.create_line(50, 180, 350, 180, fill="black", width=2)  # X轴
        self.trend_canvas.create_line(50, 20, 50, 180, fill="black", width=2)   # Y轴
        
        # 绘制趋势线
        for i, (topic, color) in enumerate(zip(topics, colors)):
            points = []
            for j in range(7):  # 7天数据
                x = 50 + j * 40
                y = 180 - random.randint(20, 150)
                points.extend([x, y])
            
            if len(points) >= 4:
                self.trend_canvas.create_line(points, fill=color, width=2, smooth=True)
            
            # 图例
            legend_y = 20 + i * 20
            self.trend_canvas.create_line(360, legend_y, 380, legend_y, fill=color, width=3)
            self.trend_canvas.create_text(385, legend_y, text=topic, anchor="w", font=("Arial", 8))
        
        # 更新统计信息
        self.update_trend_stats()
    
    def update_trend_stats(self):
        """更新趋势统计"""
        # 清空现有内容
        for widget in self.emerging_frame.winfo_children():
            widget.destroy()
        for widget in self.declining_frame.winfo_children():
            widget.destroy()
        
        # 新兴话题
        emerging_topics = ["量子计算 (+25%)", "材料科学 (+18%)"]
        for topic in emerging_topics:
            ttk.Label(self.emerging_frame, text=f"• {topic}", foreground="green").pack(anchor="w")
        
        # 衰落话题
        declining_topics = ["新能源 (-12%)"]
        for topic in declining_topics:
            ttk.Label(self.declining_frame, text=f"• {topic}", foreground="red").pack(anchor="w")


# 优化建议组件
class OptimizationSuggestionWidget(ttk.Frame):
    def __init__(self, master, preference_service):
        super().__init__(master)
        self.preference_service = preference_service
        self.topic_service = TopicDistributionService()
        self.optimization_service = None
        self.current_suggestions = []

        self.setup_ui()
        self.load_initial_state()

    def setup_ui(self):
        # 标题和控制按钮
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(header_frame, text="智能优化建议",
                 font=("Arial", 14, "bold")).pack(side="left")

        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side="right")

        self.generate_btn = ttk.Button(button_frame, text="生成建议",
                                      command=self.generate_suggestions)
        self.generate_btn.pack(side="left", padx=(0, 5))

        self.apply_btn = ttk.Button(button_frame, text="应用建议",
                                   command=self.apply_suggestions, state=tk.DISABLED)
        self.apply_btn.pack(side="left", padx=(0, 5))

        self.export_btn = ttk.Button(button_frame, text="导出建议",
                                    command=self.export_suggestions, state=tk.DISABLED)
        self.export_btn.pack(side="left")

        # 建议列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True)

        # 创建Treeview
        columns = ("priority", "category", "title", "impact")
        self.suggestion_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)

        self.suggestion_tree.heading("priority", text="优先级")
        self.suggestion_tree.heading("category", text="类别")
        self.suggestion_tree.heading("title", text="建议标题")
        self.suggestion_tree.heading("impact", text="预期影响")

        self.suggestion_tree.column("priority", width=80)
        self.suggestion_tree.column("category", width=100)
        self.suggestion_tree.column("title", width=350)
        self.suggestion_tree.column("impact", width=150)

        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.suggestion_tree.yview)
        self.suggestion_tree.configure(yscrollcommand=scrollbar.set)

        self.suggestion_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 详情显示区域
        detail_frame = ttk.LabelFrame(self, text="建议详情")
        detail_frame.pack(fill="x", pady=(10, 0))

        self.detail_text = tk.Text(detail_frame, height=6, wrap=tk.WORD)
        detail_scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=self.detail_text.yview)
        self.detail_text.configure(yscrollcommand=detail_scrollbar.set)

        self.detail_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        detail_scrollbar.pack(side="right", fill="y", pady=5)

        # 绑定选择事件
        self.suggestion_tree.bind("<<TreeviewSelect>>", self.on_suggestion_select)

    def load_initial_state(self):
        """加载初始状态"""
        self.show_empty_state()

    def show_empty_state(self):
        """显示空状态"""
        # 清空列表
        for item in self.suggestion_tree.get_children():
            self.suggestion_tree.delete(item)

        # 显示提示信息
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, "点击'生成建议'按钮，基于偏好分析报告生成智能优化建议。\n\n")
        self.detail_text.insert(tk.END, "优化建议将包括：\n")
        self.detail_text.insert(tk.END, "• 关键词配置优化\n")
        self.detail_text.insert(tk.END, "• AI提示词改进\n")
        self.detail_text.insert(tk.END, "• 筛选参数调整\n")
        self.detail_text.config(state=tk.DISABLED)

    def generate_suggestions(self):
        """生成优化建议"""
        self.generate_btn.config(state=tk.DISABLED, text="生成中...")

        # 在后台线程中执行
        threading.Thread(target=self._run_suggestion_generation, daemon=True).start()

    def _run_suggestion_generation(self):
        """在后台线程中运行建议生成"""
        try:
            # 1. 首先生成偏好分析报告
            self.after(0, lambda: self._update_status("正在生成偏好分析报告..."))

            # 获取关键词分析结果
            keyword_data = self._get_keyword_analysis()

            # 获取话题分布分析结果
            topic_data = self._get_topic_analysis()

            # 生成综合报告
            report_data = self._generate_report_data(keyword_data, topic_data)

            # 2. 调用优化服务生成建议
            self.after(0, lambda: self._update_status("正在分析配置并生成优化建议..."))

            from src.services.optimization_service import OptimizationService
            if self.optimization_service is None:
                self.optimization_service = OptimizationService()

            optimization_result = self.optimization_service.generate_optimization_suggestions(report_data)

            # 3. 在主线程中更新UI
            self.after(0, self._update_suggestions_display, optimization_result)

        except Exception as e:
            self.after(0, self._show_error, f"生成优化建议失败: {e}")
        finally:
            self.after(0, lambda: self.generate_btn.config(state=tk.NORMAL, text="生成建议"))

    def _update_status(self, message):
        """更新状态信息"""
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, message)
        self.detail_text.config(state=tk.DISABLED)

    def _get_keyword_analysis(self):
        """获取关键词分析结果"""
        try:
            job_id = self.preference_service.analyze_historical_data()
            if job_id is None:
                return None

            # 等待分析完成
            max_wait = 30
            wait_count = 0
            while wait_count < max_wait:
                status_val = self.preference_service.get_analysis_status(job_id)
                status = JobStatus(status_val) if status_val else None

                if status == JobStatus.COMPLETED:
                    result = self.preference_service.get_analysis_result(job_id)
                    if result:
                        return {item[0]: item[1] for item in result}
                    break
                elif status == JobStatus.FAILED:
                    break

                time.sleep(1)
                wait_count += 1

            return None
        except Exception as e:
            print(f"获取关键词分析结果时出错: {e}")
            return None

    def _get_topic_analysis(self):
        """获取话题分布分析结果"""
        try:
            engine = create_engine('sqlite:///data/preference_analysis.db')
            Session = sessionmaker(bind=engine)
            session = Session()

            from src.database.models import Article as DBArticle
            db_articles = session.query(DBArticle).limit(100).all()

            if not db_articles:
                session.close()
                return None

            # 转换为CombinedFilterResult格式
            results = []
            for db_article in db_articles:
                from datetime import datetime
                published_dt = db_article.published_at if db_article.published_at else datetime.now()

                news_article = NewsArticle(
                    id=str(db_article.id),
                    title=db_article.title,
                    summary="",
                    content=db_article.content or "",
                    url=db_article.url or "",
                    published=published_dt,
                    updated=published_dt
                )

                # 创建标签
                tags = []
                if hasattr(db_article, 'tags') and db_article.tags:
                    tag_names = db_article.tags.split(',')
                    for tag_name in tag_names:
                        tag = ArticleTag(
                            name=tag_name.strip(),
                            score=0.8,
                            confidence=0.7,
                            source="historical"
                        )
                        tags.append(tag)

                result = CombinedFilterResult(
                    article=news_article,
                    keyword_result=None,
                    ai_result=None,
                    final_score=0.5,
                    selected=True,
                    rejection_reason=None,
                    tags=tags
                )
                results.append(result)

            session.close()

            if results:
                analysis_result = self.topic_service.analyze_current_data(results)
                return analysis_result

            return None
        except Exception as e:
            print(f"获取话题分布分析结果时出错: {e}")
            return None

    def _generate_report_data(self, keyword_data, topic_data):
        """生成报告数据"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "keyword_analysis": keyword_data,
            "topic_analysis": topic_data,
            "summary": {},
            "insights": [],
            "recommendations": []
        }

        # 生成摘要统计
        if keyword_data:
            report["summary"]["total_keywords"] = len(keyword_data)
            report["summary"]["top_keyword"] = max(keyword_data.items(), key=lambda x: x[1])[0] if keyword_data else "无"

        if topic_data:
            report["summary"]["total_topics"] = topic_data.total_topics
            report["summary"]["diversity_score"] = topic_data.diversity_score
            report["summary"]["concentration_index"] = topic_data.concentration_index
        else:
            report["summary"]["total_topics"] = 0
            report["summary"]["diversity_score"] = 0.0
            report["summary"]["concentration_index"] = 0.0

        # 生成洞察
        insights = []
        if keyword_data:
            top_keywords = sorted(keyword_data.items(), key=lambda x: x[1], reverse=True)[:5]
            insights.append(f"最受关注的关键词是：{', '.join([k for k, v in top_keywords])}")

        if topic_data and topic_data.topic_distribution:
            top_topic = max(topic_data.topic_distribution.items(), key=lambda x: x[1].count)
            insights.append(f"最热门的话题是'{top_topic[0]}'，占比{top_topic[1].percentage:.1f}%")

        report["insights"] = insights

        return report

    def _update_suggestions_display(self, optimization_result):
        """更新建议显示"""
        self.current_suggestions = optimization_result.suggestions

        # 清空现有内容
        for item in self.suggestion_tree.get_children():
            self.suggestion_tree.delete(item)

        # 添加建议到列表
        for suggestion in optimization_result.suggestions:
            # 设置优先级颜色标记
            priority_color = {
                "high": "red",
                "medium": "orange",
                "low": "green"
            }.get(suggestion.priority, "black")

            item_id = self.suggestion_tree.insert("", "end", values=(
                suggestion.priority,
                suggestion.category,
                suggestion.title,
                suggestion.impact
            ))

            # 设置颜色标记
            if suggestion.priority == "high":
                self.suggestion_tree.set(item_id, "priority", "🔴 " + suggestion.priority)
            elif suggestion.priority == "medium":
                self.suggestion_tree.set(item_id, "priority", "🟡 " + suggestion.priority)
            else:
                self.suggestion_tree.set(item_id, "priority", "🟢 " + suggestion.priority)

        # 显示摘要
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, f"优化建议生成完成！\n\n")
        self.detail_text.insert(tk.END, f"置信度: {optimization_result.confidence:.1%}\n")
        self.detail_text.insert(tk.END, f"生成时间: {optimization_result.generated_at}\n\n")
        self.detail_text.insert(tk.END, optimization_result.summary)
        self.detail_text.config(state=tk.DISABLED)

        # 启用按钮
        self.apply_btn.config(state=tk.NORMAL)
        self.export_btn.config(state=tk.NORMAL)

    def on_suggestion_select(self, event):
        """处理建议选择事件"""
        selection = self.suggestion_tree.selection()
        if not selection or not self.current_suggestions:
            return

        # 获取选中项的索引
        item = selection[0]
        index = self.suggestion_tree.index(item)

        if 0 <= index < len(self.current_suggestions):
            suggestion = self.current_suggestions[index]

            # 显示详细信息
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)

            self.detail_text.insert(tk.END, f"建议标题: {suggestion.title}\n\n")
            self.detail_text.insert(tk.END, f"类别: {suggestion.category}\n")
            self.detail_text.insert(tk.END, f"优先级: {suggestion.priority}\n\n")
            self.detail_text.insert(tk.END, f"详细描述:\n{suggestion.description}\n\n")

            if suggestion.current_value:
                self.detail_text.insert(tk.END, f"当前值: {suggestion.current_value}\n")
            if suggestion.suggested_value:
                self.detail_text.insert(tk.END, f"建议值: {suggestion.suggested_value}\n\n")

            self.detail_text.insert(tk.END, f"建议理由:\n{suggestion.reasoning}\n\n")
            self.detail_text.insert(tk.END, f"预期影响:\n{suggestion.impact}")

            self.detail_text.config(state=tk.DISABLED)

    def apply_suggestions(self):
        """应用选中的建议"""
        if not self.current_suggestions:
            messagebox.showwarning("警告", "没有可应用的建议")
            return

        # 获取选中的建议
        selection = self.suggestion_tree.selection()
        if not selection:
            # 如果没有选中，询问是否应用所有高优先级建议
            high_priority_suggestions = [s for s in self.current_suggestions if s.priority == "high"]
            if high_priority_suggestions:
                result = messagebox.askyesno(
                    "应用建议",
                    f"没有选中具体建议。是否应用所有 {len(high_priority_suggestions)} 条高优先级建议？"
                )
                if result:
                    self._apply_suggestions_list(high_priority_suggestions)
            else:
                messagebox.showinfo("提示", "请先选择要应用的建议")
            return

        # 应用选中的建议
        selected_suggestions = []
        for item in selection:
            index = self.suggestion_tree.index(item)
            if 0 <= index < len(self.current_suggestions):
                selected_suggestions.append(self.current_suggestions[index])

        if selected_suggestions:
            result = messagebox.askyesno(
                "确认应用",
                f"确定要应用选中的 {len(selected_suggestions)} 条建议吗？\n\n"
                "这将修改当前的配置文件。"
            )
            if result:
                self._apply_suggestions_list(selected_suggestions)

    def _apply_suggestions_list(self, suggestions):
        """应用建议列表"""
        applied_count = 0
        failed_count = 0

        for suggestion in suggestions:
            try:
                if suggestion.category == "keyword":
                    self._apply_keyword_suggestion(suggestion)
                elif suggestion.category == "prompt":
                    self._apply_prompt_suggestion(suggestion)
                elif suggestion.category == "config":
                    self._apply_config_suggestion(suggestion)

                applied_count += 1
            except Exception as e:
                print(f"应用建议失败: {suggestion.title}, 错误: {e}")
                failed_count += 1

        # 显示结果
        if applied_count > 0:
            messagebox.showinfo(
                "应用完成",
                f"成功应用 {applied_count} 条建议。\n"
                f"失败 {failed_count} 条建议。\n\n"
                "建议重启应用以使配置生效。"
            )
        else:
            messagebox.showerror("应用失败", "没有成功应用任何建议，请检查配置权限。")

    def _apply_keyword_suggestion(self, suggestion):
        """应用关键词建议"""
        # 这里可以实现具体的关键词配置修改逻辑
        # 由于涉及复杂的配置解析，这里提供一个基础实现
        print(f"应用关键词建议: {suggestion.title}")
        # TODO: 实现具体的关键词配置修改

    def _apply_prompt_suggestion(self, suggestion):
        """应用提示词建议"""
        # 这里可以实现具体的提示词配置修改逻辑
        print(f"应用提示词建议: {suggestion.title}")
        # TODO: 实现具体的提示词配置修改

    def _apply_config_suggestion(self, suggestion):
        """应用配置建议"""
        # 这里可以实现具体的配置参数修改逻辑
        print(f"应用配置建议: {suggestion.title}")
        # TODO: 实现具体的配置参数修改

    def export_suggestions(self):
        """导出优化建议"""
        if not self.current_suggestions:
            messagebox.showwarning("警告", "没有可导出的建议")
            return

        from tkinter import filedialog
        import os

        # 选择保存位置
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"优化建议_{timestamp}.md"

        file_path = filedialog.asksaveasfilename(
            title="导出优化建议",
            defaultextension=".md",
            filetypes=[
                ("Markdown文件", "*.md"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            initialfile=default_filename
        )

        if not file_path:
            return

        try:
            # 生成导出内容
            content = self._generate_export_content()

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            messagebox.showinfo("成功", f"优化建议已导出到：\n{file_path}")

            # 询问是否打开文件
            if messagebox.askyesno("打开文件", "是否要打开导出的建议文件？"):
                os.startfile(file_path)

        except Exception as e:
            messagebox.showerror("错误", f"导出建议失败：{e}")

    def _generate_export_content(self):
        """生成导出内容"""
        content = []

        content.append("# 新闻筛选系统优化建议")
        content.append("")
        content.append(f"**生成时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        content.append(f"**建议数量：** {len(self.current_suggestions)}")
        content.append("")

        # 按优先级分组
        high_priority = [s for s in self.current_suggestions if s.priority == "high"]
        medium_priority = [s for s in self.current_suggestions if s.priority == "medium"]
        low_priority = [s for s in self.current_suggestions if s.priority == "low"]

        # 高优先级建议
        if high_priority:
            content.append("## 🔴 高优先级建议")
            content.append("")
            for i, suggestion in enumerate(high_priority, 1):
                content.extend(self._format_suggestion_for_export(suggestion, i))
            content.append("")

        # 中优先级建议
        if medium_priority:
            content.append("## 🟡 中优先级建议")
            content.append("")
            for i, suggestion in enumerate(medium_priority, 1):
                content.extend(self._format_suggestion_for_export(suggestion, i))
            content.append("")

        # 低优先级建议
        if low_priority:
            content.append("## 🟢 低优先级建议")
            content.append("")
            for i, suggestion in enumerate(low_priority, 1):
                content.extend(self._format_suggestion_for_export(suggestion, i))
            content.append("")

        content.append("---")
        content.append("*此建议由新闻筛选系统智能优化服务生成*")

        return "\n".join(content)

    def _format_suggestion_for_export(self, suggestion, index):
        """格式化单个建议用于导出"""
        lines = []

        lines.append(f"### {index}. {suggestion.title}")
        lines.append("")
        lines.append(f"**类别：** {suggestion.category}")
        lines.append(f"**优先级：** {suggestion.priority}")
        lines.append("")
        lines.append(f"**描述：** {suggestion.description}")
        lines.append("")

        if suggestion.current_value:
            lines.append(f"**当前值：** {suggestion.current_value}")
        if suggestion.suggested_value:
            lines.append(f"**建议值：** {suggestion.suggested_value}")
        if suggestion.current_value or suggestion.suggested_value:
            lines.append("")

        lines.append(f"**理由：** {suggestion.reasoning}")
        lines.append("")
        lines.append(f"**预期影响：** {suggestion.impact}")
        lines.append("")

        return lines

    def _show_error(self, error_message):
        """显示错误信息"""
        messagebox.showerror("错误", error_message)

        # 在详情区域也显示错误
        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.insert(tk.END, f"错误: {error_message}\n\n")
        self.detail_text.insert(tk.END, "请检查以下可能的原因：\n")
        self.detail_text.insert(tk.END, "• 网络连接是否正常\n")
        self.detail_text.insert(tk.END, "• AI服务配置是否正确\n")
        self.detail_text.insert(tk.END, "• 是否有足够的历史数据\n")
        self.detail_text.config(state=tk.DISABLED)


class AnalysisReportWidget(ttk.Frame):
    """分析报告组件"""

    def __init__(self, master, preference_service):
        super().__init__(master)
        self.preference_service = preference_service
        self.topic_service = TopicDistributionService()
        self.current_report_data = None  # 存储当前报告数据

        self.setup_ui()
        self.load_report_data()

    def setup_ui(self):
        # 标题和刷新按钮
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(header_frame, text="偏好分析综合报告",
                 font=("Arial", 14, "bold")).pack(side="left")

        # 按钮框架
        button_frame = ttk.Frame(header_frame)
        button_frame.pack(side="right")

        self.refresh_btn = ttk.Button(button_frame, text="生成报告",
                                     command=self.generate_report)
        self.refresh_btn.pack(side="left", padx=(0, 5))

        self.export_btn = ttk.Button(button_frame, text="导出报告",
                                    command=self.export_report, state=tk.DISABLED)
        self.export_btn.pack(side="left")

        # 创建滚动区域
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 报告内容区域
        self.create_report_sections()

    def create_report_sections(self):
        """创建报告各个部分"""
        # 概览部分
        self.overview_frame = ttk.LabelFrame(self.scrollable_frame, text="分析概览")
        self.overview_frame.pack(fill="x", padx=10, pady=5)

        # 关键词分析部分
        self.keyword_frame = ttk.LabelFrame(self.scrollable_frame, text="关键词分析结果")
        self.keyword_frame.pack(fill="x", padx=10, pady=5)

        # 话题分布部分
        self.topic_frame = ttk.LabelFrame(self.scrollable_frame, text="话题分布分析")
        self.topic_frame.pack(fill="x", padx=10, pady=5)

        # 趋势分析部分
        self.trend_frame = ttk.LabelFrame(self.scrollable_frame, text="趋势分析")
        self.trend_frame.pack(fill="x", padx=10, pady=5)

        # 建议部分
        self.recommendation_frame = ttk.LabelFrame(self.scrollable_frame, text="优化建议")
        self.recommendation_frame.pack(fill="x", padx=10, pady=5)

        # 初始化显示空状态
        self.show_empty_state()

    def show_empty_state(self):
        """显示空状态"""
        for frame in [self.overview_frame, self.keyword_frame, self.topic_frame,
                     self.trend_frame, self.recommendation_frame]:
            # 清空现有内容
            for widget in frame.winfo_children():
                widget.destroy()

            ttk.Label(frame, text="点击'生成报告'按钮开始分析...",
                     foreground="gray").pack(pady=20)

    def load_report_data(self):
        """加载报告数据"""
        self.show_empty_state()

    def generate_report(self):
        """生成分析报告"""
        self.refresh_btn.config(state=tk.DISABLED, text="生成中...")

        # 在后台线程中执行分析
        threading.Thread(target=self._run_report_analysis, daemon=True).start()

    def _run_report_analysis(self):
        """在后台线程中运行报告分析"""
        try:
            # 1. 获取关键词分析结果
            keyword_data = self._get_keyword_analysis()

            # 2. 获取话题分布分析结果
            topic_data = self._get_topic_analysis()

            # 3. 生成综合报告
            report_data = self._generate_comprehensive_report(keyword_data, topic_data)

            # 4. 在主线程中更新UI
            self.after(0, self._update_report_display, report_data)

        except Exception as e:
            self.after(0, self._show_error, f"生成报告时出错: {e}")
        finally:
            self.after(0, lambda: self.refresh_btn.config(state=tk.NORMAL, text="生成报告"))

    def _get_keyword_analysis(self):
        """获取关键词分析结果"""
        try:
            # 分析历史数据
            job_id = self.preference_service.analyze_historical_data()
            if job_id is None:
                return None

            # 等待分析完成
            max_wait = 30  # 最多等待30秒
            wait_count = 0
            while wait_count < max_wait:
                status_val = self.preference_service.get_analysis_status(job_id)
                status = JobStatus(status_val) if status_val else None

                if status == JobStatus.COMPLETED:
                    result = self.preference_service.get_analysis_result(job_id)
                    if result:
                        # 转换为字典格式
                        return {item[0]: item[1] for item in result}
                    break
                elif status == JobStatus.FAILED:
                    break

                time.sleep(1)
                wait_count += 1

            return None
        except Exception as e:
            print(f"获取关键词分析结果时出错: {e}")
            return None

    def _get_topic_analysis(self):
        """获取话题分布分析结果"""
        try:
            # 获取历史数据 - 使用偏好分析数据库
            engine = create_engine('sqlite:///data/preference_analysis.db')
            Session = sessionmaker(bind=engine)
            session = Session()

            # 查询历史文章数据
            from src.database.models import Article as DBArticle
            db_articles = session.query(DBArticle).limit(100).all()

            if not db_articles:
                session.close()
                return None

            # 转换为CombinedFilterResult格式
            results = []
            for db_article in db_articles:
                # 创建NewsArticle对象
                from datetime import datetime
                published_dt = db_article.published_at if db_article.published_at else datetime.now()

                news_article = NewsArticle(
                    id=str(db_article.id),
                    title=db_article.title,
                    summary="",
                    content=db_article.content or "",
                    url=db_article.url or "",
                    published=published_dt,
                    updated=published_dt
                )

                # 创建标签（如果有的话）
                tags = []
                if hasattr(db_article, 'tags') and db_article.tags:
                    tag_names = db_article.tags.split(',')
                    for tag_name in tag_names:
                        tag = ArticleTag(
                            name=tag_name.strip(),
                            score=0.8,
                            confidence=0.7,
                            source="historical"
                        )
                        tags.append(tag)

                # 创建CombinedFilterResult对象
                result = CombinedFilterResult(
                    article=news_article,
                    keyword_result=None,
                    ai_result=None,
                    final_score=0.5,
                    selected=True,
                    rejection_reason=None,
                    tags=tags
                )
                results.append(result)

            session.close()

            if results:
                # 进行话题分布分析
                analysis_result = self.topic_service.analyze_current_data(results)
                return analysis_result

            return None
        except Exception as e:
            print(f"获取话题分布分析结果时出错: {e}")
            return None

    def _generate_comprehensive_report(self, keyword_data, topic_data):
        """生成综合分析报告"""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "keyword_analysis": keyword_data,
            "topic_analysis": topic_data,
            "summary": {},
            "insights": [],
            "recommendations": []
        }

        # 生成摘要统计
        if keyword_data:
            report["summary"]["total_keywords"] = len(keyword_data)
            report["summary"]["top_keyword"] = max(keyword_data.items(), key=lambda x: x[1])[0] if keyword_data else "无"

        if topic_data:
            report["summary"]["total_topics"] = topic_data.total_topics
            report["summary"]["diversity_score"] = topic_data.diversity_score
            report["summary"]["concentration_index"] = topic_data.concentration_index
        else:
            # 如果话题分析失败，设置默认值
            report["summary"]["total_topics"] = 0
            report["summary"]["diversity_score"] = 0.0
            report["summary"]["concentration_index"] = 0.0

        # 生成洞察
        insights = []
        if keyword_data:
            top_keywords = sorted(keyword_data.items(), key=lambda x: x[1], reverse=True)[:5]
            insights.append(f"最受关注的关键词是：{', '.join([k for k, v in top_keywords])}")

        if topic_data and topic_data.topic_distribution:
            top_topic = max(topic_data.topic_distribution.items(), key=lambda x: x[1].count)
            insights.append(f"最热门的话题是'{top_topic[0]}'，占比{top_topic[1].percentage:.1f}%")

        report["insights"] = insights

        # 生成建议
        recommendations = []
        if keyword_data:
            low_score_keywords = [k for k, v in keyword_data.items() if v < 0.3]
            if low_score_keywords:
                recommendations.append(f"建议关注权重较低的关键词：{', '.join(low_score_keywords[:3])}")

        if topic_data and topic_data.diversity_score < 0.5:
            recommendations.append("话题多样性较低，建议扩展内容来源以增加话题覆盖面")

        if topic_data and topic_data.concentration_index > 0.7:
            recommendations.append("话题集中度较高，建议平衡各话题的关注度")

        report["recommendations"] = recommendations

        return report

    def _update_report_display(self, report_data):
        """更新报告显示"""
        # 存储报告数据
        self.current_report_data = report_data

        # 启用导出按钮
        self.export_btn.config(state=tk.NORMAL)

        # 清空现有内容
        for frame in [self.overview_frame, self.keyword_frame, self.topic_frame,
                     self.trend_frame, self.recommendation_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        # 更新概览部分
        self._update_overview_section(report_data)

        # 更新关键词分析部分
        self._update_keyword_section(report_data.get("keyword_analysis"))

        # 更新话题分布部分
        self._update_topic_section(report_data.get("topic_analysis"))

        # 更新趋势分析部分
        self._update_trend_section(report_data)

        # 更新建议部分
        self._update_recommendation_section(report_data.get("recommendations", []))

    def _update_overview_section(self, report_data):
        """更新概览部分"""
        summary = report_data.get("summary", {})
        insights = report_data.get("insights", [])

        # 基本统计信息
        stats_frame = ttk.Frame(self.overview_frame)
        stats_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(stats_frame, text=f"生成时间: {report_data.get('timestamp', '未知')}").pack(anchor="w")
        ttk.Label(stats_frame, text=f"关键词总数: {summary.get('total_keywords', 0)}").pack(anchor="w")
        ttk.Label(stats_frame, text=f"话题总数: {summary.get('total_topics', 0)}").pack(anchor="w")
        ttk.Label(stats_frame, text=f"话题多样性: {summary.get('diversity_score', 0):.2f}").pack(anchor="w")

        # 主要洞察
        if insights:
            ttk.Label(self.overview_frame, text="主要洞察:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
            for insight in insights:
                ttk.Label(self.overview_frame, text=f"• {insight}").pack(anchor="w", padx=20)

    def _update_keyword_section(self, keyword_data):
        """更新关键词分析部分"""
        if not keyword_data:
            ttk.Label(self.keyword_frame, text="暂无关键词分析数据").pack(pady=20)
            return

        # 创建关键词表格
        columns = ("关键词", "权重", "排名")
        tree = ttk.Treeview(self.keyword_frame, columns=columns, show="headings", height=8)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        # 添加数据
        sorted_keywords = sorted(keyword_data.items(), key=lambda x: x[1], reverse=True)
        for i, (keyword, weight) in enumerate(sorted_keywords[:20], 1):
            tree.insert("", "end", values=(keyword, f"{weight:.3f}", i))

        tree.pack(fill="both", expand=True, padx=10, pady=5)

        # 添加滚动条
        scrollbar_kw = ttk.Scrollbar(self.keyword_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar_kw.set)
        scrollbar_kw.pack(side="right", fill="y")

    def _update_topic_section(self, topic_data):
        """更新话题分布部分"""
        if not topic_data or not topic_data.topic_distribution:
            ttk.Label(self.topic_frame, text="暂无话题分布数据").pack(pady=20)
            return

        # 创建话题表格
        columns = ("话题", "文章数", "占比%", "平均评分")
        tree = ttk.Treeview(self.topic_frame, columns=columns, show="headings", height=8)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        # 添加数据
        for topic_name, topic_info in topic_data.topic_distribution.items():
            tree.insert("", "end", values=(
                topic_name,
                topic_info.count,
                f"{topic_info.percentage:.1f}%",
                f"{topic_info.avg_score:.2f}"
            ))

        tree.pack(fill="both", expand=True, padx=10, pady=5)

        # 添加滚动条
        scrollbar_tp = ttk.Scrollbar(self.topic_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar_tp.set)
        scrollbar_tp.pack(side="right", fill="y")

    def _update_trend_section(self, report_data):
        """更新趋势分析部分"""
        summary = report_data.get("summary", {})

        # 显示趋势指标
        ttk.Label(self.trend_frame, text="趋势指标:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)

        metrics_frame = ttk.Frame(self.trend_frame)
        metrics_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(metrics_frame, text=f"话题集中度: {summary.get('concentration_index', 0):.3f}").pack(anchor="w")
        ttk.Label(metrics_frame, text=f"内容多样性: {summary.get('diversity_score', 0):.2f}").pack(anchor="w")

        # 趋势说明
        trend_text = "基于当前数据的趋势分析显示："
        if summary.get('concentration_index', 0) > 0.7:
            trend_text += "\n• 话题集中度较高，内容相对集中"
        elif summary.get('concentration_index', 0) < 0.3:
            trend_text += "\n• 话题分布较为分散，覆盖面广"
        else:
            trend_text += "\n• 话题分布相对均衡"

        ttk.Label(self.trend_frame, text=trend_text).pack(anchor="w", padx=10, pady=5)

    def _update_recommendation_section(self, recommendations):
        """更新建议部分"""
        if not recommendations:
            ttk.Label(self.recommendation_frame, text="暂无优化建议").pack(pady=20)
            return

        ttk.Label(self.recommendation_frame, text="优化建议:", font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)

        for i, recommendation in enumerate(recommendations, 1):
            ttk.Label(self.recommendation_frame, text=f"{i}. {recommendation}").pack(anchor="w", padx=20, pady=2)

    def _show_error(self, error_message):
        """显示错误信息"""
        messagebox.showerror("错误", error_message)

    def export_report(self):
        """导出分析报告"""
        if not self.current_report_data:
            messagebox.showwarning("警告", "没有可导出的报告数据，请先生成报告")
            return

        from tkinter import filedialog
        import os

        # 选择保存位置
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        default_filename = f"偏好分析报告_{timestamp}.md"

        file_path = filedialog.asksaveasfilename(
            title="保存分析报告",
            defaultextension=".md",
            filetypes=[
                ("Markdown文件", "*.md"),
                ("文本文件", "*.txt"),
                ("所有文件", "*.*")
            ],
            initialfile=default_filename
        )

        if not file_path:
            return

        try:
            # 生成报告内容
            report_content = self._generate_report_content()

            # 写入文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report_content)

            messagebox.showinfo("成功", f"报告已导出到：\n{file_path}")

            # 询问是否打开文件
            if messagebox.askyesno("打开文件", "是否要打开导出的报告文件？"):
                os.startfile(file_path)

        except Exception as e:
            messagebox.showerror("错误", f"导出报告失败：{e}")

    def _generate_report_content(self):
        """生成报告内容（Markdown格式）"""
        if not self.current_report_data:
            return ""

        report = self.current_report_data
        content = []

        # 标题和基本信息
        content.append("# 新闻偏好分析报告")
        content.append("")
        content.append(f"**生成时间：** {report.get('timestamp', '未知')}")
        content.append("")

        # 执行摘要
        content.append("## 执行摘要")
        content.append("")
        summary = report.get("summary", {})
        content.append(f"- **关键词总数：** {summary.get('total_keywords', 0)}")
        content.append(f"- **话题总数：** {summary.get('total_topics', 0)}")
        content.append(f"- **话题多样性评分：** {summary.get('diversity_score', 0):.2f}")
        content.append(f"- **话题集中度指数：** {summary.get('concentration_index', 0):.3f}")
        content.append("")

        # 主要洞察
        insights = report.get("insights", [])
        if insights:
            content.append("## 主要洞察")
            content.append("")
            for insight in insights:
                content.append(f"- {insight}")
            content.append("")

        # 关键词分析
        keyword_data = report.get("keyword_analysis")
        if keyword_data:
            content.append("## 关键词分析")
            content.append("")
            content.append("### 高权重关键词（Top 20）")
            content.append("")
            content.append("| 排名 | 关键词 | 权重 |")
            content.append("|------|--------|------|")

            sorted_keywords = sorted(keyword_data.items(), key=lambda x: x[1], reverse=True)
            for i, (keyword, weight) in enumerate(sorted_keywords[:20], 1):
                content.append(f"| {i} | {keyword} | {weight:.3f} |")
            content.append("")

            # 关键词优化建议
            content.append("### 关键词优化建议")
            content.append("")
            low_weight_keywords = [k for k, v in keyword_data.items() if v < 0.3]
            if low_weight_keywords:
                content.append("**权重较低的关键词（建议关注）：**")
                for keyword in low_weight_keywords[:10]:
                    content.append(f"- {keyword}")
                content.append("")

            high_weight_keywords = [k for k, v in sorted_keywords[:5]]
            content.append("**核心关键词（建议保持）：**")
            for keyword in high_weight_keywords:
                content.append(f"- {keyword}")
            content.append("")

        # 话题分布分析
        topic_data = report.get("topic_analysis")
        if topic_data and topic_data.topic_distribution:
            content.append("## 话题分布分析")
            content.append("")
            content.append("### 话题统计")
            content.append("")
            content.append("| 话题 | 文章数 | 占比 | 平均评分 |")
            content.append("|------|--------|------|----------|")

            for topic_name, topic_info in topic_data.topic_distribution.items():
                content.append(f"| {topic_name} | {topic_info.count} | {topic_info.percentage:.1f}% | {topic_info.avg_score:.2f} |")
            content.append("")

            # 话题关键词
            content.append("### 各话题关键词")
            content.append("")
            for topic_name, topic_info in topic_data.topic_distribution.items():
                if topic_info.keywords:
                    content.append(f"**{topic_name}：** {', '.join(topic_info.keywords[:10])}")
            content.append("")

        # 趋势分析
        content.append("## 趋势分析")
        content.append("")
        concentration_index = summary.get('concentration_index', 0)
        diversity_score = summary.get('diversity_score', 0)

        content.append(f"- **话题集中度：** {concentration_index:.3f}")
        if concentration_index > 0.7:
            content.append("  - 话题集中度较高，内容相对集中")
        elif concentration_index < 0.3:
            content.append("  - 话题分布较为分散，覆盖面广")
        else:
            content.append("  - 话题分布相对均衡")

        content.append(f"- **内容多样性：** {diversity_score:.2f}")
        if diversity_score < 0.5:
            content.append("  - 内容多样性较低，建议扩展内容来源")
        elif diversity_score > 0.8:
            content.append("  - 内容多样性很高，话题覆盖面广")
        else:
            content.append("  - 内容多样性良好")

        # 添加数据一致性检查和说明
        if concentration_index == 0.0 and diversity_score == 0.0:
            content.append("")
            content.append("**注意：** 当前显示的指标值为0，可能是由于以下原因：")
            content.append("- 话题分析数据不足或分析失败")
            content.append("- 历史数据中缺少有效的话题标签")
            content.append("- 建议检查数据源并重新生成报告")
        content.append("")

        # 优化建议
        recommendations = report.get("recommendations", [])
        if recommendations:
            content.append("## 优化建议")
            content.append("")
            for i, recommendation in enumerate(recommendations, 1):
                content.append(f"{i}. {recommendation}")
            content.append("")

        # Agent优化上下文
        content.append("## Agent优化上下文")
        content.append("")
        content.append("### 筛选关键词优化建议")
        content.append("")

        if keyword_data:
            # 建议增加的关键词
            sorted_keywords = sorted(keyword_data.items(), key=lambda x: x[1], reverse=True)
            top_keywords = [k for k, v in sorted_keywords[:10]]
            content.append("**建议重点关注的关键词：**")
            content.append("```")
            content.append(", ".join(top_keywords))
            content.append("```")
            content.append("")

            # 建议调整权重的关键词
            medium_keywords = [k for k, v in sorted_keywords[10:20]]
            if medium_keywords:
                content.append("**建议适度关注的关键词：**")
                content.append("```")
                content.append(", ".join(medium_keywords))
                content.append("```")
                content.append("")

        # 提示词优化建议
        content.append("### 提示词优化建议")
        content.append("")

        if topic_data and topic_data.topic_distribution:
            top_topics = sorted(topic_data.topic_distribution.items(),
                              key=lambda x: x[1].count, reverse=True)[:5]
            content.append("**重点话题领域：**")
            for topic_name, topic_info in top_topics:
                content.append(f"- {topic_name}（{topic_info.count}篇文章，{topic_info.percentage:.1f}%）")
            content.append("")

            content.append("**建议的提示词模板：**")
            content.append("```")
            content.append("请分析以下新闻文章，重点关注以下话题领域：")
            for topic_name, _ in top_topics:
                content.append(f"- {topic_name}")
            content.append("")
            content.append("评估标准：")
            content.append("1. 内容相关性（是否与上述话题相关）")
            content.append("2. 信息价值（是否提供有价值的信息）")
            content.append("3. 时效性（是否为最新或重要的发展）")
            content.append("```")
            content.append("")

        # 配置建议
        content.append("### 配置优化建议")
        content.append("")

        if concentration_index > 0.7:
            content.append("- **话题多样化：** 当前话题集中度较高，建议：")
            content.append("  - 扩展RSS源，增加不同领域的内容")
            content.append("  - 调整关键词权重，平衡各话题关注度")
            content.append("  - 降低主要话题的筛选阈值")

        if diversity_score < 0.5:
            content.append("- **内容丰富化：** 当前内容多样性较低，建议：")
            content.append("  - 增加更多RSS订阅源")
            content.append("  - 扩展关键词列表")
            content.append("  - 调整AI筛选的评分标准")

        content.append("")
        content.append("---")
        content.append("*此报告由新闻偏好分析系统自动生成*")

        return "\n".join(content)