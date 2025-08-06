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

    def analyze_historical_data(self):
        """
        Triggers an analysis run on the pre-loaded historical data.
        """
        # The historical data is associated with a predefined job ID.
        from scripts.import_historical_news import HISTORICAL_JOB_ID
        
        session = self.Session()
        try:
            # Find the special job for historical data
            historical_job = session.query(AnalysisJob).filter_by(id=HISTORICAL_JOB_ID).first()
            if not historical_job:
                print(f"Error: Historical job with ID {HISTORICAL_JOB_ID} not found. Please run the import script first.")
                return None

            # Reset status to PENDING to allow re-analysis
            historical_job.status = JobStatus.PENDING
            session.commit()

            # Start the worker for this specific job
            worker = PreferenceAnalysisWorker(historical_job.id, self.db_url)
            worker.start()

            print(f"Successfully started analysis for historical data. Job ID: {historical_job.id}")
            return historical_job.id
        except Exception as e:
            print(f"Failed to start historical analysis. Error: {e}")
            session.rollback()
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
    # This is an example of how you might use the service.
    # For a real application, you would import and use the service class elsewhere.
    print("PreferenceAnalysisService is ready to be used in your application.")
    # Example:
    # service = PreferenceAnalysisService()
    # job_id = service.request_analysis("http://example.com/rss.xml")
    # or
    # job_id = service.analyze_historical_data()