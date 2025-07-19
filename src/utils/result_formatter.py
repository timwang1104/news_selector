"""
筛选结果格式化工具
"""
import json
import csv
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import StringIO

from ..filters.base import BatchFilterResult, CombinedFilterResult, SubscriptionFilterResult
from ..services.batch_filter_service import BatchFilterConfig


class ResultFormatter:
    """筛选结果格式化器"""
    
    @staticmethod
    def format_batch_summary(batch_result: BatchFilterResult) -> str:
        """格式化批量筛选摘要"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 批量筛选结果摘要")
        lines.append("=" * 60)
        
        # 基本统计
        lines.append(f"订阅源总数: {batch_result.total_subscriptions}")
        lines.append(f"成功处理: {batch_result.processed_subscriptions}")
        lines.append(f"成功率: {batch_result.success_rate:.1%}")
        lines.append(f"获取文章: {batch_result.total_articles_fetched} 篇")
        lines.append(f"选中文章: {batch_result.total_articles_selected} 篇")
        
        if batch_result.total_articles_fetched > 0:
            selection_rate = batch_result.total_articles_selected / batch_result.total_articles_fetched
            lines.append(f"筛选率: {selection_rate:.1%}")
        
        # 时间统计
        lines.append(f"总耗时: {batch_result.total_processing_time:.2f} 秒")
        lines.append(f"获取耗时: {batch_result.total_fetch_time:.2f} 秒")
        lines.append(f"筛选耗时: {batch_result.total_filter_time:.2f} 秒")
        
        # 错误信息
        if batch_result.errors:
            lines.append(f"错误数量: {len(batch_result.errors)}")
        
        if batch_result.warnings:
            lines.append(f"警告数量: {len(batch_result.warnings)}")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_subscription_results(batch_result: BatchFilterResult, 
                                  show_details: bool = True) -> str:
        """格式化订阅源结果"""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("📰 订阅源处理结果")
        lines.append("=" * 60)
        
        for i, sub_result in enumerate(batch_result.subscription_results, 1):
            lines.append(f"\n{i}. {sub_result.subscription_title}")
            lines.append(f"   获取: {sub_result.articles_fetched} 篇")
            lines.append(f"   选中: {sub_result.selected_count} 篇")
            lines.append(f"   耗时: {sub_result.total_processing_time:.2f}s")
            
            if show_details and sub_result.filter_result.selected_articles:
                lines.append("   选中文章:")
                for j, article in enumerate(sub_result.filter_result.selected_articles[:3], 1):
                    score_info = f"(分数: {article.final_score:.2f})"
                    lines.append(f"     {j}. {article.article.title[:50]}... {score_info}")
                
                if len(sub_result.filter_result.selected_articles) > 3:
                    remaining = len(sub_result.filter_result.selected_articles) - 3
                    lines.append(f"     ... 还有 {remaining} 篇文章")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_top_articles(batch_result: BatchFilterResult, 
                          top_n: int = 10,
                          group_by_subscription: bool = False) -> str:
        """格式化顶级文章列表"""
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append(f"🏆 精选文章 (Top {top_n})")
        lines.append("=" * 60)
        
        all_articles = batch_result.all_selected_articles
        
        if not all_articles:
            lines.append("暂无选中文章")
            return "\n".join(lines)
        
        # 按分数排序
        sorted_articles = sorted(all_articles, key=lambda x: x.final_score, reverse=True)
        top_articles = sorted_articles[:top_n]
        
        if group_by_subscription:
            # 按订阅源分组
            subscription_groups = {}
            for article in top_articles:
                feed_title = article.article.feed_title or "未知订阅源"
                if feed_title not in subscription_groups:
                    subscription_groups[feed_title] = []
                subscription_groups[feed_title].append(article)
            
            for feed_title, articles in subscription_groups.items():
                lines.append(f"\n📰 {feed_title}")
                lines.append("-" * 40)
                for i, article in enumerate(articles, 1):
                    lines.append(ResultFormatter._format_article_line(article, i))
        else:
            # 统一列表
            for i, article in enumerate(top_articles, 1):
                lines.append(ResultFormatter._format_article_line(article, i))
        
        return "\n".join(lines)
    
    @staticmethod
    def _format_article_line(article: CombinedFilterResult, index: int) -> str:
        """格式化单篇文章行"""
        title = article.article.title[:60] + "..." if len(article.article.title) > 60 else article.article.title
        score = article.final_score
        published = article.article.published.strftime("%m-%d %H:%M")
        feed = article.article.feed_title[:20] + "..." if article.article.feed_title and len(article.article.feed_title) > 20 else (article.article.feed_title or "")
        
        return f"{index:2d}. [{score:.2f}] {title} | {feed} | {published}"
    
    @staticmethod
    def export_to_json(batch_result: BatchFilterResult, 
                      include_content: bool = False) -> str:
        """导出为JSON格式"""
        data = {
            "export_time": datetime.now().isoformat(),
            "summary": {
                "total_subscriptions": batch_result.total_subscriptions,
                "processed_subscriptions": batch_result.processed_subscriptions,
                "success_rate": batch_result.success_rate,
                "total_articles_fetched": batch_result.total_articles_fetched,
                "total_articles_selected": batch_result.total_articles_selected,
                "total_processing_time": batch_result.total_processing_time
            },
            "subscription_results": []
        }
        
        for sub_result in batch_result.subscription_results:
            sub_data = {
                "subscription_id": sub_result.subscription_id,
                "subscription_title": sub_result.subscription_title,
                "articles_fetched": sub_result.articles_fetched,
                "articles_selected": sub_result.selected_count,
                "processing_time": sub_result.total_processing_time,
                "selected_articles": []
            }
            
            for article in sub_result.filter_result.selected_articles:
                article_data = {
                    "id": article.article.id,
                    "title": article.article.title,
                    "url": article.article.url,
                    "published": article.article.published.isoformat(),
                    "final_score": article.final_score
                }
                
                if include_content:
                    article_data.update({
                        "summary": article.article.summary,
                        "content": article.article.content[:500] + "..." if len(article.article.content) > 500 else article.article.content
                    })
                
                if article.keyword_result:
                    article_data["keyword_score"] = article.keyword_result.relevance_score
                
                if article.ai_result:
                    article_data["ai_score"] = article.ai_result.evaluation.total_score
                    article_data["ai_reasoning"] = article.ai_result.evaluation.reasoning
                
                sub_data["selected_articles"].append(article_data)
            
            data["subscription_results"].append(sub_data)
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def export_to_csv(batch_result: BatchFilterResult) -> str:
        """导出为CSV格式"""
        output = StringIO()
        writer = csv.writer(output)
        
        # 写入标题行
        headers = [
            "订阅源", "文章标题", "URL", "发布时间", "最终分数",
            "关键词分数", "AI分数", "AI评估理由"
        ]
        writer.writerow(headers)
        
        # 写入数据行
        for sub_result in batch_result.subscription_results:
            for article in sub_result.filter_result.selected_articles:
                row = [
                    sub_result.subscription_title,
                    article.article.title,
                    article.article.url,
                    article.article.published.strftime("%Y-%m-%d %H:%M:%S"),
                    f"{article.final_score:.2f}",
                    f"{article.keyword_result.relevance_score:.2f}" if article.keyword_result else "",
                    f"{article.ai_result.evaluation.total_score}" if article.ai_result else "",
                    article.ai_result.evaluation.reasoning if article.ai_result else ""
                ]
                writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def format_errors_and_warnings(batch_result: BatchFilterResult) -> str:
        """格式化错误和警告信息"""
        lines = []
        
        if batch_result.errors:
            lines.append("\n" + "=" * 60)
            lines.append("❌ 错误信息")
            lines.append("=" * 60)
            for i, error in enumerate(batch_result.errors, 1):
                lines.append(f"{i}. {error}")
        
        if batch_result.warnings:
            lines.append("\n" + "=" * 60)
            lines.append("⚠️  警告信息")
            lines.append("=" * 60)
            for i, warning in enumerate(batch_result.warnings, 1):
                lines.append(f"{i}. {warning}")
        
        return "\n".join(lines) if lines else ""


class ResultExporter:
    """结果导出器"""
    
    @staticmethod
    def save_to_file(content: str, filename: str, encoding: str = "utf-8"):
        """保存内容到文件"""
        with open(filename, 'w', encoding=encoding) as f:
            f.write(content)
    
    @staticmethod
    def generate_filename(prefix: str, extension: str) -> str:
        """生成带时间戳的文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
