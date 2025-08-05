import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import AnalysisJob, JobStatus, setup_database, AnalysisResult
from src.workers.preference_analysis_worker import PreferenceAnalysisWorker

class PreferenceAnalysisService:
    def __init__(self, db_url='sqlite:///data/preference_analysis.db'):
        self.db_url = db_url
        self.engine = create_engine(self.db_url)
        # Ensure tables are created
        setup_database(self.db_url)
        self.Session = sessionmaker(bind=self.engine)

    def request_analysis(self, rss_url):
        """
        Creates a new analysis job and starts a worker to process it.
        """
        session = self.Session()
        try:
            # Create a new job in the database
            new_job = AnalysisJob(rss_url=rss_url, status=JobStatus.PENDING)
            session.add(new_job)
            session.commit()
            job_id = new_job.id

            # Start the background worker
            worker = PreferenceAnalysisWorker(job_id, self.db_url)
            worker.start()

            print(f"Successfully requested analysis for {rss_url}. Job ID: {job_id}")
            return job_id
        except Exception as e:
            print(f"Failed to request analysis for {rss_url}. Error: {e}")
            session.rollback()
            return None
        finally:
            session.close()

    def get_analysis_status(self, job_id):
        """
        Retrieves the status of a specific analysis job.
        """
        session = self.Session()
        try:
            job = session.query(AnalysisJob).filter_by(id=job_id).first()
            if job:
                return job.status.value
            return None
        finally:
            session.close()

    def get_analysis_result(self, job_id):
        """
        Retrieves the results of a completed analysis job.
        """
        session = self.Session()
        try:
            result = session.query(AnalysisResult).filter_by(job_id=job_id, result_type='keyword').first()
            if result:
                return json.loads(result.data)
            return None
        finally:
            session.close()

# Example of how to use the service
if __name__ == '__main__':
    service = PreferenceAnalysisService('sqlite:///data/preference_analysis.db')
    
    # --- Test 1: Request a new analysis ---
    print("--- Testing: Request Analysis ---")
    test_rss_url = "http://feeds.bbci.co.uk/news/rss.xml"
    job_id = service.request_analysis(test_rss_url)

    if job_id:
        print(f"\n--- Testing: Polling for Status (Job ID: {job_id}) ---")
        # --- Test 2: Poll for status ---
        status = None
        while status not in ["COMPLETED", "FAILED"]:
            status = service.get_analysis_status(job_id)
            print(f"Current status: {status}")
            if status in ["COMPLETED", "FAILED"]:
                break
            import time
            time.sleep(3)

        # --- Test 3: Get the result ---
        print(f"\n--- Testing: Get Result (Job ID: {job_id}) ---")
        result = service.get_analysis_result(job_id)
        print(f"Final result: {result}")
    else:
        print("Failed to create a job for testing.")