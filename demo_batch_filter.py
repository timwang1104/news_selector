#!/usr/bin/env python3
"""
批量筛选功能演示脚本
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api.auth import InoreaderAuth
from src.services.batch_filter_service import BatchFilterConfig, BatchFilterManager, CLIBatchProgressCallback
from src.utils.result_formatter import ResultFormatter, ResultExporter


def demo_batch_filter_with_keywords():
    """演示使用关键词过滤的批量筛选"""
    print("🎯 演示：使用关键词过滤的批量筛选")
    print("=" * 60)
    
    # 检查认证状态
    auth = InoreaderAuth()
    if not auth.is_authenticated():
        print("❌ 未登录，请先运行 'python main.py login' 命令")
        return
    
    # 创建批量筛选管理器
    manager = BatchFilterManager(auth)
    
    # 创建配置 - 筛选包含AI相关关键词的订阅源
    config = BatchFilterConfig()
    config.max_subscriptions = 5  # 限制处理5个订阅源
    config.articles_per_subscription = 20  # 每个订阅源获取20篇文章
    config.filter_type = "keyword"  # 使用关键词筛选
    config.enable_parallel = True  # 并行处理
    config.subscription_keywords = ["AI", "tech", "Technology", "科技"]  # 筛选包含这些关键词的订阅源
    config.min_score_threshold = 0.7  # 最小分数阈值
    config.max_results_per_subscription = 3  # 每个订阅源最多选择3篇文章
    
    # 创建进度回调
    callback = CLIBatchProgressCallback(show_progress=True)
    
    try:
        # 执行批量筛选
        batch_result = manager.filter_subscriptions_batch(config, callback)
        
        print("\n" + "=" * 60)
        print("📊 筛选结果展示")
        print("=" * 60)
        
        # 显示摘要
        summary = ResultFormatter.format_batch_summary(batch_result)
        print(summary)
        
        # 显示顶级文章（按订阅源分组）
        if batch_result.total_articles_selected > 0:
            top_articles = ResultFormatter.format_top_articles(
                batch_result, 
                top_n=10,
                group_by_subscription=True
            )
            print(top_articles)
        
        # 导出结果
        timestamp = batch_result.processing_start_time.strftime("%Y%m%d_%H%M%S")
        
        # 导出JSON
        json_filename = f"batch_filter_demo_{timestamp}.json"
        json_content = ResultFormatter.export_to_json(batch_result, include_content=False)
        ResultExporter.save_to_file(json_content, json_filename)
        print(f"\n✅ 结果已导出到: {json_filename}")
        
        # 导出CSV
        csv_filename = f"batch_filter_demo_{timestamp}.csv"
        csv_content = ResultFormatter.export_to_csv(batch_result)
        ResultExporter.save_to_file(csv_content, csv_filename)
        print(f"✅ 结果已导出到: {csv_filename}")
        
        return batch_result
        
    except Exception as e:
        print(f"❌ 批量筛选失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_subscription_filtering():
    """演示订阅源过滤功能"""
    print("\n🔍 演示：订阅源过滤功能")
    print("=" * 60)
    
    auth = InoreaderAuth()
    if not auth.is_authenticated():
        print("❌ 未登录，跳过演示")
        return
    
    from src.services.subscription_service import SubscriptionService
    
    try:
        subscription_service = SubscriptionService(auth)
        all_subscriptions = subscription_service.get_all_subscriptions()
        
        print(f"📰 总订阅源数量: {len(all_subscriptions)}")
        
        # 按关键词过滤
        keywords = ["AI", "tech", "Technology", "科技", "Bloomberg", "BBC"]
        filtered_subscriptions = []
        
        for subscription in all_subscriptions:
            title_lower = subscription.title.lower()
            if any(keyword.lower() in title_lower for keyword in keywords):
                filtered_subscriptions.append(subscription)
        
        print(f"🎯 包含关键词的订阅源: {len(filtered_subscriptions)}")
        print("\n匹配的订阅源:")
        for i, sub in enumerate(filtered_subscriptions[:10], 1):
            print(f"{i:2d}. {sub.title}")
            if sub.categories:
                categories = ", ".join([cat.label for cat in sub.categories])
                print(f"     分类: {categories}")
        
        if len(filtered_subscriptions) > 10:
            print(f"     ... 还有 {len(filtered_subscriptions) - 10} 个订阅源")
        
    except Exception as e:
        print(f"❌ 订阅源过滤演示失败: {e}")


def show_usage_examples():
    """显示使用示例"""
    print("\n💡 批量筛选功能使用示例")
    print("=" * 60)
    
    examples = [
        {
            "title": "基本批量筛选",
            "description": "筛选所有订阅源，使用关键词筛选",
            "code": """
from src.services.batch_filter_service import BatchFilterConfig, batch_filter_manager

config = BatchFilterConfig()
config.filter_type = "keyword"
config.max_subscriptions = 10
result = batch_filter_manager.filter_subscriptions_batch(config)
"""
        },
        {
            "title": "按关键词筛选订阅源",
            "description": "只处理标题包含特定关键词的订阅源",
            "code": """
config = BatchFilterConfig()
config.subscription_keywords = ["AI", "tech", "科技"]
config.filter_type = "chain"  # 使用完整筛选链
result = batch_filter_manager.filter_subscriptions_batch(config)
"""
        },
        {
            "title": "高质量文章筛选",
            "description": "使用AI筛选获取高质量文章",
            "code": """
config = BatchFilterConfig()
config.filter_type = "ai"
config.min_score_threshold = 0.8
config.max_results_per_subscription = 5
result = batch_filter_manager.filter_subscriptions_batch(config)
"""
        },
        {
            "title": "并行处理大量订阅源",
            "description": "启用并行处理提高效率",
            "code": """
config = BatchFilterConfig()
config.enable_parallel = True
config.max_workers = 5
config.max_subscriptions = 20
result = batch_filter_manager.filter_subscriptions_batch(config)
"""
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['title']}")
        print(f"   {example['description']}")
        print(f"   代码示例:{example['code']}")


if __name__ == "__main__":
    print("🚀 批量筛选功能演示")
    print("=" * 60)
    
    # 演示订阅源过滤
    demo_subscription_filtering()
    
    # 演示批量筛选
    result = demo_batch_filter_with_keywords()
    
    # 显示使用示例
    show_usage_examples()
    
    if result:
        print(f"\n🎉 演示完成！共筛选出 {result.total_articles_selected} 篇文章")
    else:
        print("\n⚠️  演示未完成，请检查错误信息")
