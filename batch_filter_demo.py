#!/usr/bin/env python3
"""
批量筛选功能演示脚本
这个脚本展示了如何使用批量筛选功能来自动处理多个订阅源
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """主演示函数"""
    print("🚀 批量筛选功能演示")
    print("=" * 60)
    
    try:
        # 导入必要的模块
        from src.api.auth import InoreaderAuth
        from src.services.batch_filter_service import (
            BatchFilterConfig, 
            BatchFilterManager, 
            CLIBatchProgressCallback
        )
        from src.utils.result_formatter import ResultFormatter, ResultExporter
        
        print("✅ 模块导入成功")
        
        # 检查认证状态
        auth = InoreaderAuth()
        if not auth.is_authenticated():
            print("❌ 未登录Inoreader账户")
            print("请先运行: python main.py login")
            return
        
        print("✅ 认证状态正常")
        
        # 创建批量筛选管理器
        manager = BatchFilterManager(auth)
        print("✅ 批量筛选管理器创建成功")
        
        # 演示场景1：快速科技新闻筛选
        print("\n" + "=" * 60)
        print("📰 演示场景1：快速科技新闻筛选")
        print("=" * 60)
        
        config1 = BatchFilterConfig()
        config1.subscription_keywords = ["tech", "Technology", "AI", "科技"]
        config1.max_subscriptions = 3
        config1.articles_per_subscription = 10
        config1.filter_type = "keyword"
        config1.enable_parallel = False  # 顺序处理便于观察
        config1.min_score_threshold = 0.6
        
        callback = CLIBatchProgressCallback(show_progress=True)
        
        print("配置信息:")
        print(f"  - 订阅源关键词: {config1.subscription_keywords}")
        print(f"  - 最大订阅源数: {config1.max_subscriptions}")
        print(f"  - 每源文章数: {config1.articles_per_subscription}")
        print(f"  - 筛选类型: {config1.filter_type}")
        print(f"  - 最小分数: {config1.min_score_threshold}")
        
        result1 = manager.filter_subscriptions_batch(config1, callback)
        
        # 显示结果摘要
        summary1 = ResultFormatter.format_batch_summary(result1)
        print("\n📊 结果摘要:")
        print(summary1)
        
        # 显示顶级文章
        if result1.total_articles_selected > 0:
            top_articles1 = ResultFormatter.format_top_articles(
                result1, 
                top_n=5,
                group_by_subscription=True
            )
            print(top_articles1)
        
        # 导出结果
        timestamp = result1.processing_start_time.strftime("%Y%m%d_%H%M%S")
        json_filename = f"demo_tech_news_{timestamp}.json"
        csv_filename = f"demo_tech_news_{timestamp}.csv"
        
        json_content = ResultFormatter.export_to_json(result1, include_content=False)
        ResultExporter.save_to_file(json_content, json_filename)
        
        csv_content = ResultFormatter.export_to_csv(result1)
        ResultExporter.save_to_file(csv_content, csv_filename)
        
        print(f"\n📤 结果已导出:")
        print(f"  - JSON: {json_filename}")
        print(f"  - CSV: {csv_filename}")
        
        # 演示场景2：高质量文章筛选（如果有AI配置）
        print("\n" + "=" * 60)
        print("📊 演示场景2：订阅源统计分析")
        print("=" * 60)
        
        # 显示订阅源处理详情
        sub_results = ResultFormatter.format_subscription_results(result1, show_details=True)
        print(sub_results)
        
        # 显示性能统计
        print(f"\n⏱️  性能统计:")
        print(f"  - 成功率: {result1.success_rate:.1%}")
        print(f"  - 平均获取时间: {result1.total_fetch_time/result1.processed_subscriptions:.2f}秒/源")
        print(f"  - 平均筛选时间: {result1.total_filter_time/result1.processed_subscriptions:.2f}秒/源")
        
        if result1.total_articles_fetched > 0:
            selection_rate = result1.total_articles_selected / result1.total_articles_fetched
            print(f"  - 文章筛选率: {selection_rate:.1%}")
        
        # 显示使用建议
        print("\n" + "=" * 60)
        print("💡 使用建议")
        print("=" * 60)
        
        suggestions = []
        
        if result1.total_processing_time > 30:
            suggestions.append("处理时间较长，建议启用并行处理或减少订阅源数量")
        
        if result1.total_articles_selected == 0:
            suggestions.append("没有筛选出文章，建议降低分数阈值或调整关键词配置")
        
        if result1.success_rate < 0.8:
            suggestions.append("部分订阅源处理失败，请检查网络连接或API限制")
        
        if not suggestions:
            suggestions.append("筛选效果良好，可以考虑增加订阅源数量或提高质量阈值")
        
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        
        print("\n🎉 演示完成！")
        print("\n📚 更多使用方法请参考:")
        print("  - docs/batch_filter_guide.md")
        print("  - test_batch_filter.py")
        print("  - demo_batch_filter.py")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("请确保所有依赖已正确安装")
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
