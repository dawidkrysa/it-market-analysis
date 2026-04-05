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
    
    # Minimum percentage of offers with salary information required to consider a niche valid
    MIN_SALARY_TRANSPARENCY_PERCENT = 10.0
    
    # Generic tags that don't represent specific technologies
    GENERIC_TECHNOLOGY_TAGS = frozenset([
        # Braki danych
        'brak danych', 
        
        # Tryb i warunki pracy
        'gotowość do pracy zmianowej', 'praca zdalna', 'praca hybrydowa', 
        'praca stacjonarna', 'elastyczne godziny pracy',
        
        # Języki obce i kompetencje miękkie
        'english', 'angielski', 'french', 'communication', 'team player', 
        'negotiations skills', 'communication skills', 'analytical thinking', 
        'analytical skills', 'problem solving', 'tech-savvy', 'zaangażowanie', 
        'zdolności analityczne', 'ai interest',
        
        # Narzędzia i metodyki (uznane za generyczne w Twoim algorytmie)
        'agile', 'scrum', 'git', 'jira', 'confluence', 'devops', 'docker', 
        'kubernetes', 'ci/cd', 'itil', 'project management', 'agile project management',
        
        # Umiejętności biurowe i nietechniczne
        'accounting', 'financial accounting', 'excel', 'ms excel', 'ms office', 
        'office 365', 'microsoft office', 'powerpoint', 'ms project', 'rysunek techniczny',
        
        # Inne dziedziny i role biznesowe
        'recruitment', 'tutoring', 'business analysis', 'business development', 
        'customer support', 'helpdesk', 'customer experience (cx)', 'finance', 
        'finanse', 'procurement', 'supply chain', 'ilustracja', 'grafika', 'pmo',
        
        # Zbyt ogólne pojęcia IT (tzw. buzzwords)
        'pc hardware skills', 'znajomość systemów it', 'data visualization', 
        'cloud computing', 'cloud', 'it support', 'it', 'it basics', 'security', 
        'cybersecurity', 'programming', 'bazy danych', 'networking', 'network', 
        'data', 'hardware', 'os', 'algorithms', 'math', 'matematyka',
        
        # Koncepcje testowania i inżynierii (zbyt ogólne)
        'skalowalny kod', 'software testing concept', 'testing theory', 'testing', 
        'manual testing', 'qa', 'automated testing', 'engineering principles', 'database design'
    ])
    
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
    def _deduplicate_jobs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate job postings based on normalized company name and key attributes.
        
        Args:
            df: DataFrame with job postings
            
        Returns:
            DataFrame with duplicates removed
        """
        df['Firma_Znormalizowana'] = df['Firma'].apply(self.__normalize_company_name)
        
        df = df.drop_duplicates(
            subset=['Firma_Znormalizowana', 'Stanowisko', 'Technologie', 'Wynagrodzenie Od', 'Wynagrodzenie Do'],
            keep='first'
        )
        
        # Drop the temporary normalization column as it's no longer needed
        return df.drop(columns=['Firma_Znormalizowana'])
    
    def _prepare_salary_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare salary data for analysis without imputation.
        
        Strategy:
        1. Convert salary columns to numeric
        2. Calculate average salary ONLY for positions with real salary data
        3. Keep track of which salaries are real vs missing
        
        Args:
            df: DataFrame with job postings
            
        Returns:
            DataFrame with prepared salary data and tracking columns
        """
        # Fill missing currency with "PLN" if the column exists
        if 'Waluta' in df.columns:
            df['Waluta'] = df['Waluta'].fillna("PLN")

        # Convert to numeric, coercing errors to NaN
        df['Wynagrodzenie Od'] = pd.to_numeric(df['Wynagrodzenie Od'], errors='coerce')
        df['Wynagrodzenie Do'] = pd.to_numeric(df['Wynagrodzenie Do'], errors='coerce')

        # Convert outliers (hourly rates < 1000) to monthly salary
        df.loc[df["Wynagrodzenie Od"] < 1000, "Wynagrodzenie Od"] *= 168
        df.loc[df["Wynagrodzenie Do"] < 1000, "Wynagrodzenie Do"] *= 168
        
        # Track which rows have real salary data (both from and to are present)
        df['Ma_Realne_Wynagrodzenie'] = (
            df['Wynagrodzenie Od'].notna() & df['Wynagrodzenie Do'].notna()
        )
        
        # Calculate the average salary ONLY for positions with complete salary data
        df['Srednia_Kwota'] = df.apply(
            lambda row: (row['Wynagrodzenie Od'] + row['Wynagrodzenie Do']) / 2
            if row['Ma_Realne_Wynagrodzenie'] else None,
            axis=1
        )
        
        return df
    
    def _calculate_market_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate how long each job posting has been on the market.
        
        Args:
            df: DataFrame with job postings
            
        Returns:
            DataFrame with market time calculated in days
        """
        df['Utworzono'] = pd.to_datetime(df['Utworzono'], utc=True)
        df['Scraped At'] = pd.to_datetime(df['Scraped At'], utc=True)
        
        # Convert date difference to days (yields NaN if a date is missing)
        df['Czas_Na_Rynku_Dni'] = (df['Scraped At'] - df['Utworzono']).dt.days
        
        return df
    
    def _explode_technologies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tokenize and explode technology strings into individual rows.
        
        Process:
        1. Split comma-separated technology strings
        2. Create separate row for each technology
        3. Normalize text (lowercase, strip whitespace)
        4. Filter out generic tags
        
        Args:
            df: DataFrame with job postings
            
        Returns:
            DataFrame with one row per technology per job
        """
        df_tech = df.dropna(subset=['Technologie']).copy()
        
        # Convert strings to lists (splitting by comma)
        df_tech['Technologia_Pojedyncza'] = df_tech['Technologie'].astype(str).str.split(',')
        
        # Explode - creates a separate row for each technology in the list
        df_exploded = df_tech.explode('Technologia_Pojedyncza')
        
        # Text normalization (lowercase, stripping whitespaces)
        df_exploded['Technologia_Pojedyncza'] = df_exploded['Technologia_Pojedyncza'].str.strip().str.lower()
        
        # Filter out rows where technology is missing or marked as "brak danych"
        df_exploded = df_exploded[df_exploded['Technologia_Pojedyncza'] != "brak danych"]

        # Filter out generic tags using the class constant
        df_exploded = df_exploded[~df_exploded['Technologia_Pojedyncza'].isin(self.GENERIC_TECHNOLOGY_TAGS)]
        
        return df_exploded
    
    def _calculate_salary_transparency_percent(self, salary_series: pd.Series) -> float:
        """
        Calculate percentage of non-null salary values.
        
        Args:
            salary_series: Series of salary values
            
        Returns:
            Percentage of non-null values (0-100), rounded to 1 decimal
        """
        return ((salary_series.notna().sum() / len(salary_series)) * 100).round(1)
    
    def _aggregate_niche_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate job data by technology to calculate niche metrics.
        
        Metrics calculated:
        - Number of job offers (total)
        - Median salary (from real data only, excluding missing values)
        - Average time on market
        - Percentage of offers with real salary information
        
        Args:
            df: DataFrame with exploded technologies
            
        Returns:
            DataFrame with aggregated metrics per technology
        """
        return df.groupby('Technologia_Pojedyncza').agg(
            Liczba_Ofert=('ID', 'count'),
            Mediana_Zarobkow=('Srednia_Kwota', lambda x: x.dropna().median() if x.notna().any() else None),
            Sredni_Czas_Zatrudnienia=('Czas_Na_Rynku_Dni', 'mean'),
            Procent_Ofert_Z_Widelkami=('Ma_Realne_Wynagrodzenie', lambda x: (x.sum() / len(x) * 100).round(1))
        ).reset_index()
    
    def _filter_viable_niches(self, df: pd.DataFrame, min_jobs: int, max_jobs: int) -> pd.DataFrame:
        """
        Filter technologies to identify viable "Blue Ocean" niches.
        
        Filtering criteria:
        - Job count between min_jobs and max_jobs (market relevance without saturation)
        - Salary transparency above minimum threshold
        
        Args:
            df: DataFrame with aggregated niche metrics
            min_jobs: Minimum number of job offers
            max_jobs: Maximum number of job offers
            
        Returns:
            Filtered and sorted DataFrame of viable niches
        """
        return df[
            (df['Liczba_Ofert'] >= min_jobs) &
            (df['Liczba_Ofert'] <= max_jobs) &
            (df['Procent_Ofert_Z_Widelkami'] >= self.MIN_SALARY_TRANSPARENCY_PERCENT)
        ].sort_values(
            by=['Mediana_Zarobkow', 'Procent_Ofert_Z_Widelkami', 'Sredni_Czas_Zatrudnienia'],
            ascending=[False, False, True]
        )


    def get_blue_ocean_niches(self, min_jobs: int = 15, max_jobs: int = 70) -> pd.DataFrame:
        """
        Fetches data from the database and performs analysis to find "Blue Ocean" niches.
        Uses median imputation for missing salaries and calculates the market exposure time
        of job postings.
        
        Args:
            min_jobs: Minimum number of job offers for a technology to be considered market-relevant.
            max_jobs: Maximum number of job offers above which the market is considered saturated.
            
        Returns:
            pd.DataFrame: A summary of potential niches with the following columns:
                - Technologia_Pojedyncza: Technology name
                - Liczba_Ofert: Number of job offers
                - Mediana_Zarobkow: Median salary
                - Sredni_Czas_Zatrudnienia: Average time on market (days)
                - Procent_Ofert_Z_Widelkami: Percentage of offers with salary ranges (0-100)
                
            Results are filtered to include only technologies with:
                - At least 10% of offers having salary information (salary transparency threshold)
                - Job count between min_jobs and max_jobs
                
            Sorted by: Median salary (desc), Salary transparency % (desc), Time on market (asc)
        """
        # Fetch data as a list of dictionaries using the existing method
        jobs_data = self.get_all_jobs()
        
        if not jobs_data:
            return pd.DataFrame()  # Return an empty DataFrame if the database is empty

        # Process data through the refactored pipeline
        df = pd.DataFrame(jobs_data)
        df = self._deduplicate_jobs(df)
        df = self._prepare_salary_data(df)
        df = self._calculate_market_time(df)
        df_exploded = self._explode_technologies(df)
        niche_analysis = self._aggregate_niche_metrics(df_exploded)
        
        return self._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
    
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