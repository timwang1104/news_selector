"""
命令行界面主入口
"""
import click
from typing import Optional

from ..api.auth import InoreaderAuth
from ..services.news_service import NewsService
from ..services.subscription_service import SubscriptionService
from ..services.filter_service import filter_service, CLIProgressCallback
from ..services.batch_filter_service import batch_filter_manager, BatchFilterConfig, CLIBatchProgressCallback
from ..utils.result_formatter import ResultFormatter, ResultExporter
from ..models.news import NewsArticle


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """新闻订阅工具 - 基于Inoreader API的新闻获取和管理工具"""
    pass


@cli.command()
def login():
    """用户登录认证"""
    auth = InoreaderAuth()
    
    if auth.is_authenticated():
        click.echo("✅ 您已经登录")
        return
    
    click.echo("🔐 开始登录流程...")
    
    if auth.start_auth_flow():
        click.echo("✅ 登录成功！")
    else:
        click.echo("❌ 登录失败")


@cli.command()
def logout():
    """用户登出"""
    auth = InoreaderAuth()
    auth.logout()
    click.echo("✅ 已登出")


@cli.command()
def status():
    """显示登录状态和用户信息"""
    auth = InoreaderAuth()
    
    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return
    
    click.echo("✅ 已登录")
    
    # 获取用户信息
    subscription_service = SubscriptionService()
    user_info = subscription_service.get_user_info()
    
    if user_info:
        click.echo(f"👤 用户: {user_info.get('userName', 'Unknown')}")
        click.echo(f"📧 邮箱: {user_info.get('userEmail', 'Unknown')}")


@cli.command()
@click.option('--count', '-c', default=20, help='文章数量 (默认: 20)')
@click.option('--unread-only', '-u', is_flag=True, help='仅显示未读文章')
@click.option('--hours', '-h', type=int, help='显示多少小时内的文章')
def news(count: int, unread_only: bool, hours: Optional[int]):
    """获取最新新闻"""
    auth = InoreaderAuth()
    
    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return
    
    news_service = NewsService()
    
    click.echo("📰 正在获取最新新闻...")
    
    articles = news_service.get_latest_articles(
        count=count,
        exclude_read=unread_only,
        hours_back=hours
    )
    
    if not articles:
        click.echo("📭 没有找到文章")
        return
    
    # 显示文章列表
    _display_articles(articles)


@cli.command()
@click.option('--count', '-c', default=10, help='文章数量 (默认: 10)')
def starred(count: int):
    """获取星标文章"""
    auth = InoreaderAuth()
    
    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return
    
    news_service = NewsService()
    
    click.echo("⭐ 正在获取星标文章...")
    
    articles = news_service.get_starred_articles(count=count)
    
    if not articles:
        click.echo("📭 没有找到星标文章")
        return
    
    _display_articles(articles)


@cli.command()
@click.argument('keyword')
@click.option('--count', '-c', default=50, help='搜索范围内的文章数量 (默认: 50)')
def search(keyword: str, count: int):
    """搜索文章"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    news_service = NewsService()

    click.echo(f"🔍 正在搜索包含 '{keyword}' 的文章...")

    # 先获取最新文章，然后在其中搜索
    latest_articles = news_service.get_latest_articles(count=count, exclude_read=False)
    articles = news_service.search_articles(keyword, latest_articles)

    if not articles:
        click.echo(f"📭 没有找到包含 '{keyword}' 的文章")
        return

    click.echo(f"🎯 找到 {len(articles)} 篇相关文章:")
    _display_articles(articles)


@cli.command()
@click.argument('feed_name')
@click.option('--count', '-c', default=20, help='文章数量 (默认: 20)')
@click.option('--unread-only', '-u', is_flag=True, help='仅显示未读文章')
def feed(feed_name: str, count: int, unread_only: bool):
    """获取指定订阅源的文章"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    subscription_service = SubscriptionService()
    news_service = NewsService()

    # 搜索匹配的订阅源
    subscriptions = subscription_service.search_subscriptions(feed_name)

    if not subscriptions:
        click.echo(f"❌ 没有找到包含 '{feed_name}' 的订阅源")
        return

    if len(subscriptions) > 1:
        click.echo(f"🔍 找到 {len(subscriptions)} 个匹配的订阅源:")
        for i, sub in enumerate(subscriptions, 1):
            click.echo(f"  {i}. {sub.title}")

        choice = click.prompt("请选择订阅源编号", type=int)
        if choice < 1 or choice > len(subscriptions):
            click.echo("❌ 无效的选择")
            return

        selected_subscription = subscriptions[choice - 1]
    else:
        selected_subscription = subscriptions[0]

    click.echo(f"📰 正在获取 '{selected_subscription.title}' 的文章...")

    articles = news_service.get_articles_by_feed(
        feed_id=selected_subscription.id,
        count=count,
        exclude_read=unread_only
    )

    if not articles:
        click.echo("📭 没有找到文章")
        return

    _display_articles(articles)


