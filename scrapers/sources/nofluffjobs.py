import logging
from datetime import datetime
from typing import Any

import requests

from .base import BaseScraper

logger = logging.getLogger(__name__)


class NoFluffJobs(BaseScraper):
    API_URL = "https://nofluffjobs.com/api/search/posting"
    HEADERS = {
        "Content-Type": "application/infiniteSearch+json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        ),
    }

    def __init__(self) -> None:
        """Initializes the NoFluffJobs scraper."""
        super().__init__(source_name="nofluffjobs")

    def fetch_raw_data(self, experience_levels: str = "junior") -> list[dict[str, Any]]:
        """
        Fetches raw job data from the NoFluffJobs API.

        Args:
            experience_levels: Comma-separated experience levels to filter by (default: "junior")

        Returns:
            List of raw job data dictionaries.
        """
        payload = {
            "criteria": f"category=sys-administrator,business-analyst,architecture,backend,data,ux,devops,erp,embedded,frontend,fullstack,game-dev,mobile,project-manager,security,support,testing,other seniority={experience_levels}",
            "url": {"searchParam": "artificial-intelligence"},
            "rawSearch": f"artificial-intelligence category=sys-administrator,business-analyst,architecture,backend,data,ux,devops,erp,embedded,frontend,fullstack,game-dev,mobile,project-manager,security,support,testing,other seniority={experience_levels} ",
            "withSalaryMatch": True,
        }

        counter = 1
        all_offers = []

        while True:
            params = {
                "withSalaryMatch": "true",
                "pageTo": counter,
                "pageSize": 1000,
                "salaryCurrency": "PLN",
                "salaryPeriod": "month",
                "region": "pl",
                "language": "pl-PL",
            }
            logger.info(f"Fetching jobs from {self.API_URL}")

            response = requests.post(
                self.API_URL, headers=self.HEADERS, params=params, json=payload, timeout=30
            )

            response.raise_for_status()
            data = response.json()

            offers = data.get("postings", [])
            all_offers.extend(offers)
            logger.info(f"Received {len(offers)} job offers from API (page {counter})")

            counter += 1
            if counter >= data.get("totalPages", 1):
                break

        logger.info(f"Received {len(all_offers)} job offers from API (all pages)")
        return all_offers

    def parse_data(self, raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parses the raw job data from NoFluffJobs into a standardized format.

        Args:
            raw_data: List of raw job data dictionaries.
        """

        parsed_jobs = []
        # The search API returns the same offer once per region (e.g. "...-lodz",
        # "...-lublin"), all sharing one "reference": keep a single copy.
        seen_references: set[str] = set()
        for offer in raw_data:
            reference = offer.get("reference")
            if reference:
                if reference in seen_references:
                    continue
                seen_references.add(reference)
            try:
                parsed_jobs.extend(self._parse_single_offer(offer))
            except Exception as e:
                logger.warning(f"Error parsing offer {offer.get('id')}: {e}")

        return parsed_jobs

    def _parse_single_offer(self, offer: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parses a single job offer from NoFluffJobs into the standardized format.

        Args:
            offer: Raw job offer dictionary from the API.

        Returns:
            Parsed job dictionary in the standardized format.

        """
        # Seniority
        seniority = offer.get("seniority", ["Junior"])[0].strip().upper()

        # Dates
        published_at = offer.get("posted")
        utworzono = datetime.fromtimestamp(published_at / 1000) if published_at else datetime.now()

        renewed_at = offer.get("renewed")
        renewed_at = datetime.fromtimestamp(renewed_at / 1000) if renewed_at else datetime.now()

        # Technologies
        tech_str = ", ".join(
            [
                t.get("value", "")
                for t in offer.get("tiles", {}).get("values", [])
                if t.get("type") == "requirement"
            ]
        )

        # Salaries. NoFluffJobs exposes one salary range per offer, tagged with a
        # contract "type". Its search API only ever reports monthly figures (no
        # hourly rates), so the hourly bucket is always left empty for this source.
        # "zlecenie" (mandate contracts) are quoted gross like UoP by convention.
        salary_info = offer.get("salary", {}) or {}
        amount_from = salary_info.get("from")
        amount_to = salary_info.get("to")
        currency = salary_info.get("currency", "PLN")

        wynagrodzenie_uop_od = wynagrodzenie_uop_do = None
        wynagrodzenie_b2b_od = wynagrodzenie_b2b_do = None
        if amount_from is not None or amount_to is not None:
            if salary_info.get("type") == "b2b":
                wynagrodzenie_b2b_od, wynagrodzenie_b2b_do = amount_from, amount_to
            else:
                wynagrodzenie_uop_od, wynagrodzenie_uop_do = amount_from, amount_to

        # Locations
        results = []
        # Salary and technologies are identical for every city an offer lists, so
        # keep only the first usable location: one row per offer, not per city.
        locations = [
            loc for loc in offer.get("location", {}).get("places", []) if loc.get("url")
        ][:1]

        for loc in locations:
            base_slug = loc.get("url", "")
            if not base_slug:
                continue
            results.append(
                {
                    # Stable across runs (the regional copy kept first can vary).
                    "ID": f"nfj-{offer['reference']}" if offer.get("reference") else base_slug,
                    "Stanowisko": offer.get("title", ""),
                    "Firma": offer.get("name", ""),
                    "Poziom": seniority,
                    "Kategoria": offer.get("category", ""),
                    "Technologie": tech_str,
                    "Lokalizacja": loc.get("city", "Nieznana"),
                    "Wynagrodzenie UoP Od": wynagrodzenie_uop_od,
                    "Wynagrodzenie UoP Do": wynagrodzenie_uop_do,
                    "Wynagrodzenie B2B Od": wynagrodzenie_b2b_od,
                    "Wynagrodzenie B2B Do": wynagrodzenie_b2b_do,
                    "Wynagrodzenie Godzinowe Od": None,
                    "Wynagrodzenie Godzinowe Do": None,
                    "Waluta": currency,
                    "Utworzono": utworzono,
                    "Zaktualizowano": renewed_at,
                    "Source": self.source_name,
                }
            )

        return results
