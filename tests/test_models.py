"""
测试数据模型
"""
import pytest
from datetime import datetime
from src.models.news import NewsArticle, NewsAuthor, NewsCategory
from src.models.subscription import Subscription, SubscriptionCategory


class TestNewsArticle:
    """测试新闻文章模型"""
    
    def test_from_api_response(self):
        """测试从API响应创建文章对象"""
        api_data = {
            'id': 'test_article_id',
            'title': 'Test Article Title',
            'summary': {'content': '<p>Test summary content</p>'},
            'content': {'content': '<p>Test article content</p>'},
            'canonical': [{'href': 'https://example.com/article'}],
            'published': 1640995200,  # 2022-01-01 00:00:00
            'updated': 1640995200,
            'author': 'Test Author',
            'categories': [
                {'id': 'user/-/state/com.google/read', 'label': 'read'},
                {'id': 'user/-/state/com.google/starred', 'label': 'starred'}
            ],
            'origin': {
                'streamId': 'feed/test_feed_id',
                'title': 'Test Feed'
            }
        }
        
        article = NewsArticle.from_api_response(api_data)
        
        assert article.id == 'test_article_id'
        assert article.title == 'Test Article Title'
        assert article.summary == 'Test summary content'
        assert article.content == 'Test article content'
        assert article.url == 'https://example.com/article'
        assert article.is_read == True
        assert article.is_starred == True
        assert article.feed_id == 'feed/test_feed_id'
        assert article.feed_title == 'Test Feed'
        assert article.author.name == 'Test Author'
    
    def test_clean_html(self):
        """测试HTML清理功能"""
        html_content = '<p>This is <strong>bold</strong> text with <a href="#">link</a></p>'
        cleaned = NewsArticle._clean_html(html_content)
        assert cleaned == 'This is bold text with link'
    
    def test_get_short_summary(self):
        """测试短摘要生成"""
        article = NewsArticle(
            id='test',
            title='Test',
            summary='This is a very long summary that should be truncated at some point to fit within the specified length limit.',
            content='',
            url='',
            published=datetime.now(),
            updated=datetime.now()
        )
        
        short_summary = article.get_short_summary(50)
        assert len(short_summary) <= 53  # 50 + "..."
        assert short_summary.endswith('...')
    
    def test_get_display_title(self):
        """测试显示标题生成"""
        article = NewsArticle(
            id='test',
            title='This is a very long title that should be truncated',
            summary='',
            content='',
            url='',
            published=datetime.now(),
            updated=datetime.now()
        )
        
        display_title = article.get_display_title(30)
        assert len(display_title) <= 30
        assert display_title.endswith('...')


class TestSubscription:
    """测试订阅源模型"""
    
    def test_from_api_response(self):
        """测试从API响应创建订阅源对象"""
        api_data = {
            'id': 'feed/test_feed_id',
            'title': 'Test Feed Title',
            'url': 'https://example.com/feed.xml',
            'htmlUrl': 'https://example.com',
            'iconUrl': 'https://example.com/icon.png',
            'categories': [
                {'id': 'user/-/label/Technology', 'label': 'Technology'},
                {'id': 'user/-/label/News', 'label': 'News'}
            ],
            'firstitemmsec': 1640995200000,
            'sortid': 'A1B2C3'
        }
        
        subscription = Subscription.from_api_response(api_data)
        
        assert subscription.id == 'feed/test_feed_id'
        assert subscription.title == 'Test Feed Title'
        assert subscription.url == 'https://example.com/feed.xml'
        assert subscription.html_url == 'https://example.com'
        assert subscription.icon_url == 'https://example.com/icon.png'
        assert len(subscription.categories) == 2
        assert subscription.categories[0].label == 'Technology'
        assert subscription.categories[1].label == 'News'
    
    def test_get_category_names(self):
        """测试获取分类名称列表"""
        subscription = Subscription(
            id='test',
            title='Test',
            url='',
            html_url='',
            categories=[
                SubscriptionCategory(id='cat1', label='Category 1'),
                SubscriptionCategory(id='cat2', label='Category 2')
            ]
        )
        
        category_names = subscription.get_category_names()
        assert category_names == ['Category 1', 'Category 2']
    
    def test_get_display_title(self):
        """测试显示标题生成"""
        subscription = Subscription(
            id='test',
            title='This is a very long subscription title',
            url='',
            html_url=''
        )
        
        display_title = subscription.get_display_title(20)
        assert len(display_title) <= 20
        assert display_title.endswith('...')
