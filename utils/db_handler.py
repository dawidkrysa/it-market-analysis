"""
Database handler for job postings using SQLAlchemy ORM.

This module provides the necessary models and database operations
to save, retrieve, clean, and analyze job market data.
"""

import enum
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import Column, DateTime, Engine, Float, Integer, String, Text, create_engine
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.pool import NullPool

from config.settings import Settings

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
        wynagrodzenie_uop_od: Minimum gross monthly salary for an employment contract (UoP).
        wynagrodzenie_uop_do: Maximum gross monthly salary for an employment contract (UoP).
        wynagrodzenie_b2b_od: Minimum net monthly rate for a B2B contract.
        wynagrodzenie_b2b_do: Maximum net monthly rate for a B2B contract.
        wynagrodzenie_godzinowe_od: Minimum hourly rate, regardless of contract form.
        wynagrodzenie_godzinowe_do: Maximum hourly rate, regardless of contract form.
        waluta: Currency (e.g., PLN, EUR, USD).
        utworzono: Date the job posting was created on the source portal.
        zaktualizowano: Date the job posting was last updated.
        scraped_at: Timestamp indicating when the data was scraped.
        data_pobrania: Local timestamp of database insertion.
        source: Source portal of the job posting.
    """

    __tablename__: str = "job_postings"

    id = Column(String, primary_key=True)
    group_id = Column(String)
    stanowisko = Column(Text)
    firma = Column(Text)
    poziom = Column(SQLEnum(SeniorityLevel), nullable=True)
    kategoria = Column(Text)
    technologie = Column(Text)
    lokalizacja = Column(Text)
    wynagrodzenie_uop_od = Column(Integer, nullable=True)
    wynagrodzenie_uop_do = Column(Integer, nullable=True)
    wynagrodzenie_b2b_od = Column(Integer, nullable=True)
    wynagrodzenie_b2b_do = Column(Integer, nullable=True)
    wynagrodzenie_godzinowe_od = Column(Integer, nullable=True)
    wynagrodzenie_godzinowe_do = Column(Integer, nullable=True)
    waluta = Column(SQLEnum(Currency), nullable=True)
    utworzono = Column(DateTime)
    zaktualizowano = Column(DateTime)
    # Callables, so the timestamp is taken per insert, not once at import time.
    scraped_at = Column(DateTime, default=lambda: datetime.now(UTC))
    data_pobrania = Column(DateTime, default=lambda: datetime.now(UTC))
    source = Column(SQLEnum(Source), nullable=True)


class Bootcamp(Base):
    """
    SQLAlchemy model representing aggregated bootcamp cost/duration stats per technology.

    Attributes:
        id: Auto-incrementing row identifier.
        technologia: Technology the bootcamp teaches (e.g. "aws", "java").
        sredni_koszt: Average bootcamp price (PLN).
        mediana_kosztu: Median bootcamp price (PLN).
        sredni_czas_dni: Average bootcamp duration (days).
        mediana_czasu_dni: Median bootcamp duration (days).
    """

    __tablename__: str = "bootcamp_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    technologia = Column(Text, nullable=False)
    sredni_koszt = Column(Float, nullable=True)
    mediana_kosztu = Column(Float, nullable=True)
    sredni_czas_dni = Column(Float, nullable=True)
    mediana_czasu_dni = Column(Float, nullable=True)


class ScrapeRun(Base):
    """
    SQLAlchemy model recording one scraping run (scheduled or manual).

    Attributes:
        id: Auto-incrementing run identifier.
        trigger: "auto" (scheduler) or "manual" (admin panel).
        experience_levels: Comma-separated levels requested in this run.
        started_at: UTC timestamp when the run started.
        finished_at: UTC timestamp when the run ended (NULL while running).
        status: "running", "success" or "failed".
        saved_count: Number of job postings saved by the run.
        error: Error message for failed runs.
    """

    __tablename__: str = "scrape_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(Text, nullable=False)
    experience_levels = Column(Text, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False)
    saved_count = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)


def __normalize_company_name(name: str) -> str:
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
        r"spółka z ograniczoną odpowiedzialnością",
        r"oddział w polsce",
        r"prosta spółka akcyjna",
        r"spółka akcyjna",
        r"spółka komandytowa",
        r"spółka jawna",
        r"sp\.?\s*z\s*o\.?\s*o\.?\s*sp\.?\s*k\.?",  # sp. z o.o. sp. k.
        r"sp\.?\s*z\s*o\.?\s*o\.?",  # sp. z o.o. / sp z o o
        r"sp\.?\s*k\.?",  # sp. k.
        r"p\.?\s*s\.?\s*a\.?",  # p.s.a.
        r"prosta\s+s\.?\s*a\.?",  # prosta s.a.
        r"s\.?\s*a\.?",  # s.a. / sa
        r"s\.?\s*c\.?",  # s.c.
        r"\blimited\b",
        r"\bltd\.?\b",
        r"\bllc\b",
        r"\bgmbh\b",
        r"\bag\b",
        r"\bkft\.?\b",
        r"\bn\.?\s*v\.?\b",
        r"\bvvag\b",
        r"\bgroup\b",
    ]

    # 2. Iterate and strip out identified corporate legal forms
    for form in legal_forms:
        # Substitute matching patterns with spaces, treating Polish diacritics natively
        name = re.sub(form, " ", name)

    # 3. Strip punctuation characters (e.g., quotations surrounding brand names)
    name = re.sub(r"[^\w\s]", " ", name)

    # 4. Collapse multiple spaces into a single space and trim edges
    name = re.sub(r"\s+", " ", name).strip()

    return name


def _aggregate_niche_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate job data grouping by specific technologies to calculate niche KPIs.

    Calculated KPIs include:
    - Total volume of offers.
    - Median salary (derived strictly from explicitly stated salary bands).
    - Relative posting age (median within-portal age percentile).
    - Percentage of offers providing transparent salary data.

    Args:
        df (pd.DataFrame): Exploded DataFrame containing individualized technologies.

    Returns:
        pd.DataFrame: Aggregated DataFrame grouped by technology.
    """
    return (
        df.groupby("Technologia_Pojedyncza")
        .agg(
            Liczba_Ofert=("ID", "count"),
            Mediana_Zarobkow=(
                "Srednia_Kwota",
                lambda x: x.dropna().median() if x.notna().any() else None,
            ),
            # Median within-portal age percentile: 50 = typical, higher = ads stay
            # up longer (proxy for harder to hire). Comparable across portal mixes.
            Wzgledny_Wiek_Ogloszen=("Wzgledny_Wiek_Pct", "median"),
            Procent_Ofert_Z_Widelkami=(
                "Ma_Realne_Wynagrodzenie",
                lambda x: (x.sum() / len(x) * 100).round(1),
            ),
            # n behind the median: offers that actually disclose a salary range
            Liczba_Ofert_Z_Widelkami=("Ma_Realne_Wynagrodzenie", "sum"),
        )
        .reset_index()
    )


