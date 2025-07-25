"""
命令行界面主入口
"""
import click
from typing import Optional

from ..services.filter_service import filter_service, CLIProgressCallback
from ..services.batch_filter_service import custom_rss_batch_filter_manager, BatchFilterConfig
from ..services.custom_rss_service import CustomRSSService
from ..utils.result_formatter import ResultFormatter, ResultExporter
from ..models.news import NewsArticle


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """新闻订阅工具 - 基于自定义RSS的新闻获取和管理工具"""
    pass


@cli.command()
@click.argument('url')
@click.option('--category', '-c', default='默认', help='RSS分类 (默认: 默认)')
def add_rss(url: str, category: str):
    """添加RSS订阅源"""
    rss_service = CustomRSSService()

    click.echo(f"📡 正在添加RSS订阅源: {url}")

    success, message = rss_service.add_subscription(url, category)

    if success:
        click.echo(f"✅ {message}")
    else:
        click.echo(f"❌ {message}")


@cli.command()
def list_rss():
    """显示RSS订阅源列表"""
    rss_service = CustomRSSService()

    feeds = rss_service.get_all_subscriptions()

    if not feeds:
        click.echo("📭 没有找到RSS订阅源")
        return

    click.echo(f"\n📊 RSS订阅源列表 (共 {len(feeds)} 个):")
    click.echo("-" * 80)

    for feed in feeds:
        status = "✅ 激活" if feed.is_active else "❌ 未激活"
        click.echo(f"📡 {feed.title} [{status}]")
        click.echo(f"   🔗 {feed.url}")
        click.echo(f"   🏷️  分类: {feed.category}")
        click.echo(f"   📰 文章数: {len(feed.articles)}")
        if feed.last_fetched:
            click.echo(f"   🕒 最后更新: {feed.last_fetched.strftime('%Y-%m-%d %H:%M:%S')}")
        click.echo()


@cli.command()
@click.option('--category', '-c', help='按分类筛选')
@click.option('--unread-only', '-u', is_flag=True, help='仅显示未读文章')
@click.option('--hours', '-h', type=int, help='显示多少小时内的文章')
def rss_news(category: Optional[str], unread_only: bool, hours: Optional[int]):
    """获取RSS新闻文章"""
    rss_service = CustomRSSService()

    click.echo("📰 正在获取RSS新闻...")

    articles = rss_service.get_all_articles(
        category=category,
        unread_only=unread_only,
        hours_back=hours
    )

    if not articles:
        click.echo("📭 没有找到文章")
        return

    click.echo(f"✅ 获取到 {len(articles)} 篇文章")

    # 显示文章列表
    _display_rss_articles(articles)


@cli.command()
def refresh_rss():
    """刷新所有RSS订阅源"""
    rss_service = CustomRSSService()

    click.echo("🔄 正在刷新所有RSS订阅源...")

    results = rss_service.refresh_all_feeds()

    if not results:
        click.echo("📭 没有找到激活的RSS订阅源")
        return

    total_new_articles = 0
    success_count = 0

    for feed_id, (success, message, new_count) in results.items():
        if success:
            success_count += 1
            total_new_articles += new_count
            click.echo(f"✅ {message} (新增 {new_count} 篇文章)")
        else:
            click.echo(f"❌ {message}")

    click.echo(f"\n📊 刷新完成: {success_count}/{len(results)} 个订阅源成功，共获取 {total_new_articles} 篇新文章")


@cli.command()
@click.option('--days', '-d', default=7, help='保留天数 (默认: 7天)')
@click.option('--dry-run', is_flag=True, help='仅显示将要删除的文章数量，不实际删除')
def cleanup_old(days: int, dry_run: bool):
    """清理指定天数之前的未读文章"""
    rss_service = CustomRSSService()

    if dry_run:
        click.echo(f"🔍 检查 {days} 天前的未读文章...")
        # 这里可以添加预览功能，暂时简化
        click.echo("使用 --dry-run 功能需要额外实现，当前直接显示清理结果")

    click.echo(f"🧹 正在清理 {days} 天前的未读文章...")

    removed_count, feeds_count = rss_service.cleanup_old_unread_articles(days)

    if removed_count > 0:
        click.echo(f"✅ 清理完成: 从 {feeds_count} 个订阅源中删除了 {removed_count} 篇旧的未读文章")
    else:
        click.echo("📭 没有找到需要清理的旧未读文章")


