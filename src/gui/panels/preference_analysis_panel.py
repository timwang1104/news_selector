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



    def create_suggestion_widgets(self, parent):
        # 优化建议组件
        suggestion_widget = OptimizationSuggestionWidget(parent)
        suggestion_widget.pack(fill="both", expand=True, pady=5, padx=5)

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
    def __init__(self, master):
        super().__init__(master)
        
        self.suggestion_tree = ttk.Treeview(self, columns=("priority", "category", "suggestion", "impact"), 
                                          show="headings", height=10)
        
        self.suggestion_tree.heading("priority", text="优先级")
        self.suggestion_tree.heading("category", text="类别")
        self.suggestion_tree.heading("suggestion", text="建议内容")
        self.suggestion_tree.heading("impact", text="预期影响")
        
        self.suggestion_tree.column("priority", width=80)
        self.suggestion_tree.column("category", width=100)
        self.suggestion_tree.column("suggestion", width=300)
        self.suggestion_tree.column("impact", width=100)
        
        self.suggestion_tree.pack(fill="both", expand=True, pady=5)
        
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.suggestion_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.suggestion_tree.config(yscrollcommand=scrollbar.set)

        self.load_suggestions()

    def load_suggestions(self):
        suggestions = [
            ("高", "关键词", "增加 '金融科技' 关键词", "+5% 覆盖率"),
            ("中", "话题", "合并 'AI' 和 '人工智能'", "-2% 重复率"),
            ("低", "筛选", "调整 '区块链' 权重至0.8", "+1% 准确率"),
        ]
        for s in suggestions:
            self.suggestion_tree.insert("", "end", values=s)