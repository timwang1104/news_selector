"""
命令行界面主入口
"""
import click
from typing import Optional

from ..api.auth import InoreaderAuth
from ..services.news_service import NewsService
from ..services.subscription_service import SubscriptionService
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


if __name__ == '__main__':
    cli()