@cli.command()
def cleanup_status():
    """显示清理状态和统计信息"""
    rss_service = CustomRSSService()

    click.echo("📊 清理状态统计:")
    click.echo("-" * 50)

    # 统计各个时间段的未读文章
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)

    all_articles = rss_service.get_all_articles(unread_only=True)

    recent_count = len([a for a in all_articles if a.published > one_day_ago])
    week_count = len([a for a in all_articles if a.published > one_week_ago])
    month_count = len([a for a in all_articles if a.published > one_month_ago])
    old_count = len([a for a in all_articles if a.published <= one_week_ago])

    click.echo(f"📰 未读文章统计:")
    click.echo(f"   最近1天: {recent_count} 篇")
    click.echo(f"   最近1周: {week_count} 篇")
    click.echo(f"   最近1月: {month_count} 篇")
    click.echo(f"   1周前的: {old_count} 篇 (将被自动清理)")

    # 检查上次清理时间
    from pathlib import Path
    last_cleanup_file = Path.home() / ".news_selector" / "last_cleanup.txt"

    if last_cleanup_file.exists():
        try:
            with open(last_cleanup_file, 'r') as f:
                last_cleanup_str = f.read().strip()
                last_cleanup = datetime.fromisoformat(last_cleanup_str)
                time_since = now - last_cleanup

                click.echo(f"\n🕒 上次自动清理: {last_cleanup.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                click.echo(f"   距今: {time_since.days} 天 {time_since.seconds // 3600} 小时")
        except Exception:
            click.echo(f"\n🕒 上次自动清理: 无法读取记录")
    else:
        click.echo(f"\n🕒 上次自动清理: 从未执行")


def _display_rss_articles(articles):
    """显示RSS文章列表"""
    click.echo("\n📋 文章列表:")
    click.echo("=" * 80)

    for i, article in enumerate(articles, 1):
        # 状态指示器
        read_status = "✅" if article.is_read else "📰"
        star_status = "⭐" if article.is_starred else ""

        click.echo(f"{i:3d}. {read_status} {article.get_display_title(60)} {star_status}")
        click.echo(f"     🔗 {article.url}")
        click.echo(f"     📅 {article.published.strftime('%Y-%m-%d %H:%M')}")

        if article.author:
            click.echo(f"     👤 {article.author}")

        # 显示摘要（限制长度）
        if article.summary:
            summary = article.summary[:100] + "..." if len(article.summary) > 100 else article.summary
            click.echo(f"     📝 {summary}")

        click.echo()


def _display_articles(articles):
    """显示NewsArticle文章列表"""
    click.echo("\n📋 文章列表:")
    click.echo("=" * 80)

    for i, article in enumerate(articles, 1):
        # 状态指示器
        read_status = "✅" if article.is_read else "📰"
        star_status = "⭐" if article.is_starred else ""

        click.echo(f"{i:3d}. {read_status} {article.get_display_title(60)} {star_status}")
        click.echo(f"     🔗 {article.url}")
        click.echo(f"     📅 {article.published.strftime('%Y-%m-%d %H:%M')}")

        if article.author:
            click.echo(f"     👤 {article.author.name}")

        if article.feed_title:
            click.echo(f"     📡 {article.feed_title}")

        # 显示摘要（限制长度）
        if article.summary:
            summary = article.summary[:100] + "..." if len(article.summary) > 100 else article.summary
            click.echo(f"     📝 {summary}")

        click.echo()


@cli.command()
@click.option('--count', '-c', default=100, help='筛选文章数量 (默认: 100)')
@click.option('--filter-type', '-t', default='chain',
              type=click.Choice(['keyword', 'ai', 'chain']),
              help='筛选类型: keyword(关键词), ai(AI), chain(组合筛选, 默认)')
@click.option('--category', '-cat', help='按分类筛选RSS文章')
@click.option('--show-progress', '-p', is_flag=True, help='显示筛选进度')
@click.option('--show-details', '-d', is_flag=True, help='显示筛选详情')
def filter_rss(count: int, filter_type: str, category: Optional[str], show_progress: bool, show_details: bool):
    """智能筛选RSS新闻文章"""
    rss_service = CustomRSSService()

    # 获取RSS文章
    click.echo(f"📰 正在获取RSS文章...")
    rss_articles = rss_service.get_all_articles(
        category=category,
        unread_only=True,  # 只处理未读文章
        hours_back=24  # 最近24小时的文章
    )

    if not rss_articles:
        click.echo("📭 没有找到RSS文章")
        return

    # 转换为NewsArticle格式
    from ..models.news import NewsArticle, NewsAuthor
    articles = []
    for rss_article in rss_articles[:count]:
        news_article = NewsArticle(
            id=rss_article.id,
            title=rss_article.title,
            summary=rss_article.summary or "",
            content=rss_article.content or rss_article.summary or "",
            url=rss_article.url,
            published=rss_article.published,
            updated=rss_article.published,
            author=NewsAuthor(name=rss_article.author or "未知作者") if rss_article.author else None,
            categories=[],
            is_read=rss_article.is_read,
            is_starred=False,
            feed_title="RSS订阅"
        )
        articles.append(news_article)

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


if __name__ == '__main__':
    cli()
