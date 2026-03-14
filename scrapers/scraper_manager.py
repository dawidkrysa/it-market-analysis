import logging
from typing import List, Dict, Any
from .sources.justjoinit import JustJoinIT
from .sources.theprotocolit import TheProtocolIT
from .sources.nofluffjobs import NoFluffJobs


logger = logging.getLogger(__name__)

class ScraperManager:
    def __init__(self):
        """
        Register all available scrapers here. 
        Each scraper should be a subclass of BaseScraper and implement the required methods.
        """
        self._scrapers = {
            "justjoinit": JustJoinIT,
            "theprotocolit": TheProtocolIT,
            "nofluffjobs": NoFluffJobs
        }

    def run_all(self, experience_level: str = "junior") -> List[Dict[str, Any]]:
        """
        Runs all registered scrapers and aggregates their results.

        Args:
            experience_level: Filter for experience level (default: "junior")

        Returns:
            List of all job offers collected from all scrapers.
        """
        all_results = []
        
        for name, scraper_class in self._scrapers.items():
            logger.info(f"Starting scraper for: {name}")
            instance = scraper_class()
            data = instance.run(experience_levels=experience_level)
            all_results.extend(data)
            
        return all_results

    def run_single(self, source_name: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Runs a single scraper based on the source name.

        Args:
            source_name: The key name of the scraper to run (e.g., "justjoinit")
            **kwargs: Additional arguments to pass to the scraper's run method
            
        Returns:
            List of job offers collected from the specified scraper.
        """
        scraper_class = self._scrapers.get(source_name)
        if not scraper_class:
            raise ValueError(f"Nie znaleziono scrapera dla źródła: {source_name}")
            
        return scraper_class().run(**kwargs)