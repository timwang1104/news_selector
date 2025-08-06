import json
import os
import sys

# Add project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Article, AnalysisJob, JobStatus, setup_database

# --- Configuration ---
HISTORICAL_JOB_ID = 0  # A special ID for all historical news
DB_URL = 'sqlite:///data/preference_analysis.db'
NEWS_FILE_PATH = 'data/crawled_news.json'

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

        # 4. Insert new articles
        print(f"Importing {len(news_data)} articles into the database...")
        articles_to_add = []
        for item in news_data:
            article = Article(
                job_id=HISTORICAL_JOB_ID,
                title=item.get('title', 'No Title'),
                content=item.get('content', ''),
                url=item.get('url', '')
                # published_at is omitted as it's not in the JSON
            )
            articles_to_add.append(article)
        
        session.bulk_save_objects(articles_to_add)
        session.commit()
        print("Successfully imported all historical news.")

    except Exception as e:
        print(f"An error occurred during import: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    import_historical_news()