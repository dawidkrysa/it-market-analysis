"""Database handler for job postings using SQLAlchemy ORM."""

from sqlalchemy import Engine, create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime,timezone
from typing import Any

from sqlalchemy.orm.session import Session
from config.settings import Settings

Base = declarative_base()

class JobPosting(Base):
    """
    SQLAlchemy model for job postings.
    
    Attributes:
        id: Unique job identifier
        group_id: Group identifier for related jobs
        stanowisko: Job title/position
        firma: Company name
        poziom: Seniority level (Trainee, Junior, Mid, Senior)
        kategoria: Job category
        technologie: Required technologies (comma-separated)
        lokalizacja: Job location
        wynagrodzenie_od: Minimum salary
        wynagrodzenie_do: Maximum salary
        waluta: Currency (PLN, EUR, USD)
        utworzono: Job creation date
        zaktualizowano: Job last update date
        scraped_at: Timestamp when data was scraped
    """
    __tablename__: str = 'job_postings'
    
    id: Column[str] = Column(String, primary_key=True)
    group_id: Column[str] = Column(String)
    stanowisko: Column[str] = Column(Text)
    firma: Column[str] = Column(Text)
    poziom: Column[str] = Column(Text)
    kategoria: Column[str] = Column(Text)
    technologie: Column[str] = Column(Text)
    lokalizacja: Column[str] = Column(Text)
    wynagrodzenie_od: Column[int] = Column(Integer)
    wynagrodzenie_do: Column[int] = Column(Integer)
    waluta: Column[str] = Column(String)
    utworzono: Column[datetime] = Column(DateTime)
    zaktualizowano: Column[datetime] = Column(DateTime)
    scraped_at: Column[datetime] = Column(DateTime, default=datetime.now(timezone.utc))
    data_pobrania: Column[datetime] = Column(DateTime, default=datetime.now(timezone.utc))

class DatabaseHandler:
    """
    Handler for database operations related to job postings.
    
    Manages SQLAlchemy engine, sessions, and CRUD operations.
    """
    
    def __init__(self, database_url: str = Settings.DATABASE_URL) -> None:
        """
        Initialize database handler.
        
        Args:
            database_url: SQLAlchemy database URL (default from settings)
        """
        self.engine: Engine = create_engine(database_url)
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)
        
    def create_tables(self) -> None:
        """Create all database tables if they don't exist."""
        Base.metadata.create_all(self.engine)
    
    def save_jobs(self, jobs_data: list[dict[str, Any]]) -> None:
        """
        Save or update job postings in the database.
        
        Uses merge to handle both inserts and updates based on job ID.
        
        Args:
            jobs_data: List of job dictionaries with required fields
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = self.Session()
        try:
            for job in jobs_data:
                job_posting = JobPosting(
                    id=job['ID'],
                    stanowisko=job['Stanowisko'],
                    firma=job['Firma'],
                    poziom=job['Poziom'],
                    kategoria=job['Kategoria'],
                    technologie=job['Technologie'],
                    lokalizacja=job['Lokalizacja'],
                    wynagrodzenie_od=job['Wynagrodzenie Od'] if job['Wynagrodzenie Od'] else None,
                    wynagrodzenie_do=job['Wynagrodzenie Do'] if job['Wynagrodzenie Do'] else None,
                    waluta=job['Waluta'],
                    utworzono=job['Utworzono'],
                    zaktualizowano=job['Zaktualizowano'],
                    data_pobrania=datetime.now(timezone.utc)
                )
                session.merge(job_posting)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def clear_database(self) -> int:
        """
        Clear all job postings from the database.
        
        Returns:
            Number of deleted records
            
        Raises:
            Exception: If database operation fails
        """
        session: Session = self.Session()
        try:
            count: int = session.query(JobPosting).count()
            session.query(JobPosting).delete()
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_record_count(self) -> int:
        """
        Get the total number of job postings in the database.
        
        Returns:
            Number of records in the database
        """
        session: Session = self.Session()
        try:
            return session.query(JobPosting).count()
        finally:
            session.close()