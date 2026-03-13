import requests
import logging
from datetime import datetime
from typing import Any, List, Dict
from .base import BaseScraper

logger = logging.getLogger(__name__)

class JustJoinIT(BaseScraper):
    API_URL = "https://justjoin.it/api/candidate-api/offers"

    def __init__(self) -> None:
        """ Initializes the JustJoinIT scraper. """
        super().__init__(source_name="justjoinit")

    def fetch_raw_data(self, experience_levels: str = "junior") -> List[Dict[str, Any]]:
        """ 
        Fetches raw job data from the JustJoin.it API. 

        Args:
            experience_levels: Comma-separated experience levels to filter by (default: "junior")

        Returns:
            List of raw job data dictionaries.
        """
        params = {
            "experienceLevels": experience_levels,
            "itemsCount": 1500
        }
        logger.info(f"Fetching jobs from {self.API_URL}")
        response = requests.get(self.API_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        offers = data.get("data", [])
        logger.info(f"Received {len(offers)} job offers from API")
        return offers
    
    def parse_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
    

    def _parse_single_offer(self, offer: dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses a single job offer from JustJoin.it into the standardized format.
        
        Args:    
            offer: Raw job offer dictionary from the API.
        
        Returns:
            List of parsed job dictionaries (one per location).
        """
        base_slug = offer.get("slug", "")
        if not base_slug: return []

        # Mapping seniority
        experience_level = offer.get("experienceLevel", "junior")
        seniority_map = {"trainee": "Trainee", "junior": "Junior", "mid": "Mid", "senior": "Senior"}
        seniority = seniority_map.get(experience_level.lower(), "Junior")

        # Dates
        published_at = offer.get("publishedAt")
        utworzono = datetime.fromisoformat(published_at.replace('Z', '+00:00')) if published_at else datetime.now()

        # Technologies
        required_skills = offer.get("requiredSkills", [])
        tech_str = ", ".join([s.get("name", "") for s in required_skills if s.get("name")])

        # Salaries (simplified for readability)
        salary_from, salary_to, currency = None, None, "PLN"
        for emp in offer.get("employmentTypes", []):
            if emp.get("from"):
                salary_from, salary_to, currency = emp.get("from"), emp.get("to"), emp.get("currency", "PLN")
                break

        results = []
        locations = offer.get("locations", [{"city": offer.get("city", "Nieznana"), "slug": base_slug}])
        
        for loc in locations:
            results.append({
                "ID": loc.get("slug", base_slug),
                "Stanowisko": offer.get("title", "Brak tytułu"),
                "Firma": offer.get("companyName", "Nieznana firma"),
                "Poziom": seniority,
                "Kategoria": offer.get("category", {}).get("key", ""),
                "Technologie": tech_str,
                "Lokalizacja": loc.get("city", "Nieznana"),
                "Wynagrodzenie Od": salary_from,
                "Wynagrodzenie Do": salary_to,
                "Waluta": currency,
                "Utworzono": utworzono,
                "Zaktualizowano": utworzono
            })
        return results