@cli.command()
@click.option('--with-unread', '-u', is_flag=True, help='显示未读数量')
def feeds(with_unread: bool):
    """显示订阅源列表"""
    auth = InoreaderAuth()
    
    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return
    
    subscription_service = SubscriptionService()
    
    click.echo("📡 正在获取订阅源列表...")
    
    if with_unread:
        feeds_with_unread = subscription_service.get_subscriptions_with_unread_counts()
        
        if not feeds_with_unread:
            click.echo("📭 没有找到订阅源")
            return
        
        click.echo(f"\n📊 订阅源列表 (共 {len(feeds_with_unread)} 个):")
        click.echo("-" * 80)
        
        for item in feeds_with_unread:
            subscription = item['subscription']
            unread_count = item['unread_count']
            
            unread_indicator = f"({unread_count} 未读)" if unread_count > 0 else ""
            click.echo(f"📡 {subscription.get_display_title(60)} {unread_indicator}")
            
            if subscription.categories:
                categories = ", ".join(subscription.get_category_names())
                click.echo(f"   🏷️  分类: {categories}")
            
            click.echo(f"   🔗 {subscription.url}")
            click.echo()
    else:
        subscriptions = subscription_service.get_all_subscriptions()
        
        if not subscriptions:
            click.echo("📭 没有找到订阅源")
            return
        
        click.echo(f"\n📊 订阅源列表 (共 {len(subscriptions)} 个):")
        click.echo("-" * 80)
        
        for subscription in subscriptions:
            click.echo(f"📡 {subscription.title}")
            
            if subscription.categories:
                categories = ", ".join(subscription.get_category_names())
                click.echo(f"   🏷️  分类: {categories}")
            
            click.echo(f"   🔗 {subscription.url}")
            click.echo()


@cli.command()
@click.option('--count', '-c', default=100, help='筛选文章数量 (默认: 100)')
@click.option('--filter-type', '-t', default='chain',
              type=click.Choice(['keyword', 'ai', 'chain']),
              help='筛选类型: keyword(关键词), ai(AI), chain(组合筛选, 默认)')