def _calculate_market_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the duration each job posting has been active on the market.

    Args:
        df (pd.DataFrame): DataFrame containing job postings.

    Returns:
        pd.DataFrame: DataFrame augmented with 'Czas_Na_Rynku_Dni' (raw age in days)
            and 'Wzgledny_Wiek_Pct' (age percentile within the ad's portal).
    """
    df["Utworzono"] = pd.to_datetime(df["Utworzono"], utc=True)
    df["Scraped At"] = pd.to_datetime(df["Scraped At"], utc=True)

    # Calculate timedelta in days (missing dates will yield NaN)
    df["Czas_Na_Rynku_Dni"] = (df["Scraped At"] - df["Utworzono"]).dt.days

    # Portals date ads differently (NoFluffJobs/TheProtocol re-publish roughly every
    # 30 days with a new date, JustJoinIT keeps the original), so raw days aren't
    # comparable across portals. The age percentile within the ad's own portal is:
    # 50 = a typical ad on that portal, higher = up longer than most.
    df["Wzgledny_Wiek_Pct"] = (
        df.groupby("Source")["Czas_Na_Rynku_Dni"].rank(pct=True).mul(100)
    )

    return df


def _calculate_salary_transparency_percent(salary_series: pd.Series) -> float:
    """
    Calculate the percentage of valid, non-null values within a salary series.

    Args:
        salary_series (pd.Series): The pandas Series containing numerical salary data.

    Returns:
        float: The percentage of valid values (0.0 to 100.0), rounded to one decimal place.
    """
    return ((salary_series.notna().sum() / len(salary_series)) * 100).round(1)


# Maps a user-facing employment-type label to the DataFrame columns holding its
# salary range. "Stawka godzinowa" intentionally pools hourly rates regardless of
# the underlying contract form (B2B-hourly, zlecenie, ...).
SALARY_TYPE_COLUMNS: dict[str, tuple[str, str]] = {
    "UoP (brutto)": ("Wynagrodzenie UoP Od", "Wynagrodzenie UoP Do"),
    "B2B (netto)": ("Wynagrodzenie B2B Od", "Wynagrodzenie B2B Do"),
    "Stawka godzinowa": ("Wynagrodzenie Godzinowe Od", "Wynagrodzenie Godzinowe Do"),
}
DEFAULT_SALARY_TYPE = "UoP (brutto)"

# Columns kept in the cached exploded (offer x technology) frame.
EXPLODED_COLUMNS = [
    "ID",
    "Technologia_Pojedyncza",
    "Srednia_Kwota",
    "Ma_Realne_Wynagrodzenie",
    "Czas_Na_Rynku_Dni",
    "Wzgledny_Wiek_Pct",
    "Source",
    "Poziom",
]

# Plausible salary-range bounds per type (PLN). Values outside them are almost always
# data-entry errors on the portal (e.g. an hourly rate of 70 posted as "monthly"), so
# they are left out of salary statistics instead of skewing the medians.
PLAUSIBLE_SALARY_RANGE: dict[str, tuple[float, float]] = {
    "UoP (brutto)": (1_000, 100_000),
    "B2B (netto)": (1_000, 100_000),
    "Stawka godzinowa": (15, 1_000),
}


def _prepare_salary_data(
    df: pd.DataFrame, typ_wynagrodzenia: str = DEFAULT_SALARY_TYPE
) -> pd.DataFrame:
    """
    Prepare salary data for analysis (without median imputation).

    Resolves the generic "Wynagrodzenie Od"/"Wynagrodzenie Do" columns from the
    type-specific columns matching `typ_wynagrodzenia` (UoP/B2B/hourly), so every
    downstream consumer compares like with like instead of mixing gross UoP,
    net B2B, and hourly figures together.

    Args:
        df (pd.DataFrame): DataFrame containing job postings.
        typ_wynagrodzenia (str): One of the keys in `SALARY_TYPE_COLUMNS`.

    Returns:
        pd.DataFrame: DataFrame with sanitized salary data and tracking flags.
    """
    # Fill missing currency with "PLN" if the column exists
    if "Waluta" in df.columns:
        df["Waluta"] = df["Waluta"].fillna("PLN")

    od_col, do_col = SALARY_TYPE_COLUMNS[typ_wynagrodzenia]

    # Convert to numeric, coercing unparseable strings to NaN
    df["Wynagrodzenie Od"] = pd.to_numeric(df[od_col], errors="coerce")
    df["Wynagrodzenie Do"] = pd.to_numeric(df[do_col], errors="coerce")

    # Drop implausible ranges (see PLAUSIBLE_SALARY_RANGE) for both bounds together.
    low, high = PLAUSIBLE_SALARY_RANGE[typ_wynagrodzenia]
    implausible = ~(
        df["Wynagrodzenie Od"].between(low, high) & df["Wynagrodzenie Do"].between(low, high)
    ) & (df["Wynagrodzenie Od"].notna() | df["Wynagrodzenie Do"].notna())
    df.loc[implausible, ["Wynagrodzenie Od", "Wynagrodzenie Do"]] = float("nan")

    # Track rows that have real, explicitly stated salary boundaries
    df["Ma_Realne_Wynagrodzenie"] = df["Wynagrodzenie Od"].notna() & df["Wynagrodzenie Do"].notna()

    # Calculate the median/average salary exclusively for valid salary rows
    df["Srednia_Kwota"] = df.apply(
        lambda row: (
            (row["Wynagrodzenie Od"] + row["Wynagrodzenie Do"]) / 2
            if row["Ma_Realne_Wynagrodzenie"]
            else None
        ),
        axis=1,
    )

    return df


def _deduplicate_jobs(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate job postings based on normalized company name and core attributes.

    Args:
        df (pd.DataFrame): DataFrame containing raw job postings.

    Returns:
        pd.DataFrame: Deduplicated DataFrame.
    """
    df["Firma_Znormalizowana"] = df["Firma"].apply(__normalize_company_name)

    df = df.drop_duplicates(
        subset=[
            "Firma_Znormalizowana",
            "Stanowisko",
            "Technologie",
            "Wynagrodzenie UoP Od",
            "Wynagrodzenie UoP Do",
            "Wynagrodzenie B2B Od",
            "Wynagrodzenie B2B Do",
            "Wynagrodzenie Godzinowe Od",
            "Wynagrodzenie Godzinowe Do",
        ],
        keep="first",
    )

    # Drop the temporary normalization column to keep the DataFrame clean
    return df.drop(columns=["Firma_Znormalizowana"])


def _optimize_memory(df: pd.DataFrame) -> pd.DataFrame:
    """Converts data types to drastically reduce RAM usage."""
    # Replace columns with duplicate values with 'category'
    categorical_cols = ["poziom", "waluta", "kategoria", "source"]
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")

    # Converting float64 to float32 (saves 50% of memory for numbers)
    for col in [
        "wynagrodzenie_uop_od",
        "wynagrodzenie_uop_do",
        "wynagrodzenie_b2b_od",
        "wynagrodzenie_b2b_do",
        "wynagrodzenie_godzinowe_od",
        "wynagrodzenie_godzinowe_do",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], downcast="float")

    return df


