"""Database handler for job postings using SQLAlchemy ORM."""

from sqlalchemy import Engine, create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime,timezone
from typing import Any
import pandas as pd
import re

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

    def get_blue_ocean_niches(self, min_jobs: int = 15, max_jobs: int = 70) -> pd.DataFrame:
        """
        Fetches data from the database and performs analysis to find "Blue Ocean" niches.
        Uses median imputation for missing salaries and calculates the market exposure time 
        of job postings.
        
        Args:
            min_jobs: Minimum number of job offers for a technology to be considered market-relevant.
            max_jobs: Maximum number of job offers above which the market is considered saturated.
            
        Returns:
            pd.DataFrame: A summary of potential niches, sorted by highest attractiveness.
        """
        # Fetch data as a list of dictionaries using the existing method
        jobs_data = self.get_all_jobs()
        
        if not jobs_data:
            return pd.DataFrame() # Return an empty DataFrame if the database is empty

        df = pd.DataFrame(jobs_data)

        df['Firma_Znormalizowana'] = df['Firma'].apply(self.__normalize_company_name)

        df = df.drop_duplicates(
            keep='first'
        )

        # --- STEP 1: DATA CLEANING AND FINANCIAL IMPUTATION ---
        df['Wynagrodzenie Od'] = pd.to_numeric(df['Wynagrodzenie Od'], errors='coerce')
        df['Wynagrodzenie Do'] = pd.to_numeric(df['Wynagrodzenie Do'], errors='coerce')

        df['Podane_Widelki'] = df['Wynagrodzenie Od'].notna() | df['Wynagrodzenie Do'].notna()

        # Fill missing values with the median grouped by category
        # (Using transform to preserve the original DataFrame shape)
        df['Wynagrodzenie Od'] = df.groupby('Kategoria')['Wynagrodzenie Od'].transform(lambda x: x.fillna(x.median()))
        df['Wynagrodzenie Do'] = df.groupby('Kategoria')['Wynagrodzenie Do'].transform(lambda x: x.fillna(x.median()))

        # If there are still missing values after group median imputation, fill them with the overall median
        df['Wynagrodzenie Od'] = df['Wynagrodzenie Od'].fillna(df['Wynagrodzenie Od'].median())
        df['Wynagrodzenie Do'] = df['Wynagrodzenie Do'].fillna(df['Wynagrodzenie Do'].median())
        
        # Calculate the average salary for a given position
        df['Srednia_Kwota'] = (df['Wynagrodzenie Od'] + df['Wynagrodzenie Do']) / 2

        # --- STEP 2: CALCULATING TIME ON MARKET (DEMAND PROXY) ---
        df['Utworzono'] = pd.to_datetime(df['Utworzono'], utc=True)
        df['Scraped At'] = pd.to_datetime(df['Scraped At'], utc=True)
        
        # Convert date difference to days (yields NaN if a date is missing)
        df['Czas_Na_Rynku_Dni'] = (df['Scraped At'] - df['Utworzono']).dt.days

        # --- STEP 3: TECHNOLOGY TOKENIZATION ---
        df_tech = df.dropna(subset=['Technologie']).copy()
        
        # Convert strings to lists (splitting by comma)
        df_tech['Technologia_Pojedyncza'] = df_tech['Technologie'].astype(str).str.split(',')
        
        # Explode - creates a separate row for each technology in the list (cloning the rest of the data)
        df_exploded = df_tech.explode('Technologia_Pojedyncza')
        
        # Text normalization (lowercase, stripping whitespaces)
        df_exploded['Technologia_Pojedyncza'] = df_exploded['Technologia_Pojedyncza'].str.strip().str.lower()
        
        # Define a list of generic tags to filter out (these are not specific technologies and may indicate missing data)
        generic_tags = [
            'brak danych', 'english', 'angielski', 'agile', 'scrum', 'git', 
            'jira', 'confluence', 'communication', 'team player', 
        ]

        # Filter out tags indicating missing data that were set in get_all_jobs()
        df_exploded = df_exploded[~df_exploded['Technologia_Pojedyncza'].isin(generic_tags)]

        # --- STEP 4: NICHE CONSOLIDATION ---
        niche_analysis = df_exploded.groupby('Technologia_Pojedyncza').agg(
            Liczba_Ofert=('ID', 'count'),
            Mediana_Zarobkow=('Srednia_Kwota', 'median'),
            Sredni_Czas_Zatrudnienia=('Czas_Na_Rynku_Dni', 'mean'),
            Procent_Ofert_Z_Widelkami=('Podane_Widelki', 'mean')
        ).reset_index()

        niche_analysis['Procent_Ofert_Z_Widelkami'] = (niche_analysis['Procent_Ofert_Z_Widelkami'] * 100).round(1)

        # --- STEP 5: FILTERING ---
        potencjalne_nisze = niche_analysis[
            (niche_analysis['Liczba_Ofert'] >= min_jobs) & 
            (niche_analysis['Liczba_Ofert'] <= max_jobs) &
            # Avoid niches where salary data is likely missing (less than 10% of offers with salary info)
            (niche_analysis['Procent_Ofert_Z_Widelkami'] >= 10.0)
        ].sort_values(
            by=['Mediana_Zarobkow', 'Procent_Ofert_Z_Widelkami', 'Sredni_Czas_Zatrudnienia'], 
            ascending=[False, False, True]
        )


        return potencjalne_nisze
    
    def __normalize_company_name(self, name: str) -> str:
        if pd.isna(name) or name == "Brak danych":
            return "nieznana"
        
        name = str(name).lower()
        
        # 1. Lista form do usunięcia (od najdłuższych do najkrótszych)
        legal_forms = [
            r'spółka z ograniczoną odpowiedzialnością',
            r'oddział w polsce',
            r'prosta spółka akcyjna',
            r'spółka akcyjna',
            r'spółka komandytowa',
            r'spółka jawna',
            r'sp\.?\s*z\s*o\.?\s*o\.?\s*sp\.?\s*k\.?', # sp. z o.o. sp. k.
            r'sp\.?\s*z\s*o\.?\s*o\.?',                # sp. z o.o. / sp z o o
            r'sp\.?\s*k\.?',                           # sp. k.
            r'p\.?\s*s\.?\s*a\.?',                     # p.s.a.
            r'prosta\s+s\.?\s*a\.?',                   # prosta s.a.
            r's\.?\s*a\.?',                            # s.a. / sa
            r's\.?\s*c\.?',                            # s.c.
            r'\blimited\b', r'\bltd\.?\b', r'\bllc\b',
            r'\bgmbh\b', r'\bag\b', r'\bkft\.?\b', 
            r'\bn\.?\s*v\.?\b', r'\bvvag\b', r'\bgroup\b'
        ]
        
        # 2. Usuwanie form prawnych
        for form in legal_forms:
            # Używamy zamiany, ignorując polskie znaki diakrytyczne jako granice słów
            name = re.sub(form, ' ', name)
            
        # 3. Usuwanie znaków interpunkcyjnych (w tym cudzysłowów w np. "MARITEX")
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # 4. Usunięcie nadmiarowych spacji
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name