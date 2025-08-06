import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from src.services.preference_analysis_service import PreferenceAnalysisService
from src.gui.components.keyword_cloud_widget import KeywordCloudWidget
from src.database.models import JobStatus

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
        
        # 学习进度标签页
        self.progress_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.progress_frame, text="学习进度")
        self.create_progress_widgets(self.progress_frame)
        
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

    def create_progress_widgets(self, parent):
        # 学习进度面板
        progress_panel = LearningProgressPanel(parent)
        progress_panel.pack(fill="both", expand=True, pady=5, padx=5)

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
        ttk.Label(self, text="话题分布分析 (占位符)").pack(pady=20)

    def update_pie_chart(self, topic_data=None):
        pass

# 话题趋势分析组件
class TopicTrendWidget(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        ttk.Label(self, text="话题趋势变化 (占位符)").pack(pady=20)

    def update_trend_chart(self, trend_data=None):
        pass

# 进度条组件
class ProgressBarWidget(ttk.Frame):
    def __init__(self, master, title, current, total, percentage):
        super().__init__(master)
        
        title_label = ttk.Label(self, text=title, font=("Arial", 10, "bold"))
        title_label.pack(anchor="w", pady=(5, 2))
        
        self.progress_var = tk.DoubleVar(value=percentage)
        progress_bar = ttk.Progressbar(self, variable=self.progress_var, 
                                     maximum=100, length=300)
        progress_bar.pack(fill="x", pady=2)
        
        info_label = ttk.Label(self, text=f"{current}/{total} ({percentage:.1f}%)")
        info_label.pack(anchor="w", pady=2)

# 学习进度面板
class LearningProgressPanel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        
        self.data_progress = ProgressBarWidget(
            self, "数据收集进度", 1234, 1500, 82.3
        )
        self.data_progress.pack(fill="x", pady=5)
        
        self.model_progress = ProgressBarWidget(
            self, "模型训练进度", 14, 20, 70.0
        )
        self.model_progress.pack(fill="x", pady=5)
        
        self.keyword_progress = ProgressBarWidget(
            self, "关键词优化", 450, 500, 90.0
        )
        self.keyword_progress.pack(fill="x", pady=5)
        
        time_frame = ttk.Frame(self)
        time_frame.pack(fill="x", pady=10)
        
        ttk.Label(time_frame, text="最后更新: 2024-01-15 14:30:25").pack(side="left")
        ttk.Label(time_frame, text="下次更新: 2024-01-15 18:00:00").pack(side="right")
        
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=10)
        
        ttk.Button(button_frame, text="立即更新", command=self.update_now).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="查看详情", command=self.show_details).pack(side="left", padx=(0, 10))
        ttk.Button(button_frame, text="导出报告", command=self.export_report).pack(side="left")

    def update_now(self):
        print("立即更新")

    def show_details(self):
        print("查看详情")

    def export_report(self):
        print("导出报告")

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