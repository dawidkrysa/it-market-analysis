import requests
import logging
from datetime import datetime
from typing import Any, List, Dict
from .base import BaseScraper

logger = logging.getLogger(__name__)

class TheProtocolIT(BaseScraper):
    API_URL = "https://theprotocol.it/filtry/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def __init__(self) -> None:
        """ Initializes the TheProtocolIT scraper. """
        super().__init__(source_name="theprotocolit")
    
    def fetch_raw_data(self, experience_levels: str = "junior") -> List[Dict[str, Any]]:
        """ 
        Fetches raw job data from TheProtocol.it API. 

        Returns:
            List of raw job data dictionaries.
        """

        from bs4 import BeautifulSoup
        import json

        all_offers = []
        counter = 1
        page_count = 1
        first = True
        while counter <= page_count:
            url: str = self.API_URL + f"{experience_levels};p" + f"?pageNumber={counter}"
            logger.info(f"Fetching jobs from {url}")
            response = requests.get(url, timeout=30, headers=self.HEADERS)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script_tag:
                logger.error("Could not find __NEXT_DATA__ script tag in response")
                break
            data = json.loads(script_tag.text)
            offers = data.get("props", {}).get("pageProps", {}).get("offersResponse", {}).get("offers", [])
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
        logger.info(f"Received {len(all_offers)} job offers from API (all pages)")
        return all_offers
    
    def parse_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    
    def _parse_single_offer(self, offer: dict[str, Any]) -> Dict[str, Any]:
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
            if first_level and hasattr(first_level, 'get'):
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
            if first_workplace and hasattr(first_workplace, 'get'):
                lokalizacja = first_workplace.get("city")
        elif isinstance(workplace, dict):
            lokalizacja = workplace.get("city")

        types_of_contracts = offer.get("typesOfContracts", [])
        wyn_od = wyn_do = waluta = None
        if isinstance(types_of_contracts, list) and types_of_contracts:
            first_contract = types_of_contracts[0]
            if first_contract and hasattr(first_contract, 'get'):
                salary = first_contract.get("salary", {})
                if salary and hasattr(salary, 'get'):
                    wyn_od = salary.get("from")
                    wyn_do = salary.get("to")
                    waluta = salary.get("currencySymbol")
        elif isinstance(types_of_contracts, dict):
            salary = types_of_contracts.get("salary", {})
            if salary and hasattr(salary, 'get'):
                wyn_od = salary.get("from")
                wyn_do = salary.get("to")
                waluta = salary.get("currencySymbol")

        return {
            "ID": offer.get("offerUrlName").split(",")[0] if offer.get("offerUrlName") else None, # type: ignore
            "Stanowisko": offer.get("title"),
            "Firma": offer.get("employer"),
            "Poziom": poziom,
            "Kategoria": None,
            "Technologie": ", ".join(offer.get("technologies", [])),
            "Lokalizacja": lokalizacja,
            "Wynagrodzenie Od": wyn_od,
            "Wynagrodzenie Do": wyn_do,
            "Waluta": "PLN" if waluta else None,
            "Utworzono": offer.get("publicationDateUtc"),
            "Zaktualizowano": None,
            "Source": self.source_name
        }
        