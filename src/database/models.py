from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import enum
import os

Base = declarative_base()

class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AnalysisJob(Base):
    __tablename__ = 'analysis_jobs'

    id = Column(Integer, primary_key=True)
    rss_url = Column(String, nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    results = relationship("AnalysisResult", back_populates="job", cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AnalysisJob(id={self.id}, rss_url='{self.rss_url}', status='{self.status.value}')>"

class AnalysisResult(Base):
    __tablename__ = 'analysis_results'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('analysis_jobs.id'), nullable=False)
    result_type = Column(String, nullable=False)  # e.g., 'keyword', 'topic'
    data = Column(Text, nullable=False)  # JSON-encoded result data
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("AnalysisJob", back_populates="results")

    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, job_id={self.job_id}, type='{self.result_type}')>"

class Article(Base):
    __tablename__ = 'articles'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('analysis_jobs.id'), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    published_at = Column(DateTime, nullable=True)
    url = Column(String, nullable=True)

    job = relationship("AnalysisJob", back_populates="articles")

    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:30]}...')>"


# Example of how to setup the database
def setup_database(db_url='sqlite:///analysis.db'):
    # Ensure the directory for the database exists
    if db_url.startswith('sqlite:///'):
        db_path = db_url[10:]
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine

if __name__ == '__main__':
    # This is for demonstration and testing purposes
    # Note: This path is relative to the project root when run as a script from the root
    engine = setup_database('sqlite:///data/preference_analysis.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    # Example usage:
    # new_job = AnalysisJob(rss_url='http://example.com/rss')
    # session.add(new_job)
    # session.commit()
    
    print("Database and tables created successfully.")