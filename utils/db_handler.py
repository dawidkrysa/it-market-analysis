"""
Database handler for job postings using SQLAlchemy ORM.

This module provides the necessary models and database operations
to save, retrieve, clean, and analyze job market data.
"""

from sqlalchemy import Engine, create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from typing import Any, Tuple, List
import pandas as pd
import re
import streamlit as st

from sqlalchemy.orm.session import Session
from config.settings import Settings

import enum
from sqlalchemy import Enum as SQLEnum

Base = declarative_base()

class SeniorityLevel(enum.Enum):
    """Enumeration for job seniority levels."""
    TRAINEE = "TRAINEE"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"

class Currency(enum.Enum):
    """Enumeration for supported currencies."""
    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"

class Source(enum.Enum):
    """Enumeration for data scraping sources."""
    JUSTJOINIT = "JUSTJOINIT"
    NOFLUFFJOBS = "NOFLUFFJOBS"
    THEPROTOCOLIT = "THEPROTOCOLIT"
    MANUAL = "MANUAL"

class JobPosting(Base):
    """
    SQLAlchemy model representing a single job posting.

    Attributes:
        id: Unique job identifier.
        group_id: Group identifier for related jobs.
        stanowisko: Job title/position.
        firma: Company name.
        poziom: Seniority level (Trainee, Junior, Mid, Senior).
        kategoria: Job category.
        technologie: Required technologies (comma-separated string).
        lokalizacja: Job location.
        wynagrodzenie_od: Minimum salary boundary.
        wynagrodzenie_do: Maximum salary boundary.
        waluta: Currency (e.g., PLN, EUR, USD).
        utworzono: Date the job posting was created on the source portal.
        zaktualizowano: Date the job posting was last updated.
        scraped_at: Timestamp indicating when the data was scraped.
        data_pobrania: Local timestamp of database insertion.
        source: Source portal of the job posting.
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

    Manages the SQLAlchemy engine, sessions, CRUD operations,
    and data processing for market analysis.
    """

    # Minimum percentage of offers with salary information required to consider a niche valid
    MIN_SALARY_TRANSPARENCY_PERCENT: float = 10.0

    # Generic tags that do not represent specific IT technologies, used for filtering
    GENERIC_TECHNOLOGY_TAGS: frozenset[str] = frozenset([
        # Missing data
        'brak danych',

        # Working modes and conditions
        'gotowość do pracy zmianowej', 'praca zdalna', 'praca hybrydowa',
        'praca stacjonarna', 'elastyczne godziny pracy',

        # Foreign languages and soft skills
        'english', 'angielski', 'french', 'communication', 'team player',
        'negotiations skills', 'communication skills', 'analytical thinking',
        'analytical skills', 'problem solving', 'tech-savvy', 'zaangażowanie',
        'zdolności analityczne', 'ai interest',

        # Tools and methodologies (considered generic for this algorithm)
        'agile', 'scrum', 'git', 'jira', 'confluence', 'devops', 'docker',
        'kubernetes', 'ci/cd', 'itil', 'project management', 'agile project management',

        # Office and non-technical skills
        'accounting', 'financial accounting', 'excel', 'ms excel', 'ms office',
        'office 365', 'microsoft office', 'powerpoint', 'ms project', 'rysunek techniczny',

        # Other domains and business roles
        'recruitment', 'tutoring', 'business analysis', 'business development',
        'customer support', 'helpdesk', 'customer experience (cx)', 'finance',
        'finanse', 'procurement', 'supply chain', 'ilustracja', 'grafika', 'pmo',

        # Broad IT buzzwords
        'pc hardware skills', 'znajomość systemów it', 'data visualization',
        'cloud computing', 'cloud', 'it support', 'it', 'it basics', 'security',
        'cybersecurity', 'programming', 'bazy danych', 'networking', 'network',
        'data', 'hardware', 'os', 'algorithms', 'math', 'matematyka',

        # Testing and engineering concepts (too generic)
        'skalowalny kod', 'software testing concept', 'testing theory', 'testing',
        'manual testing', 'qa', 'automated testing', 'engineering principles', 'database design'
    ])

    def __init__(self, database_url: str = Settings.DATABASE_URL) -> None:
        """
        Initialize the database handler.

        Args:
            database_url (str): SQLAlchemy database URL (defaults to Settings configuration).
        """
        self.engine: Engine = create_engine(database_url)
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all database tables defined by SQLAlchemy models if they do not exist."""
        Base.metadata.create_all(self.engine)

    def save_jobs(self, jobs_data: List[dict[str, Any]]) -> int:
        """
        Save or update job postings in the database.

        Utilizes the 'merge' operation to handle both inserts of new jobs
        and updates of existing jobs based on the primary key (job ID).

        Args:
            jobs_data (List[dict[str, Any]]): List of job dictionaries with required fields.

        Returns:
            int: The number of job records successfully processed.

        Raises:
            Exception: If the database transaction fails.
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
        Irreversibly delete all job postings from the database.

        Returns:
            int: The number of deleted records.

        Raises:
            Exception: If the database transaction fails.
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
        Retrieve the total number of job postings currently stored.

        Returns:
            int: Total record count in the database.
        """
        session: Session = self.Session()
        try:
            return session.query(JobPosting).count()
        finally:
            session.close()

    def get_all_jobs(self) -> List[dict[str, Any]]:
        """
        Retrieve all job postings from the database and format them as dictionaries.

        Returns:
            List[dict[str, Any]]: A list of dictionaries representing the job postings.
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

    @staticmethod
    @st.cache_data(ttl=3600)  # ttl=3600 refreshes the cache every hour
    def get_cached_market_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Fetch, process, and cache complete market data analysis pipelines.

        Executes deduplication, salary preparation, market time calculation,
        and niche aggregation.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                - df_raw: The base, cleaned DataFrame.
                - df_exploded: DataFrame with technologies separated into individual rows.
                - niche_analysis: Aggregated metrics per individual technology.
        """
        db = DatabaseHandler()
        raw_jobs = db.get_all_jobs()
        if not raw_jobs:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df_raw = pd.DataFrame(raw_jobs)
        df_raw = db._deduplicate_jobs(df_raw)
        df_raw = db._prepare_salary_data(df_raw)
        df_raw = db._calculate_market_time(df_raw)
        df_exploded = db._explode_technologies(df_raw.copy())
        niche_analysis = db._aggregate_niche_metrics(df_exploded)

        return df_raw, df_exploded, niche_analysis

    def _deduplicate_jobs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate job postings based on normalized company name and core attributes.

        Args:
            df (pd.DataFrame): DataFrame containing raw job postings.

        Returns:
            pd.DataFrame: Deduplicated DataFrame.
        """
        df['Firma_Znormalizowana'] = df['Firma'].apply(self.__normalize_company_name)

        df = df.drop_duplicates(
            subset=['Firma_Znormalizowana', 'Stanowisko', 'Technologie', 'Wynagrodzenie Od', 'Wynagrodzenie Do'],
            keep='first'
        )

        # Drop the temporary normalization column to keep the DataFrame clean
        return df.drop(columns=['Firma_Znormalizowana'])

    def _prepare_salary_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare salary data for analysis (without median imputation).

        Process steps:
        1. Fill missing currencies with "PLN".
        2. Cast salary columns to numeric types.
        3. Standardize hourly rates (<1000) to monthly salaries.
        4. Calculate the average salary only for postings with complete bounds.

        Args:
            df (pd.DataFrame): DataFrame containing job postings.

        Returns:
            pd.DataFrame: DataFrame with sanitized salary data and tracking flags.
        """
        # Fill missing currency with "PLN" if the column exists
        if 'Waluta' in df.columns:
            df['Waluta'] = df['Waluta'].fillna("PLN")

        # Convert to numeric, coercing unparseable strings to NaN
        df['Wynagrodzenie Od'] = pd.to_numeric(df['Wynagrodzenie Od'], errors='coerce')
        df['Wynagrodzenie Do'] = pd.to_numeric(df['Wynagrodzenie Do'], errors='coerce')

        # Convert outliers (assumed to be hourly rates) to a standard monthly salary
        df.loc[df["Wynagrodzenie Od"] < 1000, "Wynagrodzenie Od"] *= 168
        df.loc[df["Wynagrodzenie Do"] < 1000, "Wynagrodzenie Do"] *= 168

        # Track rows that have real, explicitly stated salary boundaries
        df['Ma_Realne_Wynagrodzenie'] = (
            df['Wynagrodzenie Od'].notna() & df['Wynagrodzenie Do'].notna()
        )

        # Calculate the median/average salary exclusively for valid salary rows
        df['Srednia_Kwota'] = df.apply(
            lambda row: (row['Wynagrodzenie Od'] + row['Wynagrodzenie Do']) / 2
            if row['Ma_Realne_Wynagrodzenie'] else None,
            axis=1
        )

        return df

    def _calculate_market_time(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate the duration each job posting has been active on the market.

        Args:
            df (pd.DataFrame): DataFrame containing job postings.

        Returns:
            pd.DataFrame: DataFrame augmented with a 'Czas_Na_Rynku_Dni' column.
        """
        df['Utworzono'] = pd.to_datetime(df['Utworzono'], utc=True)
        df['Scraped At'] = pd.to_datetime(df['Scraped At'], utc=True)

        # Calculate timedelta in days (missing dates will yield NaN)
        df['Czas_Na_Rynku_Dni'] = (df['Scraped At'] - df['Utworzono']).dt.days

        return df

    def _explode_technologies(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Tokenize and flatten the comma-separated technology strings into individual rows.

        Process steps:
        1. Split technology strings by commas.
        2. Explode the lists so each technology gets its own DataFrame row.
        3. Normalize text (convert to lowercase, trim whitespaces).
        4. Filter out generic or meaningless tags using predefined sets.

        Args:
            df (pd.DataFrame): DataFrame containing grouped job postings.

        Returns:
            pd.DataFrame: A normalized DataFrame with one technology per row.
        """
        df_tech = df.dropna(subset=['Technologie']).copy()

        # Split string representations into Python lists
        df_tech['Technologia_Pojedyncza'] = df_tech['Technologie'].astype(str).str.split(',')

        # Flatten the dataset based on the generated lists
        df_exploded = df_tech.explode('Technologia_Pojedyncza')

        # Standardize formatting
        df_exploded['Technologia_Pojedyncza'] = df_exploded['Technologia_Pojedyncza'].str.strip().str.lower()

        # Exclude edge cases indicating missing data
        df_exploded = df_exploded[df_exploded['Technologia_Pojedyncza'] != "brak danych"]

        # Drop non-technical tags defined in the class constant
        df_exploded = df_exploded[~df_exploded['Technologia_Pojedyncza'].isin(self.GENERIC_TECHNOLOGY_TAGS)]

        return df_exploded

    def _calculate_salary_transparency_percent(self, salary_series: pd.Series) -> float:
        """
        Calculate the percentage of valid, non-null values within a salary series.

        Args:
            salary_series (pd.Series): The pandas Series containing numerical salary data.

        Returns:
            float: The percentage of valid values (0.0 to 100.0), rounded to one decimal place.
        """
        return ((salary_series.notna().sum() / len(salary_series)) * 100).round(1)

    def _aggregate_niche_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate job data grouping by specific technologies to calculate niche KPIs.

        Calculated KPIs include:
        - Total volume of offers.
        - Median salary (derived strictly from explicitly stated salary bands).
        - Average market exposure time.
        - Percentage of offers providing transparent salary data.

        Args:
            df (pd.DataFrame): Exploded DataFrame containing individualized technologies.

        Returns:
            pd.DataFrame: Aggregated DataFrame grouped by technology.
        """
        return df.groupby('Technologia_Pojedyncza').agg(
            Liczba_Ofert=('ID', 'count'),
            Mediana_Zarobkow=('Srednia_Kwota', lambda x: x.dropna().median() if x.notna().any() else None),
            Sredni_Czas_Zatrudnienia=('Czas_Na_Rynku_Dni', 'mean'),
            Procent_Ofert_Z_Widelkami=('Ma_Realne_Wynagrodzenie', lambda x: (x.sum() / len(x) * 100).round(1))
        ).reset_index()

    def _filter_viable_niches(self, df: pd.DataFrame, min_jobs: int, max_jobs: int) -> pd.DataFrame:
        """
        Filter aggregated technology metrics to isolate viable 'Blue Ocean' niches.

        Args:
            df (pd.DataFrame): DataFrame containing aggregated niche metrics.
            min_jobs (int): Minimum threshold for total job postings (ensures market relevance).
            max_jobs (int): Maximum threshold for total job postings (avoids saturated markets).

        Returns:
            pd.DataFrame: Filtered DataFrame sorted by profitability and data transparency.
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
        Fetch database records and execute the complete 'Blue Ocean' niche discovery pipeline.

        Args:
            min_jobs (int): Minimum number of job offers to be considered a viable niche.
            max_jobs (int): Maximum number of job offers to avoid saturated 'Red Oceans'.

        Returns:
            pd.DataFrame: Summarized metrics of potential niches, containing:
                - Technologia_Pojedyncza: Single technology identifier.
                - Liczba_Ofert: Total volume of associated postings.
                - Mediana_Zarobkow: Calculated median salary.
                - Sredni_Czas_Zatrudnienia: Average posting age (in days).
                - Procent_Ofert_Z_Widelkami: Salary transparency metric (0-100%).
        """
        jobs_data = self.get_all_jobs()

        if not jobs_data:
            return pd.DataFrame()

        # Route the raw dictionary list through the data transformation pipeline
        df = pd.DataFrame(jobs_data)
        df = self._deduplicate_jobs(df)
        df = self._prepare_salary_data(df)
        df = self._calculate_market_time(df)
        df_exploded = self._explode_technologies(df)
        niche_analysis = self._aggregate_niche_metrics(df_exploded)

        return self._filter_viable_niches(niche_analysis, min_jobs, max_jobs)

    def __normalize_company_name(self, name: str) -> str:
        """
        Standardize and clean corporate names for accurate deduplication.

        Strips legal entities, punctuation, and extraneous whitespace.

        Args:
            name (str): Raw company name.

        Returns:
            str: Normalized company name string.
        """
        if pd.isna(name) or name == "Brak danych":
            return "nieznana"

        name = str(name).lower()

        # 1. Define regular expressions for corporate entity identifiers (longest to shortest)
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

        # 2. Iterate and strip out identified corporate legal forms
        for form in legal_forms:
            # Substitute matching patterns with spaces, treating Polish diacritics natively
            name = re.sub(form, ' ', name)

        # 3. Strip punctuation characters (e.g., quotations surrounding brand names)
        name = re.sub(r'[^\w\s]', ' ', name)

        # 4. Collapse multiple spaces into a single space and trim edges
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name