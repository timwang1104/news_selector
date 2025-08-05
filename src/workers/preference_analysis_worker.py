import threading
import time
import json
import jieba
import jieba.analyse
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

from src.database.models import AnalysisJob, JobStatus, Article, AnalysisResult
from src.services.rss_service import RSSService

class PreferenceAnalysisWorker(threading.Thread):
    def __init__(self, job_id, db_url='sqlite:///data/preference_analysis.db', top_k=20):
        super().__init__()
        self.job_id = job_id
        self.db_url = db_url
        self.top_k = top_k
        self.daemon = True

    def run(self):
        print(f"Worker starting for job {self.job_id}")
        engine = create_engine(self.db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            job = session.query(AnalysisJob).filter_by(id=self.job_id).first()
            if not job:
                print(f"Error: Job {self.job_id} not found.")
                return

            job.status = JobStatus.RUNNING
            session.commit()

            # 1. Fetch articles from RSS feed
            print(f"Fetching articles from {job.rss_url}")
            rss_service = RSSService()
            articles_data = rss_service.fetch_articles_for_analysis(job.rss_url)
            if not articles_data:
                raise ValueError("No articles found or failed to fetch feed.")

            # 2. Store articles in the database
            print(f"Storing {len(articles_data)} articles for job {self.job_id}")
            for article_data in articles_data:
                article = Article(
                    job_id=self.job_id,
                    title=article_data['title'],
                    content=article_data['content'],
                    published_at=article_data['published_at'],
                    url=article_data['url']
                )
                session.add(article)
            session.commit()

            # 3. Perform keyword extraction
            print("Performing keyword extraction...")
            full_text = " ".join([
                f"{article.title} {article.content}" 
                for article in job.articles
            ])
            
            keywords = jieba.analyse.extract_tags(full_text, topK=self.top_k, withWeight=True)
            
            # 4. Save keyword analysis results
            keyword_result = AnalysisResult(
                job_id=self.job_id,
                result_type='keyword',
                data=json.dumps(keywords, ensure_ascii=False)
            )
            session.add(keyword_result)
            
            print(f"Analysis for job {self.job_id} finished. Found {len(keywords)} keywords.")

            # 5. Update job status to COMPLETED
            job.status = JobStatus.COMPLETED
            session.commit()
            print(f"Job {self.job_id} marked as COMPLETED.")

        except Exception as e:
            print(f"An error occurred in worker for job {self.job_id}: {e}")
            # Rollback any changes
            session.rollback()
            # Mark job as FAILED
            job = session.query(AnalysisJob).filter_by(id=self.job_id).first()
            if job:
                job.status = JobStatus.FAILED
                session.commit()
        finally:
            session.close()

if __name__ == '__main__':
    # This is for demonstration and testing purposes
    print("Running worker demonstration.")
    # You would typically not run the worker directly like this.
    # The service would start it.
    # For a test, you'd need to create a job in the DB first.