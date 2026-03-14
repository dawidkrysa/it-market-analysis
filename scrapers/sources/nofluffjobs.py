import requests
import logging
from datetime import datetime
from typing import Any, List, Dict
from .base import BaseScraper

logger = logging.getLogger(__name__)

class NoFluffJobs(BaseScraper):
    API_URL = "https://nofluffjobs.com/api/search/posting"
    HEADERS = {
        "Content-Type": "application/infiniteSearch+json",
        "Accept": "application/json, text/plain, */*"
    }
    
    def __init__(self) -> None:
        """ Initializes the NoFluffJobs scraper. """
        super().__init__(source_name="nofluffjobs")

    def fetch_raw_data(self, experience_levels: str = "junior") -> List[Dict[str, Any]]:
        """
        Fetches raw job data from the NoFluffJobs API.

        Args:
            experience_levels: Comma-separated experience levels to filter by (default: "junior")
        
        Returns:
            List of raw job data dictionaries.
        """
        payload = {
                "criteria": f"category=sys-administrator,business-analyst,architecture,backend,data,ux,devops,erp,embedded,frontend,fullstack,game-dev,mobile,project-manager,security,support,testing,other seniority={experience_levels}",
                "url": {
                    "searchParam": "artificial-intelligence"
                },
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
                "language": "pl-PL"
            }
            logger.info(f"Fetching jobs from {self.API_URL}")

            response = requests.post(self.API_URL, headers=self.HEADERS, params=params, json=payload, timeout=30)
            
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

    def parse_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """ 
        Parses the raw job data from NoFluffJobs into a standardized format.
        
        Args:
            raw_data: List of raw job data dictionaries.
        """

        parsed_jobs = []
        for offer in raw_data:
            try:
                parsed_jobs.extend(self._parse_single_offer(offer))
            except Exception as e:
                logger.warning(f"Error parsing offer {offer.get('id')}: {e}")

        return parsed_jobs
    
    def _parse_single_offer(self, offer: dict[str, Any]) -> List[Dict[str, Any]]:
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
        tech_str = ", ".join([t.get("value", "") for t in offer.get("tiles", {}).get("values", []) if t.get("type") == "requirement"])

        # Salaries (simplified for readability)
        salary_from, salary_to, currency = None, None, "PLN"
        salary_info = offer.get("salary", {})
        if salary_info.get("disclosedAt") == "AT_FIRST_INTERVIEW":
            salary_from, salary_to = None, None
        elif salary_info.get("disclosedAt") == "ALWAYS":
            salary_from, salary_to = None, None
        elif salary_info.get("disclosedAt") == "NEVER":
            salary_from, salary_to = None, None
        else:
            salary_from, salary_to = None, None

        # Locations
        results = []
        locations = offer.get("location", {}).get("places", [])

        

        for loc in locations:
            base_slug = loc.get("url", "")
            if not base_slug: continue
            results.append({
                "ID": base_slug,
                "Stanowisko": offer.get("title", ""),
                "Firma": offer.get("name", ""),
                "Poziom": seniority,
                "Kategoria": offer.get("category", ""),
                "Technologie": tech_str,
                "Lokalizacja": loc.get("city", "Nieznana"),
                "Wynagrodzenie Od": salary_from,
                "Wynagrodzenie Do": salary_to,
                "Waluta": currency,
                "Utworzono": utworzono,
                "Zaktualizowano": renewed_at,
                "Source": self.source_name
            })
         
        return results
            