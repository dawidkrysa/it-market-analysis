from datetime import datetime
from typing import Any
import logging
import requests

from utils.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)

class JustJoinIT:
    """
    Collector for JustJoin.it job listings using their API.
    
    Fetches job postings for junior positions from the JustJoin.it API
    and saves them to the database.
    """
    
    API_URL = "https://justjoin.it/api/candidate-api/offers"
    
    def __init__(self, experience_levels: str = "junior") -> None:
        """
        Initialize collector and fetch job listings from JustJoin.it API.
        
        Args:
            experience_levels: Comma-separated experience levels (default: "junior")
                              Options: trainee, junior, mid, senior
        """
        self.__extracted_data: list[dict[str, Any]] = []
        self.__db_handler = DatabaseHandler()
        self.__db_handler.create_tables()
        
        try:
            logger.info(f"Starting JustJoin.it API collector for experience levels: {experience_levels}")
            self.__extracted_data = self._fetch_jobs_from_api(experience_levels)
            self.__db_handler.save_jobs(self.__extracted_data)
            logger.info(f"Successfully saved {len(self.__extracted_data)} jobs to database")
        except Exception as e:
            logger.error(f"Error during JustJoin.it data collection: {e}")
    
    def _fetch_jobs_from_api(self, experience_levels: str) -> list[dict[str, Any]]:
        """
        Fetch job listings from JustJoin.it API.
        
        Args:
            experience_levels: Experience levels to filter by
            
        Returns:
            List of parsed job dictionaries
        """
        parsed_jobs = []
        
        try:
            params = {
                "experienceLevels": experience_levels,
                "itemsCount": 1500
            }
            
            logger.info(f"Fetching jobs from {self.API_URL}")
            response: requests.Response = requests.get(self.API_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            offers = data.get("data", [])
            
            logger.info(f"Received {len(offers)} job offers from API")
            
            for offer in offers:
                try:
                    parsed_job_list: list[dict[str, Any]] = self._parse_offer(offer)
                    if parsed_job_list:
                        parsed_jobs.extend(parsed_job_list)
                except Exception as e:
                    logger.warning(f"Error parsing offer {offer.get('guid', 'unknown')}: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(parsed_jobs)} jobs")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from API: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        
        return parsed_jobs
    
    def _parse_offer(self, offer: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Parse a single job offer from JustJoin.it API response.
        Creates separate entries for each location if multiple locations exist.
        
        Args:
            offer: Job offer dictionary from API
            
        Returns:
            List of parsed job dictionaries (one per location), or empty list if parsing fails
        """
        try:
            # Extract basic information
            base_slug = offer.get("slug", "")
            if not base_slug:
                return []
            
            title = offer.get("title", "Brak tytułu")
            company = offer.get("companyName", "Nieznana firma")
            
            # Map experience level
            experience_level = offer.get("experienceLevel", "junior")
            seniority_map = {
                "trainee": "Trainee",
                "junior": "Junior",
                "mid": "Mid",
                "senior": "Senior"
            }
            seniority = seniority_map.get(experience_level.lower(), "Junior")
            
            # Extract category
            category_data = offer.get("category", {})
            category = category_data.get("key", "") if category_data else ""
            
            # Get all locations - create separate entry for each
            locations = offer.get("locations", [])
            if not locations:
                # Fallback to main city if no locations array
                locations = [{"city": offer.get("city", "Nieznana"), "slug": base_slug}]
            
            # Handle remote work
            workplace_type = offer.get("workplaceType", "")
            
            # Extract technologies from required skills
            required_skills = offer.get("requiredSkills", [])
            technologies = [skill.get("name", "") for skill in required_skills if skill.get("name")]
            technologies_str = ", ".join(technologies) if technologies else ""
            
            # Extract salary information - prefer PLN currency
            employment_types = offer.get("employmentTypes", [])
            salary_from, salary_to, currency = None, None, ""
            
            # Try to find PLN salary first
            for emp_type in employment_types:
                if emp_type.get("currency") == "PLN" and emp_type.get("currencySource") == "original":
                    salary_from = emp_type.get("from")
                    salary_to = emp_type.get("to")
                    currency = "PLN"
                    break
            
            # If no PLN found, use first available with salary data
            if not currency:
                for emp_type in employment_types:
                    if emp_type.get("from") or emp_type.get("to"):
                        salary_from = emp_type.get("from")
                        salary_to = emp_type.get("to")
                        currency = emp_type.get("currency", "")
                        break
            
            # Parse dates
            published_at = offer.get("publishedAt")
            last_published_at = offer.get("lastPublishedAt")
            
            utworzono = datetime.fromisoformat(published_at.replace('Z', '+00:00')) if published_at else datetime.now()
            zaktualizowano = datetime.fromisoformat(last_published_at.replace('Z', '+00:00')) if last_published_at else utworzono
            
            # Create separate job entry for each location
            parsed_jobs = []
            for loc in locations:
                location_city = loc.get("city", "Nieznana")
                location_slug = loc.get("slug", base_slug)
                
                # Add remote indicator if applicable
                if workplace_type == "remote":
                    location_display = f"{location_city} (Remote)" if location_city != "Nieznana" else "Remote"
                else:
                    location_display = location_city
                
                parsed_jobs.append({
                    "ID": location_slug,
                    "Stanowisko": title,
                    "Firma": company,
                    "Poziom": seniority,
                    "Kategoria": category,
                    "Technologie": technologies_str,
                    "Lokalizacja": location_display,
                    "Wynagrodzenie Od": salary_from,
                    "Wynagrodzenie Do": salary_to,
                    "Waluta": currency,
                    "Utworzono": utworzono,
                    "Zaktualizowano": zaktualizowano
                })
            
            return parsed_jobs
            
        except Exception as e:
            logger.error(f"Error parsing offer: {e}")
            return []
    
    def getData(self) -> list[dict[str, Any]]:
        """Return extracted job data."""
        return self.__extracted_data