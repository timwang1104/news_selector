#!/usr/bin/env python3
"""
筛选功能演示脚本
"""
from datetime import datetime
from src.models.news import NewsArticle
from src.services.filter_service import FilterService, CLIProgressCallback


def create_demo_articles():
    """创建演示文章"""
    now = datetime.now()
    
    articles = [
        NewsArticle(
            id="demo_1",
            title="OpenAI releases breakthrough artificial intelligence model with advanced machine learning capabilities",
            summary="The latest large language model shows significant improvements in reasoning and code generation, marking a major advance in AI technology",
            content="OpenAI announced today the release of a new generation GPT model that achieves major breakthroughs in natural language processing and machine learning algorithm optimization...",
            url="http://example.com/ai-breakthrough",
            published=now,
            updated=now,
            feed_title="Tech News"
        ),
        NewsArticle(
            id="demo_2",
            title="China announces $10 billion quantum computing research investment plan",
            summary="Government funding aims to accelerate quantum technology development and maintain technological leadership",
            content="The Chinese government announced an ambitious quantum technology investment plan, focusing on quantum computing, quantum communication and quantum sensor technologies...",
            url="http://example.com/quantum-investment",
            published=now,
            updated=now,
            feed_title="Policy News"
        ),
        NewsArticle(
            id="demo_3",
            title="FDA approves revolutionary CRISPR gene editing therapy for genetic disorders",
            summary="Revolutionary gene editing treatment offers hope for patients with inherited diseases",
            content="The US Food and Drug Administration approved a CRISPR-based gene editing therapy for treating rare genetic diseases, marking a milestone in biotechnology...",
            url="http://example.com/crispr-therapy",
            published=now,
            updated=now,
            feed_title="Medical News"
        ),
        NewsArticle(
            id="demo_4",
            title="Local restaurant opens new downtown location",
            summary="Popular eatery expands to meet growing customer demand in city center",
            content="This beloved local restaurant decided to open a second location in the bustling downtown area...",
            url="http://example.com/restaurant-news",
            published=now,
            updated=now,
            feed_title="Local News"
        ),
        NewsArticle(
            id="demo_5",
            title="Technology stocks drive market to new highs amid AI and innovation surge",
            summary="Investors show confidence in tech sector growth prospects driven by artificial intelligence advances",
            content="Driven by emerging technologies like artificial intelligence and quantum computing, tech stocks performed strongly, pushing the overall market higher...",
            url="http://example.com/stock-market",
            published=now,
            updated=now,
            feed_title="Financial News"
        ),
        NewsArticle(
            id="demo_6",
            title="MIT researchers develop breakthrough battery technology for electric vehicles",
            summary="Energy storage breakthrough could revolutionize the electric vehicle industry with faster charging",
            content="MIT research team developed a new lithium battery technology that increases energy density by 50% and reduces charging time to 10 minutes...",
            url="http://example.com/battery-tech",
            published=now,
            updated=now,
            feed_title="Tech News"
        )
    ]
    
    return articles


def main():
    """主演示函数"""
    print("🎯 新闻智能筛选功能演示")
    print("=" * 60)
    
    # 创建演示文章
    articles = create_demo_articles()
    print(f"📰 创建了 {len(articles)} 篇演示文章")
    
    # 显示原始文章列表
    print(f"\n📋 原始文章列表:")
    print("-" * 50)
    for i, article in enumerate(articles, 1):
        print(f"{i}. {article.title}")
        print(f"   来源: {article.feed_title}")
        print()
    
    # 创建筛选服务
    filter_service = FilterService()
    
    # 执行关键词筛选
    print("🔍 执行关键词筛选...")
    print("-" * 50)
    
    callback = CLIProgressCallback(show_progress=True)
    result = filter_service.filter_articles(
        articles=articles,
        filter_type="keyword",
        callback=callback
    )
    
    # 显示筛选结果
    print(f"\n🎯 筛选结果摘要:")
    print("-" * 50)
    print(f"📥 输入文章数: {result.total_articles}")
    print(f"📝 关键词筛选通过: {result.keyword_filtered_count}")
    print(f"✅ 最终选出: {result.final_selected_count}")
    print(f"⏱️  总处理时间: {result.total_processing_time:.3f}秒")
    
    if result.selected_articles:
        print(f"\n📊 筛选出的文章详情:")
        print("-" * 50)
        
        for i, combined_result in enumerate(result.selected_articles, 1):
            article = combined_result.article
            print(f"{i}. {article.title}")
            print(f"   来源: {article.feed_title}")
            
            if combined_result.keyword_result:
                kr = combined_result.keyword_result
                print(f"   📝 关键词分数: {kr.relevance_score:.3f}")
                if kr.matched_keywords:
                    keywords = [m.keyword for m in kr.matched_keywords[:3]]
                    print(f"   🔑 匹配关键词: {', '.join(keywords)}")
                
                if kr.category_scores:
                    categories = [f"{cat}({score:.2f})" for cat, score in kr.category_scores.items()]
                    print(f"   🏷️  分类评分: {', '.join(categories)}")
            
            print(f"   🎯 最终分数: {combined_result.final_score:.3f}")
            print()
    
    # 显示配置信息
    print(f"\n⚙️  当前筛选配置:")
    print("-" * 50)
    config = filter_service.get_config("keyword")
    print(f"筛选阈值: {config['threshold']}")
    print(f"最大结果数: {config['max_results']}")
    print(f"最少匹配关键词: {config['min_matches']}")
    
    # 显示性能指标
    print(f"\n📊 性能指标:")
    print("-" * 50)
    metrics = filter_service.get_metrics()
    keyword_metrics = metrics.get("keyword_filter", {})
    if keyword_metrics.get("status") != "no_data":
        print(f"平均处理时间: {keyword_metrics.get('avg_processing_time', 0):.2f}ms")
        print(f"处理文章总数: {keyword_metrics.get('total_processed', 0)}")
        print(f"错误率: {keyword_metrics.get('error_rate', 0):.2%}")
    
    print(f"\n✅ 演示完成！")
    print("💡 提示: 可以使用 'python main.py filter-news --help' 查看完整的筛选命令选项")


if __name__ == "__main__":
    main()
