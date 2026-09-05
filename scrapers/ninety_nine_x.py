import json
import requests
from bs4 import BeautifulSoup
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class NinetyNineXScraper(BaseScraper):
    """Scrapes 99x.io careers page via embedded JSON hydration data."""

    URL = "https://99x.io/careers/open-positions"

    def __init__(self):
        super().__init__("99x")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_urls = set()

        try:
            response = requests.get(self.URL, headers=DEFAULT_HEADERS, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Find the React4XP script tags containing job data
            script_tags = soup.find_all("script", {"type": "application/json"})
            for script_tag in script_tags:
                try:
                    json_data = json.loads(script_tag.string)
                    props = json_data.get("props", {})
                    items = props.get("items", [])

                    for item in items:
                        job_name = clean_text(item.get("name", ""))
                        job_href = item.get("href", "") or self.URL
                        job_intro = clean_text(item.get("intro", ""))

                        if not job_name or job_href in seen_urls:
                            continue

                        if is_relevant_job(job_name) or is_relevant_job(job_intro):
                            seen_urls.add(job_href)
                            found_jobs.append(
                                Job(
                                    title=job_name,
                                    company="99x",
                                    url=job_href,
                                    source="99x",
                                )
                            )
                except (json.JSONDecodeError, AttributeError):
                    continue

        except requests.RequestException as e:
            self.logger.error(f"99x scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"99x parsing error: {e}")

        return found_jobs
