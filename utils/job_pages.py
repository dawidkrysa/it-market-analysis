from concurrent.futures._base import Future

import requests
from datetime import datetime
from typing import Any
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

# Obsługa User-Agent, aby serwer traktował nas jak zwykłą przeglądarkę
HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Content-Type": "application/json"
}


class ApiError(Exception):
    """ Wyjątek na wypadek wystąpienia błędów w API"""
    def __init__(self, message: str, error_code: int) -> None:
        super().__init__(message)
        self.message: str = message
        self.error_code: int = error_code

    def __str__(self) -> str:
        return f"{self.message} (Error Code: {self.error_code})"

class NoFluffJobs:
    # URL do API NoFluffJobs, które pozwala na pobranie ofert pracy
    API_URL: str = "https://nofluffjobs.com/api/search/posting?region=pl&salaryCurrency=PLN&salaryPeriod=month"

    def __init__(self, pages_to_fetch: int = 60, max_workers: int = 5) -> None:
        self.__extracted_data: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:

            futures: dict[Future[list[dict[str, Any]]], int] = {
                executor.submit(self._fetch_page, i): i 
                for i in range(1, pages_to_fetch + 1)
            }

            for future in as_completed(futures):
                try:
                    # Get the list of jobs from the completed thread
                    page_data: list[dict[str, Any]] = future.result()
                    # Add them to our main list
                    self.__extracted_data.extend(page_data)
                except ApiError:
                    # If a specific page failed, we just skip it to not crash the whole app
                    continue
                except Exception:
                    continue
    
    def _fetch_page(self, page_num: int) -> list[dict[str, Any]]:

        delay: float = random.uniform(0.5, 2.5)
        time.sleep(delay)

        """Worker method that fetches and parses a single page."""
        parsed_jobs: list[dict[str, Any]] = []
        
        payload: dict[str, Any] = {
            "page": page_num,
            "criteriaSearch": {"seniority": ["Junior"]},
        }
        
        response: requests.Response = requests.post(self.API_URL, headers=HEADERS, json=payload)
        
        if response.status_code != 200:
            raise ApiError(response.text, response.status_code)
            
        data: dict[str, Any] = response.json()
        postings: list[dict[str, Any]] = data.get('postings', [])

        for job in postings:
            job_id: str = str(job.get('id', ''))
            title: str = str(job.get('title', 'Brak tytułu'))
            company: str = str(job.get('name', 'Nieznana firma'))
            category: str = str(job.get('category', ''))
            
            posted_ms: int = int(job.get('posted', 0))
            renewed_ms: int = int(job.get('renewed', 0))
            posted: datetime = datetime.fromtimestamp(posted_ms / 1000.0)
            renewed: datetime = datetime.fromtimestamp(renewed_ms / 1000.0)
            
            reference: str = str(job.get('reference', ''))
            
            seniority_list: list[str] = job.get('seniority', [])
            seniority: str = ", ".join(seniority_list)
            
            salary_dict: dict[str, Any] = job.get('salary', {})
            salary_from: Any = salary_dict.get('from', '')
            salary_to: Any = salary_dict.get('to', '')
            currency: str = str(salary_dict.get('currency', ''))
            contract_type: str = str(salary_dict.get('type', ''))
            
            location_dict: dict[str, Any] = job.get('location', {})
            location_info: list[dict[str, Any]] = location_dict.get('places', [])
            
            city: str = "Nieznana"
            if location_info and len(location_info) > 0:
                city = str(location_info[0].get('city', 'Zdalnie / Inna'))
                
            is_remote: bool = bool(job.get('fullyRemote', False))
            if is_remote:
                city = "Praca Zdalna"

            parsed_jobs.append({
                "ID": job_id,
                "GROUP_ID": reference,
                "Stanowisko": title,
                "Firma": company,
                "Poziom": seniority,
                "Kategoria": category,
                "Lokalizacja": city,
                "Wynagrodzenie Od": salary_from,
                "Wynagrodzenie Do": salary_to,
                "Waluta": currency,
                "Umowa": contract_type,
                "Utworzono": posted,
                "Zaktualizowano": renewed
            })
            
        
        return parsed_jobs
        
    def getData(self) -> list[dict[str, Any]]:
        return self.__extracted_data