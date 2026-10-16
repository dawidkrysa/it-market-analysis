import logging
from typing import Any

import requests

from .base import BaseScraper

logger = logging.getLogger(__name__)


class TheProtocolIT(BaseScraper):
    API_URL = "https://theprotocol.it/filtry/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self) -> None:
        """Initializes the TheProtocolIT scraper."""
        super().__init__(source_name="theprotocolit")

    def fetch_raw_data(self, experience_levels: str = "junior") -> list[dict[str, Any]]:
        """
        Fetches raw job data from TheProtocol.it API.

        Args:
            experience_levels: Comma-separated experience levels to filter by (default: "junior").
                TheProtocol.it encodes the level as a URL path segment rather than a query
                param, so each level requires its own paginated request.

        Returns:
            List of raw job data dictionaries.
        """

        import json

        from bs4 import BeautifulSoup

        all_offers = []
        for level in [lvl.strip() for lvl in experience_levels.split(",") if lvl.strip()]:
            counter = 1
            page_count = 1
            first = True
            while counter <= page_count:
                url: str = self.API_URL + f"{level};p" + f"?pageNumber={counter}"
                logger.info(f"Fetching jobs from {url}")
                response = requests.get(url, timeout=30, headers=self.HEADERS)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
                if not script_tag:
                    logger.error("Could not find __NEXT_DATA__ script tag in response")
                    break
                data = json.loads(script_tag.text)
                offers = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("offersResponse", {})
                    .get("offers", [])
                )
                all_offers.extend(offers)
                if first:
                    page_count = (
                        data.get("props", {})
                        .get("pageProps", {})
                        .get("offersResponse", {})
                        .get("page", {})
                        .get("count", 1)
                    )
                    first = False
                counter += 1
        logger.info(f"Received {len(all_offers)} job offers from API (all levels, all pages)")
        return all_offers

    def parse_data(self, raw_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Parses the raw job data from TheProtocol.it into a standardized format.

        Args:
            raw_data: List of raw job data dictionaries.
        """

        parsed_jobs = []
        for offer in raw_data:
            try:
                parsed = self._parse_single_offer(offer)
                # Only add if poziom is allowed (not None)
                if parsed["Poziom"] is not None:
                    parsed_jobs.append(parsed)
            except Exception as e:
                logger.warning(f"Error parsing offer {offer.get('id')}: {e}")
        return parsed_jobs

    def _parse_single_offer(self, offer: dict[str, Any]) -> dict[str, Any]:
        """
        Parses a single job offer from TheProtocol.it into the standardized format.

        Args:
            offer: Raw job offer dictionary.

        Returns:
            Parsed job data dictionary in standardized format.
        """

        # Handle positionLevels (list of dicts)
        position_levels = offer.get("positionLevels", [])
        poziom = None
        if isinstance(position_levels, list) and position_levels:
            first_level = position_levels[0]
            if first_level and hasattr(first_level, "get"):
                poziom = first_level.get("value")
        elif isinstance(position_levels, dict):
            poziom = position_levels.get("value")
        allowed_levels = {"TRAINEE", "JUNIOR", "MID", "SENIOR"}
        if poziom:
            poziom = poziom.strip().upper()
            if poziom not in allowed_levels:
                poziom = None

        workplace = offer.get("workplace", [])
        lokalizacja = None
        if isinstance(workplace, list) and workplace:
            first_workplace = workplace[0]
            if first_workplace and hasattr(first_workplace, "get"):
                lokalizacja = first_workplace.get("city")
        elif isinstance(workplace, dict):
            lokalizacja = workplace.get("city")

        # Salaries. An offer can list several contract variants at once (e.g. both
        # B2B and UoP); each is routed by its disclosed kind/unit: hourly -> godzinowe
        # bucket, "brutto"/"gross" -> UoP bucket, "netto"/"net" -> B2B bucket.
        types_of_contracts = offer.get("typesOfContracts", [])
        if isinstance(types_of_contracts, dict):
            types_of_contracts = [types_of_contracts]
        waluta = None
        wynagrodzenie_uop_od = wynagrodzenie_uop_do = None
        wynagrodzenie_b2b_od = wynagrodzenie_b2b_do = None
        wynagrodzenie_godzinowe_od = wynagrodzenie_godzinowe_do = None
        for contract in types_of_contracts:
            if not contract or not hasattr(contract, "get"):
                continue
            salary = contract.get("salary")
            if not salary or not hasattr(salary, "get"):
                continue
            if (salary.get("currencySymbol") or "").strip().lower() not in ("zł", "pln"):
                continue
            amount_from, amount_to = salary.get("from"), salary.get("to")
            if amount_from is None and amount_to is None:
                continue
            waluta = "PLN"
            kind_name = (salary.get("kindName") or "").lower()
            unit_name = (salary.get("timeUnit") or {}).get("longForm", "").lower()
            if "godz" in unit_name or "hour" in unit_name:
                if wynagrodzenie_godzinowe_od is None and wynagrodzenie_godzinowe_do is None:
                    wynagrodzenie_godzinowe_od, wynagrodzenie_godzinowe_do = amount_from, amount_to
            elif "brutto" in kind_name or "gross" in kind_name:
                if wynagrodzenie_uop_od is None and wynagrodzenie_uop_do is None:
                    wynagrodzenie_uop_od, wynagrodzenie_uop_do = amount_from, amount_to
            else:
                if wynagrodzenie_b2b_od is None and wynagrodzenie_b2b_do is None:
                    wynagrodzenie_b2b_od, wynagrodzenie_b2b_do = amount_from, amount_to

        return {
            "ID": offer.get("offerUrlName").split(",")[0] if offer.get("offerUrlName") else None,  # type: ignore
            "Stanowisko": offer.get("title"),
            "Firma": offer.get("employer"),
            "Poziom": poziom,
            "Kategoria": None,
            "Technologie": ", ".join(offer.get("technologies", [])),
            "Lokalizacja": lokalizacja,
            "Wynagrodzenie UoP Od": wynagrodzenie_uop_od,
            "Wynagrodzenie UoP Do": wynagrodzenie_uop_do,
            "Wynagrodzenie B2B Od": wynagrodzenie_b2b_od,
            "Wynagrodzenie B2B Do": wynagrodzenie_b2b_do,
            "Wynagrodzenie Godzinowe Od": wynagrodzenie_godzinowe_od,
            "Wynagrodzenie Godzinowe Do": wynagrodzenie_godzinowe_do,
            "Waluta": waluta,
            "Utworzono": offer.get("publicationDateUtc"),
            "Zaktualizowano": None,
            "Source": self.source_name,
        }
