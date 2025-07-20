#!/usr/bin/env python3
"""
火山引擎使用示例
"""
import os
import sys
sys.path.append('..')
from datetime import datetime

from src.config.agent_config import agent_config_manager
from src.ai.factory import create_ai_client
from src.config.filter_config import AIFilterConfig
from src.models.news import NewsArticle

def main():
    """火山引擎使用示例"""
    print("=== 火山引擎使用示例 ===\n")
    print("使用官方SDK volcengine-python-sdk")

    # 1. 设置API密钥（从环境变量或直接设置）
    api_key = os.getenv("VOLCENGINE_API_KEY") or os.getenv("ARK_API_KEY")
    if not api_key:
        print("请设置API密钥环境变量:")
        print("export VOLCENGINE_API_KEY=your_api_key")
        print("或")
        print("export ARK_API_KEY=your_api_key")
        return
    
    # 2. 设置火山引擎配置
    print("1. 设置火山引擎配置...")
    agent_config_manager.set_current_config("火山引擎")
    current_config = agent_config_manager.get_current_config()
    
    if current_config:
        print(f"✓ 当前配置: {current_config.config_name}")
        print(f"✓ 模型: {current_config.api_config.model_name}")
        print(f"✓ Base URL: {current_config.api_config.base_url}")
    else:
        print("✗ 火山引擎配置未找到")
        return
    
    # 3. 创建AI客户端
    print("\n2. 创建AI客户端...")
    config = AIFilterConfig()
    client = create_ai_client(config)
    print(f"✓ 客户端类型: {type(client).__name__}")
    
    # 4. 创建测试文章
    print("\n3. 创建测试文章...")
    test_articles = [
        NewsArticle(
            id="article_1",
            title="上海发布人工智能产业发展三年行动计划",
            summary="上海市政府发布了人工智能产业发展三年行动计划，提出到2026年产业规模突破5000亿元的目标。",
            content="""
            上海市政府近日发布《上海市人工智能产业发展三年行动计划（2024-2026年）》，
            明确提出到2026年，上海人工智能产业规模突破5000亿元，形成具有全球影响力的
            人工智能产业集群。计划重点发展大模型、智能芯片、智能机器人等核心技术，
            推动人工智能在制造业、金融、医疗、教育等领域的深度应用。
            """,
            url="https://example.com/ai-plan",
            published=datetime.now(),
            updated=datetime.now()
        ),
        NewsArticle(
            id="article_2", 
            title="某明星恋情曝光引发网友热议",
            summary="某知名明星的恋情被媒体曝光，引发了广泛的网络讨论。",
            content="娱乐新闻内容...",
            url="https://example.com/entertainment",
            published=datetime.now(),
            updated=datetime.now()
        ),
        NewsArticle(
            id="article_3",
            title="上海生物医药创新中心启动建设",
            summary="上海生物医药创新中心正式启动建设，将打造世界级生物医药产业集群。",
            content="""
            上海生物医药创新中心项目正式启动，该中心位于张江科学城核心区域，
            总投资超过100亿元，将建设包括新药研发平台、临床试验中心、
            产业化基地等在内的完整产业链条，预计将吸引200家以上生物医药企业入驻。
            """,
            url="https://example.com/biomedical",
            published=datetime.now(),
            updated=datetime.now()
        )
    ]
    
    print(f"✓ 创建了 {len(test_articles)} 篇测试文章")
    
    # 5. 单篇文章评估
    print("\n4. 单篇文章评估...")
    for i, article in enumerate(test_articles):
        print(f"\n评估文章 {i+1}: {article.title}")
        try:
            evaluation = client.evaluate_article(article)
            print(f"  总分: {evaluation.total_score}/30")
            print(f"  政策相关性: {evaluation.relevance_score}/10")
            print(f"  创新影响: {evaluation.innovation_impact}/10") 
            print(f"  实用性: {evaluation.practicality}/10")
            print(f"  置信度: {evaluation.confidence:.2f}")
            print(f"  评估理由: {evaluation.reasoning[:100]}...")
            
        except Exception as e:
            print(f"  ✗ 评估失败: {e}")
    
    # 6. 批量评估
    print("\n5. 批量评估...")
    try:
        batch_evaluations = client.evaluate_articles_batch(test_articles)
        print(f"✓ 批量评估完成，共 {len(batch_evaluations)} 个结果")
        
        for i, evaluation in enumerate(batch_evaluations):
            if evaluation:
                print(f"  文章 {i+1}: {evaluation.total_score}/30 分")
            else:
                print(f"  文章 {i+1}: 评估失败")
                
    except Exception as e:
        print(f"✗ 批量评估失败: {e}")
    
    # 7. 筛选高分文章
    print("\n6. 筛选高分文章...")
    threshold = 20  # 设置阈值为20分
    high_score_articles = []
    
    for i, article in enumerate(test_articles):
        try:
            evaluation = client.evaluate_article(article)
            if evaluation.total_score >= threshold:
                high_score_articles.append((article, evaluation))
        except Exception:
            continue
    
    print(f"✓ 找到 {len(high_score_articles)} 篇高分文章（>= {threshold}分）:")
    for article, evaluation in high_score_articles:
        print(f"  - {article.title} ({evaluation.total_score}分)")
    
    print("\n=== 示例完成 ===")

if __name__ == "__main__":
    main()