@click.option('--show-progress', '-p', is_flag=True, help='显示筛选进度')
@click.option('--show-details', '-d', is_flag=True, help='显示筛选详情')
def filter_news(count: int, filter_type: str, show_progress: bool, show_details: bool):
    """智能筛选新闻文章"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    news_service = NewsService()

    # 获取文章
    click.echo(f"📰 正在获取最新 {count} 篇文章...")
    articles = news_service.get_latest_articles(count=count, exclude_read=False)

    if not articles:
        click.echo("📭 没有找到文章")
        return

    click.echo(f"✅ 获取到 {len(articles)} 篇文章，开始筛选...")

    # 执行筛选
    try:
        callback = CLIProgressCallback(show_progress) if show_progress else None
        result = filter_service.filter_articles(
            articles=articles,
            filter_type=filter_type,
            callback=callback
        )

        # 显示筛选结果
        _display_filter_result(result, show_details)

        # 显示筛选出的文章
        if result.selected_articles:
            click.echo(f"\n📋 筛选出的文章 ({len(result.selected_articles)} 篇):")
            click.echo("=" * 60)

            selected_news_articles = [r.article for r in result.selected_articles]
            _display_articles(selected_news_articles)

    except Exception as e:
        click.echo(f"❌ 筛选失败: {e}")


@cli.command()
@click.option('--config-type', '-t', default='chain',
              type=click.Choice(['keyword', 'ai', 'chain']),
              help='配置类型')
def filter_config(config_type: str):
    """显示筛选配置"""
    try:
        config = filter_service.get_config(config_type)

        click.echo(f"\n⚙️  {config_type.upper()} 筛选配置:")
        click.echo("-" * 50)

        for key, value in config.items():
            if isinstance(value, dict):
                click.echo(f"{key}:")
                for sub_key, sub_value in value.items():
                    click.echo(f"  {sub_key}: {sub_value}")
            else:
                click.echo(f"{key}: {value}")

    except Exception as e:
        click.echo(f"❌ 获取配置失败: {e}")


@cli.command()
def filter_metrics():
    """显示筛选性能指标"""
    try:
        metrics = filter_service.get_metrics()

        click.echo("\n📊 筛选性能指标:")
        click.echo("-" * 50)

        for filter_type, filter_metrics in metrics.items():
            if filter_metrics.get('status') == 'no_data':
                continue

            click.echo(f"\n{filter_type.upper()} 筛选器:")

            if 'avg_processing_time' in filter_metrics:
                click.echo(f"  平均处理时间: {filter_metrics['avg_processing_time']:.2f}ms")
                click.echo(f"  最大处理时间: {filter_metrics['max_processing_time']:.2f}ms")
                click.echo(f"  处理文章总数: {filter_metrics['total_processed']}")
                click.echo(f"  错误率: {filter_metrics['error_rate']:.2%}")

            if 'cache_hit_rate' in filter_metrics:
                click.echo(f"  缓存命中率: {filter_metrics['cache_hit_rate']:.2%}")
                click.echo(f"  缓存大小: {filter_metrics.get('cache_size', 0)}")

    except Exception as e:
        click.echo(f"❌ 获取指标失败: {e}")


@cli.command()
def stats():
    """显示统计信息"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    subscription_service = SubscriptionService()

    click.echo("📊 正在获取统计信息...")

    stats = subscription_service.get_subscription_statistics()

    click.echo(f"\n📈 统计信息:")
    click.echo("-" * 50)
    click.echo(f"📡 订阅源总数: {stats['total_subscriptions']}")
    click.echo(f"📰 未读文章总数: {stats['total_unread']}")

    if stats['categories']:
        click.echo(f"\n🏷️  分类统计:")
        for category, data in stats['categories'].items():
            click.echo(f"   {category}: {data['count']} 个订阅源, {data['unread']} 篇未读")
    
    if stats['most_active_feeds']:
        click.echo(f"\n🔥 最活跃的订阅源 (未读数量):")
        for item in stats['most_active_feeds'][:5]:
            subscription = item['subscription']
            unread_count = item['unread_count']
            if unread_count > 0:
                click.echo(f"   📡 {subscription.get_display_title(50)}: {unread_count} 篇未读")


