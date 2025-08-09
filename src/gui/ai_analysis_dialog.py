"""
AI分析详情对话框
"""
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional

from ..filters.base import AIEvaluation, CombinedFilterResult


class AIAnalysisDialog:
    """AI分析详情对话框"""
    
    def __init__(self, parent, combined_result: CombinedFilterResult):
        self.parent = parent
        self.combined_result = combined_result
        self.dialog = None
        
        # 创建对话框
        self.create_dialog()
    
    def create_dialog(self):
        """创建对话框"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("AI智能分析详情")
        self.dialog.geometry("800x700")
        self.dialog.resizable(True, True)
        
        # 设置为模态对话框
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.center_dialog()
        
        # 创建界面
        self.create_widgets()
    
    def center_dialog(self):
        """居中显示对话框"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 文章标题
        article = self.combined_result.article
        title_label = ttk.Label(main_frame, text=article.title, 
                               font=("Arial", 14, "bold"), wraplength=750)
        title_label.pack(pady=(0, 10), anchor=tk.W)
        
        # 文章信息
        info_text = f"来源: {getattr(article, 'feed_title', '未知')} | "
        if hasattr(article, 'published') and article.published:
            info_text += f"发布时间: {article.published.strftime('%Y-%m-%d %H:%M')}"
        elif hasattr(article, 'published_date') and article.published_date:
            info_text += f"发布时间: {article.published_date.strftime('%Y-%m-%d %H:%M')}"
        
        info_label = ttk.Label(main_frame, text=info_text, foreground="gray")
        info_label.pack(pady=(0, 15), anchor=tk.W)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # AI评估标签页
        self.create_ai_evaluation_tab(notebook)
        
        # 关键信息标签页
        self.create_key_insights_tab(notebook)
        
        # 详细分析标签页
        self.create_detailed_analysis_tab(notebook)
        
        # 实施建议标签页
        self.create_suggestions_tab(notebook)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="关闭", command=self.dialog.destroy).pack(side=tk.RIGHT)
        
        # 如果有原文链接，添加打开原文按钮
        if hasattr(article, 'url') and article.url:
            ttk.Button(button_frame, text="打开原文", 
                      command=lambda: self.open_article_url(article.url)).pack(side=tk.RIGHT, padx=(0, 10))
    
    def create_ai_evaluation_tab(self, notebook):
        """创建AI评估标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="AI评估")
        
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
        
        # 获取AI评估结果
        ai_result = self.combined_result.ai_result
        if not ai_result or not ai_result.evaluation:
            ttk.Label(scrollable_frame, text="没有AI评估信息", 
                     font=("Arial", 12)).pack(pady=20)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            return
        
        evaluation = ai_result.evaluation
        
        # 总体评分
        score_frame = ttk.LabelFrame(scrollable_frame, text="总体评分", padding="10")
        score_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 分数显示
        scores_info = [
            ("政策相关性", evaluation.relevance_score, 10),
            ("创新影响", evaluation.innovation_impact, 10),
            ("实用性", evaluation.practicality, 10),
            ("总分", evaluation.total_score, 30)
        ]
        
        for i, (label, score, max_score) in enumerate(scores_info):
            row_frame = ttk.Frame(score_frame)
            row_frame.pack(fill=tk.X, pady=2)
            
            ttk.Label(row_frame, text=f"{label}:", width=12).pack(side=tk.LEFT)
            
            # 进度条显示分数
            progress = ttk.Progressbar(row_frame, length=200, maximum=max_score, value=score)
            progress.pack(side=tk.LEFT, padx=(0, 10))
            
            ttk.Label(row_frame, text=f"{score}/{max_score}").pack(side=tk.LEFT)
        
        # 置信度
        confidence_frame = ttk.Frame(score_frame)
        confidence_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Label(confidence_frame, text="置信度:", width=12).pack(side=tk.LEFT)
        confidence_progress = ttk.Progressbar(confidence_frame, length=200, maximum=1.0, 
                                            value=evaluation.confidence)
        confidence_progress.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(confidence_frame, text=f"{evaluation.confidence:.2%}").pack(side=tk.LEFT)
        
        # AI摘要
        if evaluation.summary:
            summary_frame = ttk.LabelFrame(scrollable_frame, text="AI摘要", padding="10")
            summary_frame.pack(fill=tk.X, pady=(0, 10))
            
            summary_text = tk.Text(summary_frame, height=4, wrap=tk.WORD, 
                                  font=("Arial", 10), state="disabled")
            summary_text.pack(fill=tk.X)
            summary_text.config(state="normal")
            summary_text.insert("1.0", evaluation.summary)
            summary_text.config(state="disabled")
        
        # 推荐理由
        if evaluation.recommendation_reason:
            reason_frame = ttk.LabelFrame(scrollable_frame, text="推荐理由", padding="10")
            reason_frame.pack(fill=tk.X, pady=(0, 10))
            
            reason_text = tk.Text(reason_frame, height=3, wrap=tk.WORD, 
                                 font=("Arial", 10), state="disabled")
            reason_text.pack(fill=tk.X)
            reason_text.config(state="normal")
            reason_text.insert("1.0", evaluation.recommendation_reason)
            reason_text.config(state="disabled")
        
        # 评估理由
        if evaluation.reasoning:
            reasoning_frame = ttk.LabelFrame(scrollable_frame, text="详细评估理由", padding="10")
            reasoning_frame.pack(fill=tk.X, pady=(0, 10))
            
            reasoning_text = scrolledtext.ScrolledText(reasoning_frame, height=6, wrap=tk.WORD, 
                                                     font=("Arial", 10), state="disabled")
            reasoning_text.pack(fill=tk.BOTH, expand=True)
            reasoning_text.config(state="normal")
            reasoning_text.insert("1.0", evaluation.reasoning)
            reasoning_text.config(state="disabled")
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def create_key_insights_tab(self, notebook):
        """创建关键信息标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="关键信息")
        
        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ai_result = self.combined_result.ai_result
        if not ai_result or not ai_result.evaluation:
            ttk.Label(main_frame, text="没有关键信息", font=("Arial", 12)).pack(pady=20)
            return
        
        evaluation = ai_result.evaluation
        
        # 关键洞察
        if evaluation.key_insights:
            insights_frame = ttk.LabelFrame(main_frame, text="关键洞察", padding="10")
            insights_frame.pack(fill=tk.X, pady=(0, 10))
            
            for i, insight in enumerate(evaluation.key_insights, 1):
                insight_text = f"{i}. {insight}"
                ttk.Label(insights_frame, text=insight_text, wraplength=700, 
                         justify=tk.LEFT).pack(anchor=tk.W, pady=2)
        
        # 推荐亮点
        if evaluation.highlights:
            highlights_frame = ttk.LabelFrame(main_frame, text="推荐亮点", padding="10")
            highlights_frame.pack(fill=tk.X, pady=(0, 10))
            
            for i, highlight in enumerate(evaluation.highlights, 1):
                highlight_text = f"★ {highlight}"
                ttk.Label(highlights_frame, text=highlight_text, wraplength=700, 
                         justify=tk.LEFT, foreground="blue").pack(anchor=tk.W, pady=2)
        
        # 相关标签
        if evaluation.tags:
            tags_frame = ttk.LabelFrame(main_frame, text="相关标签", padding="10")
            tags_frame.pack(fill=tk.X, pady=(0, 10))
            
            tags_text = " | ".join([f"#{tag}" for tag in evaluation.tags])
            ttk.Label(tags_frame, text=tags_text, wraplength=700, 
                     foreground="green").pack(anchor=tk.W)
        
        # 风险评估
        if evaluation.risk_assessment:
            risk_frame = ttk.LabelFrame(main_frame, text="风险评估", padding="10")
            risk_frame.pack(fill=tk.X, pady=(0, 10))
            
            risk_text = tk.Text(risk_frame, height=4, wrap=tk.WORD, 
                               font=("Arial", 10), state="disabled")
            risk_text.pack(fill=tk.X)
            risk_text.config(state="normal")
            risk_text.insert("1.0", evaluation.risk_assessment)
            risk_text.config(state="disabled")
    
    def create_detailed_analysis_tab(self, notebook):
        """创建详细分析标签页"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="详细分析")
        
        main_frame = ttk.Frame(frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        ai_result = self.combined_result.ai_result
        if not ai_result or not ai_result.evaluation or not ai_result.evaluation.detailed_analysis:
            ttk.Label(main_frame, text="没有详细分析信息", font=("Arial", 12)).pack(pady=20)
            return
        
        evaluation = ai_result.evaluation
        
        for dimension, analysis in evaluation.detailed_analysis.items():
            if analysis:
                analysis_frame = ttk.LabelFrame(main_frame, text=dimension, padding="10")
                analysis_frame.pack(fill=tk.X, pady=(0, 10))
                
                analysis_text = scrolledtext.ScrolledText(analysis_frame, height=5, wrap=tk.WORD, 
                                                        font=("Arial", 10), state="disabled")
                analysis_text.pack(fill=tk.BOTH, expand=True)
                analysis_text.config(state="normal")
                analysis_text.insert("1.0", analysis)
                analysis_text.config(state="disabled")
    
    
    def open_article_url(self, url):
        """打开文章原文链接"""
        import webbrowser
        webbrowser.open(url)
    
    def show(self):
        """显示对话框"""
        self.dialog.wait_window()
