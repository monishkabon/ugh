import requests
from typing import List, Dict, Any

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class WorkdayScraper(BaseScraper):
    """Scrapes Workday-based career portals (LSEG and Sysco LABS)."""

    TENANTS = [
        {
            "company": "LSEG",
            "source": "LSEG (Workday)",
            "api_url": "https://lseg.wd3.myworkdayjobs.com/wday/cxs/lseg/Careers/jobs",
            "base_url": "https://lseg.wd3.myworkdayjobs.com/Careers",
            "applied_facets": {},
            "queries": ["intern", "internship", "trainee"],
        },
        {
            "company": "Sysco LABS",
            "source": "Sysco LABS (Workday)",
            "api_url": "https://wd5.myworkdaysite.com/wday/cxs/sysco/syscocareers/jobs",
            "base_url": "https://wd5.myworkdaysite.com/en-US/recruiting/sysco/syscocareers",
            "applied_facets": {
                "locations": ["b014cc62fe6601b8d666502cd5287f36"]  # Sri Lanka
            },
            "queries": ["intern", "trainee"],
        },
    ]

    def __init__(self):
        super().__init__("Workday (LSEG & Sysco LABS)")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_urls = set()

        headers = {
            **DEFAULT_HEADERS,
            "Content-Type": "application/json",
        }

        for tenant in self.TENANTS:
            company_name = tenant["company"]
            source_name = tenant["source"]
            api_url = tenant["api_url"]
            base_url = tenant["base_url"]
            applied_facets = tenant["applied_facets"]
            queries = tenant["queries"]

            for query in queries:
                try:
                    payload: Dict[str, Any] = {
                        "appliedFacets": applied_facets,
                        "limit": 20,
                        "offset": 0,
                        "searchText": query,
                    }

                    response = requests.post(
                        api_url, headers=headers, json=payload, timeout=25
                    )
                    response.raise_for_status()
                    data = response.json()

                    job_postings = data.get("jobPostings", [])
                    for posting in job_postings:
                        raw_title = clean_text(posting.get("title", ""))
                        external_path = posting.get("externalPath", "")
                        bullet_fields = posting.get("bulletFields", [])
                        location_str = clean_text(bullet_fields[0]) if bullet_fields else ""

                        if not raw_title or not external_path:
                            continue

                        if is_relevant_job(raw_title):
                            job_url = f"{base_url}{external_path}"
                            if job_url in seen_urls:
                                continue

                            seen_urls.add(job_url)
                            display_title = (
                                f"{raw_title} ({location_str})"
                                if location_str and location_str not in raw_title
                                else raw_title
                            )

                            found_jobs.append(
                                Job(
                                    title=display_title,
                                    company=company_name,
                                    url=job_url,
                                    source=source_name,
                                )
                            )

                except requests.RequestException as e:
                    self.logger.error(
                        f"Workday scrape failed for {company_name} (query '{query}'): {e}"
                    )
                except Exception as e:
                    self.logger.error(
                        f"Workday parsing error for {company_name} (query '{query}'): {e}"
                    )

        return found_jobs