def _display_filter_result(result, show_details: bool = False):
    """显示筛选结果摘要"""
    click.echo(f"\n🎯 筛选结果摘要:")
    click.echo("-" * 50)
    click.echo(f"📥 输入文章数: {result.total_articles}")
    click.echo(f"📝 关键词筛选通过: {result.keyword_filtered_count}")
    click.echo(f"🤖 AI筛选通过: {result.ai_filtered_count}")
    click.echo(f"✅ 最终选出: {result.final_selected_count}")
    click.echo(f"⏱️  总处理时间: {result.total_processing_time:.2f}秒")

    if result.keyword_filter_time > 0:
        click.echo(f"📝 关键词筛选时间: {result.keyword_filter_time:.2f}秒")
    if result.ai_filter_time > 0:
        click.echo(f"🤖 AI筛选时间: {result.ai_filter_time:.2f}秒")

    if result.warnings:
        click.echo(f"\n⚠️  警告:")
        for warning in result.warnings:
            click.echo(f"   {warning}")

    if result.errors:
        click.echo(f"\n❌ 错误:")
        for error in result.errors:
            click.echo(f"   {error}")

    if show_details and result.selected_articles:
        click.echo(f"\n📊 筛选详情:")
        click.echo("-" * 50)

        for i, combined_result in enumerate(result.selected_articles[:5], 1):
            article = combined_result.article
            click.echo(f"{i}. {article.get_display_title()}")

            if combined_result.keyword_result:
                kr = combined_result.keyword_result
                click.echo(f"   📝 关键词分数: {kr.relevance_score:.3f}")
                if kr.matched_keywords:
                    keywords = [m.keyword for m in kr.matched_keywords[:3]]
                    click.echo(f"   🔑 匹配关键词: {', '.join(keywords)}")

            if combined_result.ai_result:
                ar = combined_result.ai_result
                eval_result = ar.evaluation
                click.echo(f"   🤖 AI评分: {eval_result.total_score}/30")
                click.echo(f"   📊 详细评分: 相关性{eval_result.relevance_score} | 创新性{eval_result.innovation_impact} | 实用性{eval_result.practicality}")
                if ar.cached:
                    click.echo(f"   💾 (使用缓存)")

            click.echo(f"   🎯 最终分数: {combined_result.final_score:.3f}")
            click.echo()

        if len(result.selected_articles) > 5:
            click.echo(f"   ... 还有 {len(result.selected_articles) - 5} 篇文章")


def _display_articles(articles):
    """显示文章列表"""
    click.echo(f"\n📰 文章列表 (共 {len(articles)} 篇):")
    click.echo("=" * 80)
    
    for i, article in enumerate(articles, 1):
        # 状态指示器
        status_indicators = []
        if not article.is_read:
            status_indicators.append("🆕")
        if article.is_starred:
            status_indicators.append("⭐")
        
        status = " ".join(status_indicators) + " " if status_indicators else ""
        
        click.echo(f"{i:2d}. {status}{article.get_display_title()}")
        
        # 订阅源和时间
        feed_info = f"📡 {article.feed_title}" if article.feed_title else ""
        time_info = f"🕒 {article.published.strftime('%Y-%m-%d %H:%M')}"
        click.echo(f"    {feed_info}  {time_info}")
        
        # 摘要
        summary = article.get_short_summary(100)
        if summary:
            click.echo(f"    💬 {summary}")
        
        # URL
        if article.url:
            click.echo(f"    🔗 {article.url}")
        
        click.echo()


@cli.command()
@click.option('--filter-type', '-t', default='chain',
              type=click.Choice(['keyword', 'ai', 'chain']),
              help='筛选类型 (默认: chain)')
@click.option('--max-subscriptions', '-s', type=int,
              help='最大处理订阅源数量')
@click.option('--subscription-keywords', '-k', multiple=True,
              help='订阅源标题关键词过滤 (可多次指定)')
@click.option('--articles-per-sub', '-a', default=50, type=int,
              help='每个订阅源获取的文章数量 (默认: 50)')
@click.option('--top-results', '-n', default=20, type=int,
              help='显示的顶级结果数量 (默认: 20)')
@click.option('--min-score', '-m', type=float,
              help='最小分数阈值')
@click.option('--parallel/--sequential', default=True,
              help='是否并行处理 (默认: 并行)')
@click.option('--export-json', type=str,
              help='导出JSON结果到指定文件')
@click.option('--export-csv', type=str,
              help='导出CSV结果到指定文件')
@click.option('--group-by-subscription', is_flag=True,
              help='按订阅源分组显示结果')
@click.option('--show-details', is_flag=True,
              help='显示详细的订阅源处理结果')
