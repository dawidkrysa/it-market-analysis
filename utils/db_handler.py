"""Database handler for job postings using SQLAlchemy ORM."""

from sqlalchemy import Engine, create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime,timezone
from typing import Any

from sqlalchemy.orm.session import Session
from config.settings import Settings

import enum
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()

class SeniorityLevel(enum.Enum):
    TRAINEE = "TRAINEE"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"

class Currency(enum.Enum):
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"

class Source(enum.Enum):
    JUSTJOINIT = "JUSTJOINIT"
    NOFLUFFJOBS = "NOFLUFFJOBS"
    THEPROTOCOLIT = "THEPROTOCOLIT"
    MANUAL = "MANUAL"

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
        source: Source of the job posting (e.g., "justjoinit")
    """
    __tablename__: str = 'job_postings'
    
    id: Column[str] = Column(String, primary_key=True)
    group_id: Column[str] = Column(String)
    stanowisko: Column[str] = Column(Text)
    firma: Column[str] = Column(Text)
    poziom: Column[str] = Column(SQLEnum(SeniorityLevel), nullable=True)
    kategoria: Column[str] = Column(Text)
    technologie: Column[str] = Column(Text)
    lokalizacja: Column[str] = Column(Text)
    wynagrodzenie_od: Column[int] = Column(Integer)
    wynagrodzenie_do: Column[int] = Column(Integer)
    waluta: Column[str] = Column(SQLEnum(Currency), nullable=True)
    utworzono: Column[datetime] = Column(DateTime)
    zaktualizowano: Column[datetime] = Column(DateTime)
    scraped_at: Column[datetime] = Column(DateTime, default=datetime.now(timezone.utc))
    data_pobrania: Column[datetime] = Column(DateTime, default=datetime.now(timezone.utc))
    source: Column[str] = Column(SQLEnum(Source), nullable=True)

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
    
    def save_jobs(self, jobs_data: list[dict[str, Any]]) -> int:
        """
        Save or update job postings in the database.
        
        Uses merge to handle both inserts and updates based on job ID.
        
        Args:
            jobs_data: List of job dictionaries with required fields
            
        Returns:
            Number of jobs processed
            
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
                    data_pobrania=datetime.now(timezone.utc),
                    source=job['Source'].strip().upper() if job.get('Source') else None
                )
                session.merge(job_posting)
            session.commit()
            return len(jobs_data)
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
    
    def get_all_jobs(self) -> list[dict[str, Any]]:
        """
        Get all job postings from the database as a list of dictionaries.
        
        Returns:
            List of job dictionaries
        """
        session: Session = self.Session()
        try:
            jobs = session.query(JobPosting).all()
            return [
                {
                    'ID': job.id,
                    'Stanowisko': job.stanowisko,
                    'Firma': job.firma,
                    'Poziom': job.poziom.value if job.poziom else None, # type: ignore
                    'Kategoria': job.kategoria,
                    'Technologie': job.technologie if job.technologie else "Brak danych", # type: ignore
                    'Lokalizacja': job.lokalizacja,
                    'Wynagrodzenie Od': job.wynagrodzenie_od,
                    'Wynagrodzenie Do': job.wynagrodzenie_do,
                    'Waluta': job.waluta.value if job.waluta else None, # type: ignore
                    'Utworzono': job.utworzono,
                    'Zaktualizowano': job.zaktualizowano,
                    'Scraped At': job.scraped_at,
                    'Source': job.source.value if job.source else None # type: ignore
                }
                for job in jobs
            ]
        finally:
            session.close()