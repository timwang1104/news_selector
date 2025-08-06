import json
import os
import sys
import time
import logging
import requests

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Article, AnalysisJob, JobStatus, setup_database

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
HISTORICAL_JOB_ID = 0  # A special ID for all historical news
DB_URL = 'sqlite:///data/preference_analysis.db'
NEWS_FILE_PATH = 'data/crawled_news.json'

# Kimi API配置
KIMI_API_KEY = "sk-L2OPwC45YAGP5aShGcyAUXA8uK3XhTgJVWqjD7SKl5ukrP80"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = "kimi-k2-0711-preview"

# AI主题分类提示词模板
CATEGORY_PROMPT_TEMPLATE = """
你是一位专业的学术研究分析师。请根据以下新闻内容，从给定的学科领域列表中选择一个最合适的词来分类这篇新闻。

新闻标题：{title}
新闻内容：{content}

请从以下学科领域中选择最合适的一个词：
人工智能、机器学习、计算机视觉、自然语言处理、生物技术、医学、物理学、化学、材料科学、能源、环境科学、航空航天、机器人、量子计算、区块链、网络安全、软件工程、数据科学、金融科技、教育技术、其他

要求：
1. 只返回一个词，不要包含任何解释、标点符号或额外文字
2. 必须从上述列表中选择
3. 如果无法确定，请返回"其他"

分类结果：
"""

def call_kimi_api(prompt: str) -> str:
    """
    直接调用Kimi API进行文本生成
    
    Args:
        prompt: 输入提示词
    
    Returns:
        str: API响应内容
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KIMI_API_KEY}"
    }
    
    data = {
        "model": KIMI_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 100
    }
    
    try:
        response = requests.post(KIMI_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        if 'choices' in result and len(result['choices']) > 0:
            return result['choices'][0]['message']['content'].strip()
        else:
            logger.error(f"Kimi API响应格式异常: {result}")
            return ""
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Kimi API请求失败: {e}")
        return ""
    except Exception as e:
        logger.error(f"Kimi API调用异常: {e}")
        return ""

def classify_news_category(title: str, content: str) -> str:
    """
    使用Kimi AI对新闻进行主题分类
    
    Args:
        title: 新闻标题
        content: 新闻内容
    
    Returns:
        str: 分类结果，如果分类失败则返回"其他"
    """
    try:
        # 限制内容长度以避免token过多
        content_preview = content[:500] if content else ""
        
        # 构建提示词
        prompt = CATEGORY_PROMPT_TEMPLATE.format(
            title=title,
            content=content_preview
        )
        
        # 调用Kimi API
        logger.debug(f"正在调用Kimi分类API，标题: {title[:30]}...")
        response = call_kimi_api(prompt)
        
        if not response:
            logger.warning(f"Kimi API返回空响应，使用默认分类")
            return "其他"
        
        # 清理响应，只保留分类词
        category = response.strip().replace('"', '').replace("'", "").replace('`', '')
        
        # 移除可能的换行符和多余空格
        category = ' '.join(category.split())
        
        # 验证分类结果长度和内容
        if len(category) > 20:  # 如果返回内容过长，可能不是单个词
            logger.warning(f"AI返回的分类过长，使用默认分类: {category[:50]}...")
            return "其他"
        
        # 检查是否为空或无效响应
        if not category or category.lower() in ['none', 'null', 'undefined', '']:
            logger.warning(f"AI返回空分类，使用默认分类")
            return "其他"
            
        logger.info(f"Kimi分类成功: {title[:30]}... -> {category}")
        return category
        
    except Exception as e:
        logger.error(f"AI分类失败: {e}")
        return "其他"

def import_historical_news():
    """
    Imports news from a JSON file into the database under a special job ID.
    """
    print(f"Connecting to database: {DB_URL}")
    engine = setup_database(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Check if the historical job already exists
        historical_job = session.query(AnalysisJob).filter_by(id=HISTORICAL_JOB_ID).first()
        if not historical_job:
            print(f"Creating historical analysis job with ID: {HISTORICAL_JOB_ID}")
            historical_job = AnalysisJob(
                id=HISTORICAL_JOB_ID, 
                rss_url='local_import',
                status=JobStatus.COMPLETED # Mark as completed as it's a one-off import
            )
            session.add(historical_job)
            session.commit()
        else:
            print(f"Historical job with ID {HISTORICAL_JOB_ID} already exists.")

        # 2. Clear existing articles for this job to prevent duplicates on re-run
        print(f"Deleting existing articles for job ID {HISTORICAL_JOB_ID}...")
        session.query(Article).filter_by(job_id=HISTORICAL_JOB_ID).delete()
        session.commit()

        # 3. Load news from JSON file
        print(f"Loading news from {NEWS_FILE_PATH}...")
        if not os.path.exists(NEWS_FILE_PATH):
            print(f"Error: News file not found at {NEWS_FILE_PATH}")
            return

        with open(NEWS_FILE_PATH, 'r', encoding='utf-8') as f:
            news_data = json.load(f)

        # 4. 验证Kimi API配置
        print("Verifying Kimi API configuration...")
        print(f"Using Kimi model: {KIMI_MODEL}")
        print(f"API base URL: {KIMI_API_URL}")
        print(f"API key: {KIMI_API_KEY[:10]}...{KIMI_API_KEY[-10:]}")
        
        # 测试API连接
        test_response = call_kimi_api("你好")
        if test_response:
            print("Kimi API连接测试成功！")
            kimi_available = True
        else:
            print("Warning: Kimi API连接测试失败，将跳过AI分类")
            kimi_available = False

        # 5. Insert new articles with AI classification
        print(f"Importing {len(news_data)} articles into the database with AI classification...")
        articles_to_add = []
        
        for i, item in enumerate(news_data):
            title = item.get('title', 'No Title')
            content = item.get('content', '')
            url = item.get('url', '')
            
            # 使用Kimi AI进行主题分类
            if kimi_available:
                print(f"Processing article {i+1}/{len(news_data)}: {title[:50]}...")
                category = classify_news_category(title, content)
                # 添加延迟以避免API限制（Kimi API有速率限制）
                time.sleep(1.0)  # 增加延迟时间
            else:
                category = "其他"
                print(f"Skipping AI classification for article {i+1}/{len(news_data)} (Kimi API not available)")
            
            article = Article(
                job_id=HISTORICAL_JOB_ID,
                title=title,
                content=content,
                url=url,
                category=category
                # published_at is omitted as it's not in the JSON
            )
            articles_to_add.append(article)
        
        session.bulk_save_objects(articles_to_add)
        session.commit()
        print("Successfully imported all historical news with AI classification.")

    except Exception as e:
        print(f"An error occurred during import: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    import_historical_news()