def batch_filter(filter_type: str, max_subscriptions: Optional[int],
                subscription_keywords: tuple, articles_per_sub: int,
                top_results: int, min_score: Optional[float],
                parallel: bool, export_json: Optional[str],
                export_csv: Optional[str], group_by_subscription: bool,
                show_details: bool):
    """批量筛选多个订阅源的文章"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    # 创建批量筛选配置
    config = BatchFilterConfig()
    config.filter_type = filter_type
    config.max_subscriptions = max_subscriptions
    config.subscription_keywords = list(subscription_keywords)
    config.articles_per_subscription = articles_per_sub
    config.min_score_threshold = min_score
    config.enable_parallel = parallel
    config.group_by_subscription = group_by_subscription

    # 创建进度回调
    callback = CLIBatchProgressCallback(show_progress=True)

    try:
        # 执行批量筛选
        click.echo("🚀 开始批量筛选...")
        batch_result = batch_filter_manager.filter_subscriptions_batch(config, callback)

        # 显示摘要
        summary = ResultFormatter.format_batch_summary(batch_result)
        click.echo(summary)

        # 显示订阅源结果
        if show_details:
            sub_results = ResultFormatter.format_subscription_results(batch_result, show_details=True)
            click.echo(sub_results)

        # 显示顶级文章
        if batch_result.total_articles_selected > 0:
            top_articles = ResultFormatter.format_top_articles(
                batch_result,
                top_n=top_results,
                group_by_subscription=group_by_subscription
            )
            click.echo(top_articles)

        # 显示错误和警告
        errors_warnings = ResultFormatter.format_errors_and_warnings(batch_result)
        if errors_warnings:
            click.echo(errors_warnings)

        # 导出结果
        if export_json:
            json_content = ResultFormatter.export_to_json(batch_result, include_content=True)
            ResultExporter.save_to_file(json_content, export_json)
            click.echo(f"✅ JSON结果已导出到: {export_json}")

        if export_csv:
            csv_content = ResultFormatter.export_to_csv(batch_result)
            ResultExporter.save_to_file(csv_content, export_csv)
            click.echo(f"✅ CSV结果已导出到: {export_csv}")

    except Exception as e:
        click.echo(f"❌ 批量筛选失败: {e}")
        import traceback
        traceback.print_exc()


@cli.command()
@click.option('--subscription-keywords', '-k', multiple=True,
              help='订阅源标题关键词过滤 (可多次指定)')
@click.option('--max-subscriptions', '-s', type=int,
              help='最大显示订阅源数量')
def list_subscriptions(subscription_keywords: tuple, max_subscriptions: Optional[int]):
    """列出订阅源（支持关键词过滤）"""
    auth = InoreaderAuth()

    if not auth.is_authenticated():
        click.echo("❌ 未登录，请先运行 'login' 命令")
        return

    subscription_service = SubscriptionService()

    try:
        # 获取所有订阅源
        subscriptions = subscription_service.get_all_subscriptions()

        # 应用关键词过滤
        if subscription_keywords:
            filtered_subscriptions = []
            for subscription in subscriptions:
                title_lower = subscription.title.lower()
                if any(keyword.lower() in title_lower for keyword in subscription_keywords):
                    filtered_subscriptions.append(subscription)
            subscriptions = filtered_subscriptions

        # 限制数量
        if max_subscriptions:
            subscriptions = subscriptions[:max_subscriptions]

        if not subscriptions:
            click.echo("📭 没有找到匹配的订阅源")
            return

        click.echo(f"📰 找到 {len(subscriptions)} 个订阅源:")
        click.echo("=" * 80)

        for i, subscription in enumerate(subscriptions, 1):
            click.echo(f"{i:3d}. {subscription.title}")
            if subscription.categories:
                categories = ", ".join([cat.label for cat in subscription.categories])
                click.echo(f"     分类: {categories}")
            click.echo(f"     URL: {subscription.html_url}")
            click.echo()

    except Exception as e:
        click.echo(f"❌ 获取订阅源失败: {e}")


if __name__ == '__main__':
    cli()
