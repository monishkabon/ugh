import requests
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class SmartRecruitersScraper(BaseScraper):
    """Scrapes IFS careers via the SmartRecruiters public API."""

    BASE_API_URL = "https://api.smartrecruiters.com/v1/companies/IFS1/postings"

    def __init__(self):
        super().__init__("IFS (SmartRecruiters)")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        offset = 0
        limit = 100
        has_more = True

        try:
            while has_more:
                api_url = f"{self.BASE_API_URL}?offset={offset}&limit={limit}"
                response = requests.get(api_url, headers=DEFAULT_HEADERS, timeout=30)
                response.raise_for_status()
                data = response.json()

                postings = data.get("content", [])
                if not postings:
                    break

                for posting in postings:
                    raw_title = clean_text(posting.get("name", ""))
                    job_id = posting.get("id", "")
                    company_name = clean_text(
                        posting.get("company", {}).get("name", "IFS")
                    )
                    city = clean_text(posting.get("location", {}).get("city", ""))

                    if not raw_title or not job_id:
                        continue

                    if is_relevant_job(raw_title):
                        job_url = f"https://careers.smartrecruiters.com/IFS1/{job_id}"
                        display_title = f"{raw_title} ({city})" if city else raw_title

                        found_jobs.append(
                            Job(
                                title=display_title,
                                company=company_name,
                                url=job_url,
                                source="IFS (SmartRecruiters)",
                            )
                        )

                total_count = data.get("totalFound", 0)
                offset += limit
                has_more = offset < total_count

        except requests.RequestException as e:
            self.logger.error(f"IFS SmartRecruiters scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"IFS SmartRecruiters parsing error: {e}")

        return found_jobs
