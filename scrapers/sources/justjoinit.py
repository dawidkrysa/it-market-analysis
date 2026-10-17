import logging
from datetime import datetime
from typing import Any

import requests

from .base import BaseScraper

logger = logging.getLogger(__name__)


class JustJoinIT(BaseScraper):
    API_URL = "https://justjoin.it/api/candidate-api/offers"

    def __init__(self) -> None:
        """Initializes the JustJoinIT scraper."""
        super().__init__(source_name="justjoinit")

    def fetch_raw_data(self, experience_levels: str = "junior") -> list[dict[str, Any]]:
        """
        Fetches raw job data from the JustJoin.it API.

        Args:
            experience_levels: Comma-separated experience levels to filter by (default: "junior")

        Returns:
            List of raw job data dictionaries.
        """
        levels = [lvl.strip() for lvl in experience_levels.split(",") if lvl.strip()]
        # One paginated pass per level: the API caps a single result set at 10 000
        # items, and the "from" cursor walks through it page by page.
        offers: list[dict[str, Any]] = []
        for level in levels:
            cursor: int | None = 0
            while cursor is not None:
                params = {"experienceLevels": level, "itemsCount": 100, "from": cursor}
                logger.info(f"Fetching jobs from {self.API_URL} ({level}, from={cursor})")
                response = requests.get(self.API_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                page = data.get("data", [])
                offers.extend(page)
                cursor = data.get("meta", {}).get("next", {}).get("cursor")
                if not page:
                    break
        logger.info(f"Received {len(offers)} job offers from API")
        return offers

    def parse_data(self, raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parses the raw job data from JustJoin.it into a standardized format.

        Args:
            raw_data: List of raw job data dictionaries.

        Returns:
            List of parsed job data dictionaries.
        """
        parsed_jobs = []
        for offer in raw_data:
            try:
                parsed_jobs.extend(self._parse_single_offer(offer))
            except Exception as e:
                logger.warning(f"Error parsing offer {offer.get('slug')}: {e}")
        return parsed_jobs

    def _parse_single_offer(self, offer: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parses a single job offer from JustJoin.it into the standardized format.

        Args:
            offer: Raw job offer dictionary from the API.

        Returns:
            List with one parsed job dictionary (first listed location).
        """
        base_slug = offer.get("slug", "")
        if not base_slug:
            return []

        # Seniority
        seniority = offer.get("experienceLevel", "Junior").strip().upper()

        # Dates. "publishedAt" is the latest refresh ("bump") of the ad, while
        # "lastPublishedAt" holds the earlier original publication - so the posting's
        # age is measured from the earlier of the two.
        dates = [
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            for value in (offer.get("publishedAt"), offer.get("lastPublishedAt"))
            if value
        ]
        utworzono = min(dates) if dates else datetime.now()
        zaktualizowano = max(dates) if dates else utworzono

        # Technologies
        required_skills = offer.get("requiredSkills", [])
        tech_str = ", ".join([s.get("name", "") for s in required_skills if s.get("name")])

        # Salaries. An offer can list several contract variants at once (e.g. both
        # B2B and UoP); only the original (non currency-converted) entries are used,
        # and each is routed by its native rate unit: hourly -> godzinowe bucket,
        # gross -> UoP bucket, net -> B2B bucket.
        currency = "PLN"
        wynagrodzenie_uop_od = wynagrodzenie_uop_do = None
        wynagrodzenie_b2b_od = wynagrodzenie_b2b_do = None
        wynagrodzenie_godzinowe_od = wynagrodzenie_godzinowe_do = None
        for emp in offer.get("employmentTypes", []):
            # Only original PLN figures: other currencies would skew PLN medians.
            if emp.get("currencySource") != "original" or emp.get("currency") != "PLN":
                continue
            unit = (emp.get("unit") or "").strip().lower()
            if unit in ("hour", "month"):
                # Native rate in its own unit.
                amount_from, amount_to = emp.get("fromPerUnit"), emp.get("toPerUnit")
            else:
                # Daily/yearly rates: "from"/"to" already hold the monthly equivalent,
                # so they land in the monthly buckets in the right unit.
                amount_from, amount_to = emp.get("from"), emp.get("to")
            if amount_from is None and amount_to is None:
                continue
            currency = emp.get("currency", currency)
            if unit == "hour":
                if wynagrodzenie_godzinowe_od is None and wynagrodzenie_godzinowe_do is None:
                    wynagrodzenie_godzinowe_od, wynagrodzenie_godzinowe_do = amount_from, amount_to
            elif emp.get("gross"):
                if wynagrodzenie_uop_od is None and wynagrodzenie_uop_do is None:
                    wynagrodzenie_uop_od, wynagrodzenie_uop_do = amount_from, amount_to
            else:
                if wynagrodzenie_b2b_od is None and wynagrodzenie_b2b_do is None:
                    wynagrodzenie_b2b_od, wynagrodzenie_b2b_do = amount_from, amount_to

        results = []
        # Salary and technologies are identical for every city an offer lists, so
        # keep only the first location: one row per offer, not per city.
        locations = offer.get(
            "locations", [{"city": offer.get("city", "Nieznana"), "slug": base_slug}]
        )[:1]

        for loc in locations:
            results.append(
                {
                    "ID": loc.get("slug", base_slug),
                    "Stanowisko": offer.get("title", "Brak tytułu"),
                    "Firma": offer.get("companyName", "Nieznana firma"),
                    "Poziom": seniority,
                    "Kategoria": offer.get("category", {}).get("key", ""),
                    "Technologie": tech_str,
                    "Lokalizacja": loc.get("city", "Nieznana"),
                    "Wynagrodzenie UoP Od": wynagrodzenie_uop_od,
                    "Wynagrodzenie UoP Do": wynagrodzenie_uop_do,
                    "Wynagrodzenie B2B Od": wynagrodzenie_b2b_od,
                    "Wynagrodzenie B2B Do": wynagrodzenie_b2b_do,
                    "Wynagrodzenie Godzinowe Od": wynagrodzenie_godzinowe_od,
                    "Wynagrodzenie Godzinowe Do": wynagrodzenie_godzinowe_do,
                    "Waluta": currency,
                    "Utworzono": utworzono,
                    "Zaktualizowano": zaktualizowano,
                    "Source": self.source_name,
                }
            )
        return results