def _to_float_or_none(val: Any) -> float | None:
    """Coerce a data_editor cell value to float, or None if blank/unparseable."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


class DatabaseHandler:
    """
    Handler for database operations related to job postings.

    Manages the SQLAlchemy engine, sessions, CRUD operations,
    and data processing for market analysis.
    """

    # Minimum percentage of offers with salary information required to consider a niche valid
    MIN_SALARY_TRANSPARENCY_PERCENT: float = 10.0

    # Generic tags that do not represent specific IT technologies, used for filtering
    GENERIC_TECHNOLOGY_TAGS: frozenset[str] = frozenset(
        [
            # Missing data
            "brak danych",
            # Working modes and conditions
            "gotowość do pracy zmianowej",
            "praca zdalna",
            "praca hybrydowa",
            "praca stacjonarna",
            "elastyczne godziny pracy",
            # Foreign languages and soft skills
            "english",
            "angielski",
            "french",
            "communication",
            "team player",
            "negotiations skills",
            "communication skills",
            "analytical thinking",
            "analytical skills",
            "problem solving",
            "tech-savvy",
            "zaangażowanie",
            "zdolności analityczne",
            "ai interest",
            # Tools and methodologies (considered generic for this algorithm)
            "agile",
            "scrum",
            "git",
            "jira",
            "confluence",
            "devops",
            "docker",
            "kubernetes",
            "ci/cd",
            "itil",
            "project management",
            "agile project management",
            # Office and non-technical skills
            "accounting",
            "financial accounting",
            "excel",
            "ms excel",
            "ms office",
            "office 365",
            "microsoft office",
            "powerpoint",
            "ms project",
            "rysunek techniczny",
            # Other domains and business roles
            "recruitment",
            "tutoring",
            "business analysis",
            "business development",
            "customer support",
            "helpdesk",
            "customer experience (cx)",
            "finance",
            "finanse",
            "procurement",
            "supply chain",
            "ilustracja",
            "grafika",
            "pmo",
            # Broad IT buzzwords
            "pc hardware skills",
            "znajomość systemów it",
            "data visualization",
            "cloud computing",
            "cloud",
            "it support",
            "it",
            "it basics",
            "security",
            "cybersecurity",
            "programming",
            "bazy danych",
            "networking",
            "network",
            "data",
            "hardware",
            "os",
            "algorithms",
            "math",
            "matematyka",
            # Testing and engineering concepts (too generic)
            "skalowalny kod",
            "software testing concept",
            "testing theory",
            "testing",
            "manual testing",
            "qa",
            "automated testing",
            "engineering principles",
            "database design",
        ]
    )

    def __init__(self, database_url: str = Settings.DATABASE_URL) -> None:
        """
        Initialize the database handler.

        Args:
            database_url (str): SQLAlchemy database URL (defaults to Settings configuration).
        """
        # Pin the driver explicitly: SQLAlchemy >= 2.1 maps bare "postgresql://" to
        # psycopg 3, while this project installs psycopg2 (psycopg2-binary).
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        self.engine: Engine = create_engine(
            database_url,
            # Validate pooled connections, so a DB restart/idle cutoff doesn't surface as errors.
            pool_pre_ping=True,
            **({"poolclass": NullPool} if Settings.DB_NULL_POOL else {}),
        )
        self.Session: sessionmaker[Session] = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Create all database tables defined by SQLAlchemy models if they do not exist."""
        Base.metadata.create_all(self.engine)

    def save_jobs(self, jobs_data: list[dict[str, Any]]) -> int:
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
        now = datetime.now(UTC)
        # A source may list the same offer twice (e.g. overlapping pages); keep the last copy.
        jobs_data = list({job["ID"]: job for job in jobs_data}.values())
        try:
            for job in jobs_data:
                job_posting = JobPosting(
                    id=job["ID"],
                    stanowisko=job["Stanowisko"],
                    firma=job["Firma"],
                    poziom=job["Poziom"],
                    kategoria=job["Kategoria"],
                    technologie=job["Technologie"],
                    lokalizacja=job["Lokalizacja"],
                    wynagrodzenie_uop_od=job["Wynagrodzenie UoP Od"]
                    if job["Wynagrodzenie UoP Od"]
                    else None,  # type: ignore
                    wynagrodzenie_uop_do=job["Wynagrodzenie UoP Do"]
                    if job["Wynagrodzenie UoP Do"]
                    else None,  # type: ignore
                    wynagrodzenie_b2b_od=job["Wynagrodzenie B2B Od"]
                    if job["Wynagrodzenie B2B Od"]
                    else None,  # type: ignore
                    wynagrodzenie_b2b_do=job["Wynagrodzenie B2B Do"]
                    if job["Wynagrodzenie B2B Do"]
                    else None,  # type: ignore
                    wynagrodzenie_godzinowe_od=job["Wynagrodzenie Godzinowe Od"]
                    if job["Wynagrodzenie Godzinowe Od"]
                    else None,  # type: ignore
                    wynagrodzenie_godzinowe_do=job["Wynagrodzenie Godzinowe Do"]
                    if job["Wynagrodzenie Godzinowe Do"]
                    else None,  # type: ignore
                    waluta=job["Waluta"],
                    utworzono=job["Utworzono"],
                    zaktualizowano=job["Zaktualizowano"],
                    data_pobrania=now,
                    # Refreshed on every re-scrape: "age at last observation".
                    scraped_at=now,
                    source=job["Source"].strip().upper() if job.get("Source") else None,
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

    def start_scrape_run(self, trigger: str, experience_levels: str) -> int:
        """
        Record the start of a scraping run.

        Args:
            trigger (str): "auto" (scheduler) or "manual" (admin panel).
            experience_levels (str): Comma-separated levels being scraped.

        Returns:
            int: The new run's ID.
        """
        session: Session = self.Session()
        try:
            run = ScrapeRun(
                trigger=trigger,
                experience_levels=experience_levels,
                started_at=datetime.now(UTC),
                status="running",
            )
            session.add(run)
            session.commit()
            return run.id
        finally:
            session.close()

    def finish_scrape_run(
        self, run_id: int, status: str, saved_count: int | None = None, error: str | None = None
    ) -> None:
        """
        Mark a scraping run as finished.

        Args:
            run_id (int): ID returned by `start_scrape_run`.
            status (str): "success" or "failed".
            saved_count (int | None): Number of saved postings.
            error (str | None): Error message for failed runs.
        """
        session: Session = self.Session()
        try:
            run = session.get(ScrapeRun, run_id)
            if run is not None:
                run.finished_at = datetime.now(UTC)
                run.status = status
                run.saved_count = saved_count
                run.error = error
                session.commit()
        finally:
            session.close()

    def get_last_scrape_run(self, only_success: bool = False) -> dict[str, Any] | None:
        """
        Retrieve the most recently started scraping run.

        Args:
            only_success (bool): Consider only runs that finished successfully.

        Returns:
            dict[str, Any] | None: Run fields (trigger, status, started_at,
                finished_at, saved_count, error), or None if there are no runs.
        """
        session: Session = self.Session()
        try:
            query = session.query(ScrapeRun)
            if only_success:
                query = query.filter(ScrapeRun.status == "success")
            run = query.order_by(ScrapeRun.started_at.desc()).first()
            if run is None:
                return None
            return {
                "trigger": run.trigger,
                "status": run.status,
                "experience_levels": run.experience_levels,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "saved_count": run.saved_count,
                "error": run.error,
            }
        finally:
            session.close()

    def delete_stale_jobs(self, older_than: timedelta) -> int:
        """
        Delete postings that no scrape has seen for longer than `older_than`.

        Args:
            older_than (timedelta): Maximum time since a posting was last observed.

        Returns:
            int: The number of deleted postings.
        """
        cutoff = datetime.now(UTC) - older_than
        session: Session = self.Session()
        try:
            deleted = (
                session.query(JobPosting)
                .filter(JobPosting.scraped_at < cutoff)
                .delete(synchronize_session=False)
            )
            session.commit()
            return deleted
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_bootcamps(self) -> pd.DataFrame:
        """
        Retrieve all bootcamp cost/duration records.

        Returns:
            pd.DataFrame: Bootcamp data with Polish display column names
                (including 'ID'), sorted by technology name.
        """
        df = pd.read_sql("SELECT * FROM bootcamp_data ORDER BY technologia", con=self.engine)
        return df.rename(
            columns={
                "id": "ID",
                "technologia": "Technologia",
                "sredni_koszt": "Średni Koszt",
                "mediana_kosztu": "Mediana Kosztu",
                "sredni_czas_dni": "Średni Czas (dni)",
                "mediana_czasu_dni": "Mediana Czasu (dni)",
            }
        )

    def save_bootcamps(self, df: pd.DataFrame) -> int:
        """
        Replace all bootcamp records with the given DataFrame (full sync).

        Rows with a blank "Technologia" are skipped. Numeric columns are
        coerced to float; unparseable or missing values are stored as NULL.

        Args:
            df (pd.DataFrame): Edited bootcamp data with Polish display column
                names (as returned by `get_bootcamps`), e.g. from a Streamlit
                data editor.

        Returns:
            int: The number of rows saved.

        Raises:
            Exception: If the database transaction fails.
        """
        session: Session = self.Session()
        try:
            session.query(Bootcamp).delete()
            count = 0
            for _, row in df.iterrows():
                technologia = str(row.get("Technologia", "")).strip()
                if not technologia or technologia.lower() == "nan":
                    continue
                session.add(
                    Bootcamp(
                        technologia=technologia,
                        sredni_koszt=_to_float_or_none(row.get("Średni Koszt")),
                        mediana_kosztu=_to_float_or_none(row.get("Mediana Kosztu")),
                        sredni_czas_dni=_to_float_or_none(row.get("Średni Czas (dni)")),
                        mediana_czasu_dni=_to_float_or_none(row.get("Mediana Czasu (dni)")),
                    )
                )
                count += 1
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_all_jobs(self) -> pd.DataFrame:
        """
        Retrieve all job postings from the database and format them as dictionaries.

        Returns:
            DataFrame: A list of dictionaries representing the job postings.
        """
        query = "SELECT * FROM job_postings"
        # Load data directly using the database engine
        df = pd.read_sql(query, con=self.engine)

        rename_mapping = {
            "id": "ID",
            "stanowisko": "Stanowisko",
            "firma": "Firma",
            "poziom": "Poziom",
            "kategoria": "Kategoria",
            "technologie": "Technologie",
            "lokalizacja": "Lokalizacja",
            "wynagrodzenie_uop_od": "Wynagrodzenie UoP Od",
            "wynagrodzenie_uop_do": "Wynagrodzenie UoP Do",
            "wynagrodzenie_b2b_od": "Wynagrodzenie B2B Od",
            "wynagrodzenie_b2b_do": "Wynagrodzenie B2B Do",
            "wynagrodzenie_godzinowe_od": "Wynagrodzenie Godzinowe Od",
            "wynagrodzenie_godzinowe_do": "Wynagrodzenie Godzinowe Do",
            "waluta": "Waluta",
            "utworzono": "Utworzono",
            "zaktualizowano": "Zaktualizowano",
            "scraped_at": "Scraped At",
            "data_pobrania": "Data Pobrania",
            "source": "Source",
        }

        # Rename database columns
        df = df.rename(columns=rename_mapping)

        return df

    @staticmethod
    @st.cache_data(
        ttl=3600, max_entries=len(SALARY_TYPE_COLUMNS), show_spinner=False
    )  # ttl=3600 refreshes the cache every hour
    def get_cached_market_data(
        typ_wynagrodzenia: str = DEFAULT_SALARY_TYPE,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Fetch, process, and cache complete market data analysis pipelines.

        Executes deduplication, salary preparation, market time calculation,
        and niche aggregation.

        Args:
            typ_wynagrodzenia (str): Which salary type to analyze -- one of the
                keys in `SALARY_TYPE_COLUMNS` (UoP/B2B/hourly). Cached separately
                per type.

        Returns:
            Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
                - df_raw: The base, cleaned DataFrame.
                - df_exploded: DataFrame with technologies separated into individual rows.
                - niche_analysis: Aggregated metrics per individual technology.
        """
        db = DatabaseHandler()
        raw_jobs = db.get_all_jobs()
        if raw_jobs.empty:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

        df_raw = pd.DataFrame(raw_jobs)
        df_raw = _deduplicate_jobs(df_raw)
        df_raw = _prepare_salary_data(df_raw, typ_wynagrodzenia)
        df_raw = _calculate_market_time(df_raw)
        df_exploded = db._explode_technologies(df_raw.copy())
        niche_analysis = _aggregate_niche_metrics(df_exploded)

        # Keep only the columns the pages read from the exploded frame: it has one row per
        # (offer, technology) and is cached per salary type, so this cuts memory ~4x.
        df_exploded = df_exploded[EXPLODED_COLUMNS]

        return df_raw, df_exploded, niche_analysis

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
        df_tech = df.dropna(subset=["Technologie"]).copy()

        # Split string representations into Python lists
        df_tech["Technologia_Pojedyncza"] = df_tech["Technologie"].astype(str).str.split(",")

        # Flatten the dataset based on the generated lists
        df_exploded = df_tech.explode("Technologia_Pojedyncza")

        # Standardize formatting
        df_exploded["Technologia_Pojedyncza"] = (
            df_exploded["Technologia_Pojedyncza"].str.strip().str.lower()
        )

        # Exclude edge cases indicating missing data
        df_exploded = df_exploded[
            ~df_exploded["Technologia_Pojedyncza"].isin(["brak danych", ""])
        ]

        # Drop non-technical tags defined in the class constant
        df_exploded = df_exploded[
            ~df_exploded["Technologia_Pojedyncza"].isin(self.GENERIC_TECHNOLOGY_TAGS)
        ]

        # One row per (offer, technology): a tag repeated in one ad ("Python, python")
        # must not count that offer twice.
        return df_exploded.drop_duplicates(subset=["ID", "Technologia_Pojedyncza"])

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
            (df["Liczba_Ofert"] >= min_jobs)
            & (df["Liczba_Ofert"] <= max_jobs)
            & (df["Procent_Ofert_Z_Widelkami"] >= self.MIN_SALARY_TRANSPARENCY_PERCENT)
        ].sort_values(
            by=["Mediana_Zarobkow", "Procent_Ofert_Z_Widelkami", "Wzgledny_Wiek_Ogloszen"],
            ascending=[False, False, True],
        )

    def get_blue_ocean_niches(
        self,
        min_jobs: int = 15,
        max_jobs: int = 70,
        typ_wynagrodzenia: str = DEFAULT_SALARY_TYPE,
    ) -> pd.DataFrame:
        """
        Fetch database records and execute the complete 'Blue Ocean' niche discovery pipeline.

        Args:
            min_jobs (int): Minimum number of job offers to be considered a viable niche.
            max_jobs (int): Maximum number of job offers to avoid saturated 'Red Oceans'.
            typ_wynagrodzenia (str): Which salary type to analyze -- one of the
                keys in `SALARY_TYPE_COLUMNS` (UoP/B2B/hourly).

        Returns:
            pd.DataFrame: Summarized metrics of potential niches, containing:
                - Technologia_Pojedyncza: Single technology identifier.
                - Liczba_Ofert: Total volume of associated postings.
                - Mediana_Zarobkow: Calculated median salary.
                - Wzgledny_Wiek_Ogloszen: Median within-portal posting-age percentile.
                - Procent_Ofert_Z_Widelkami: Salary transparency metric (0-100%).
        """
        jobs_data = self.get_all_jobs()

        if jobs_data.empty:
            return pd.DataFrame()

        # Route the raw dictionary list through the data transformation pipeline
        df = pd.DataFrame(jobs_data)
        df = _deduplicate_jobs(df)
        df = _prepare_salary_data(df, typ_wynagrodzenia)
        df = _calculate_market_time(df)
        df_exploded = self._explode_technologies(df)
        niche_analysis = _aggregate_niche_metrics(df_exploded)

        return self._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
