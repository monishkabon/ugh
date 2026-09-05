import requests
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class RoosterScraper(BaseScraper):
    """Fast REST API scraper for rooster.jobs (replaces heavy Playwright browser)."""

    SEARCH_API_URL = "https://api.rooster.jobs/jobSearch/jobs/search"

    def __init__(self):
        super().__init__("Rooster")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_urls = set()

        headers = {
            **DEFAULT_HEADERS,
            "Content-Type": "application/json",
            "Referer": "https://rooster.jobs/",
        }

        queries = ["intern", "trainee"]
        for query in queries:
            try:
                payload = {
                    "query": [query],
                    "limit": 50,
                    "page": 1,
                    "filters": {},
                }
                response = requests.post(
                    self.SEARCH_API_URL, headers=headers, json=payload, timeout=15
                )
                response.raise_for_status()
                data = response.json()

                job_items = data.get("body", {}).get("data", [])
                for item in job_items:
                    title = clean_text(item.get("title", ""))
                    item_id = item.get("id")
                    if not title or not item_id:
                        continue

                    company = clean_text(item.get("company_name") or "Unknown Company")
                    job_url = f"https://rooster.jobs/jobs/{item_id}"

                    if job_url in seen_urls:
                        continue

                    if is_relevant_job(title):
                        seen_urls.add(job_url)
                        found_jobs.append(
                            Job(
                                title=title,
                                company=company,
                                url=job_url,
                                source="Rooster",
                            )
                        )

            except requests.RequestException as e:
                self.logger.error(f"Rooster API scrape failed for query '{query}': {e}")
            except Exception as e:
                self.logger.error(f"Rooster parsing error for query '{query}': {e}")

        return found_jobs
