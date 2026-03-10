from datetime import datetime
from typing import Any
import time
import re
import logging

from utils.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)


class NoFluffJobCollector:
    """
    Scraper for NoFluffJobs.com job listings using Playwright.
    
    Extracts job postings for trainee and junior positions, including:
    - Job title, company, location, seniority level
    - Salary ranges and currency
    - Categories and required technologies
    """
    
    BASE_URL = "https://nofluffjobs.com"
    
    def __init__(self, pages_to_fetch: int = 15) -> None:
        """
        Initialize scraper and fetch job listings.
        
        Args:
            pages_to_fetch: Maximum number of pages to load (default: 15)
        """
        self.__extracted_data: list[dict[str, Any]] = []
        self.__db_handler = DatabaseHandler()
        self.__db_handler.create_tables()

        try:
            from playwright.sync_api import sync_playwright
            
            logger.info("Starting NoFluffJobs scraper with Playwright")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                
                self.__extracted_data = self._fetch_all_pages_playwright(context, pages_to_fetch)
                browser.close()
                
        except ImportError as e:
            logger.error(f"Playwright not installed: {e}")
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        self.__db_handler.save_jobs(self.__extracted_data)
    
    def _fetch_all_pages_playwright(self, context: Any, pages_to_fetch: int) -> list[dict[str, Any]]:
        """
        Fetch job listings by progressively loading pages.
        
        Args:
            context: Playwright browser context
            pages_to_fetch: Number of pages to load
            
        Returns:
            List of parsed job dictionaries
        """
        parsed_jobs = []
        page = context.new_page()
        url = f"{self.BASE_URL}/pl/?criteria=seniority%3Dtrainee,junior&sort=newest"
        
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_selector('a[href*="/job/"]', timeout=10000)

            for click_num in range(pages_to_fetch - 1):
                try:
                    page.wait_for_selector('button:has-text("Pokaż kolejne oferty")', state="visible", timeout=20000)
                    time.sleep(2)
                    
                    jobs_before = page.locator('a[href*="/job/"]').count()
                    page.evaluate("""
                        const btn = Array.from(document.querySelectorAll('button'))
                            .find(b => b.textContent.includes('Pokaż kolejne oferty'));
                        if (btn) btn.click();
                    """)
                    
                    for i in range(15):
                        time.sleep(2)
                        jobs_current = page.locator('a[href*="/job/"]').count()
                        if jobs_current > jobs_before:
                            time.sleep(2)
                            break
                    else:
                        break
                        
                except Exception as e:
                    logger.warning(f"Button not found or error: {e}")
                    break
            
            job_links = page.locator('a[href*="/job/"]').all()
            logger.info(f"Scraped {len(job_links)} job listings")
            
            for link in job_links:
                try:
                    href = link.get_attribute('href')
                    job_id = href.split('/')[-1] if href else ''
                    
                    if any(job['ID'] == job_id for job in parsed_jobs):
                        continue
                    
                    full_text = link.inner_text()
                    lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                    
                    title = 'Brak tytułu'
                    try:
                        title_elem = link.locator('h3').first
                        if title_elem.count() > 0:
                            title = title_elem.inner_text().strip().replace(' NOWA','')
                        elif lines:
                            title = lines[0].strip()
                    except:
                        pass
                    
                    company = 'Nieznana firma'
                    try:
                        company_elem = link.locator('h4.company-name').first
                        if company_elem.count() > 0:
                            company = company_elem.inner_text().strip() or 'Nieznana firma'
                    except:
                        pass
                    
                    location = 'Nieznana'
                    try:
                        location_elem = link.locator('nfj-posting-item-city[data-cy="location on the job offer listing"] span').first
                        if location_elem.count() > 0:
                            location = location_elem.inner_text().strip() or 'Nieznana'
                    except:
                        pass
                    
                    salary_from, salary_to, currency = '', '', ''
                    try:
                        salary_elem = link.locator('span[data-cy="salary ranges on the job offer listing"]').first
                        if salary_elem.count() > 0:
                            salary_text = salary_elem.inner_text().strip()
                            salary_match = re.search(r'(\d+(?:[\s\xa0]\d+)*)\s*[–-]\s*(\d+(?:[\s\xa0]\d+)*)\s*(PLN|EUR|USD)', salary_text)
                            if salary_match:
                                salary_from_str = salary_match.group(1).replace(' ', '').replace('\xa0', '')
                                salary_to_str = salary_match.group(2).replace(' ', '').replace('\xa0', '')
                                currency = salary_match.group(3).strip()
                                
                                multiplier = 1000 if 'k' in salary_text.lower() and len(salary_from_str) <= 3 else 1
                                try:
                                    salary_from = int(salary_from_str) * multiplier
                                    salary_to = int(salary_to_str) * multiplier
                                except ValueError:
                                    salary_from, salary_to, currency = '', '', ''
                    except:
                        pass
                    
                    category = ''
                    technologies = []
                    
                    try:
                        tag_elements = link.locator('span[data-cy="category name on the job offer listing"]').all()
                        
                        category_keywords = [
                            'JavaScript', 'Python', 'Java', 'PHP', 'Ruby', 'C#', 'C++', 'Go', 'Rust', 'TypeScript',
                            'Frontend', 'Backend', 'Fullstack', 'DevOps', 'Mobile', 'Testing', 'QA', 'Tester',
                            'Data', 'Analytics', 'Security', 'Support', 'Admin', 'Project Manager', 'Scrum Master',
                            'Product', 'Design', 'UX', 'UI', 'Business', 'Sales', 'Marketing', 'Content',
                            'HR', 'Finanse', 'Finance', 'Accounting', 'Księgowość', 'Logistyka', 'Logistics',
                            'Customer', 'Service', 'Manager', 'Analyst', 'Consultant', 'Specialist'
                        ]
                        
                        for tag_elem in tag_elements:
                            tag_text = tag_elem.inner_text().strip()
                            
                            if not category:
                                for keyword in category_keywords:
                                    if keyword.lower() in tag_text.lower():
                                        category = tag_text
                                        break
                            
                            if tag_text != category:
                                technologies.append(tag_text)
                    except:
                        pass
                    
                    technologies_str = ', '.join(technologies) if technologies else ''
                    
                    seniority = 'Junior'
                    full_text_lower = full_text.lower()
                    if 'trainee' in full_text_lower:
                        seniority = 'Trainee'
                    elif 'junior' in full_text_lower:
                        seniority = 'Junior'
                    elif 'mid' in full_text_lower:
                        seniority = 'Mid'
                    elif 'senior' in full_text_lower:
                        seniority = 'Senior'
                    
                    utworzono = zaktualizowano = datetime.now()
                    
                    parsed_jobs.append({
                        "ID": job_id,
                        "Stanowisko": title,
                        "Firma": company,
                        "Poziom": seniority,
                        "Kategoria": category,
                        "Technologie": technologies_str,
                        "Lokalizacja": location,
                        "Wynagrodzenie Od": salary_from,
                        "Wynagrodzenie Do": salary_to,
                        "Waluta": currency,
                        "Utworzono": utworzono,
                        "Zaktualizowano": zaktualizowano
                    })
                except:
                    continue
            
            logger.info(f"Successfully parsed {len(parsed_jobs)} unique jobs")
            
        except Exception as e:
            logger.error(f"Error loading page: {e}")
        finally:
            page.close()
        
        return parsed_jobs
        
    def getData(self) -> list[dict[str, Any]]:
        """Return extracted job data."""
        return self.__extracted_data