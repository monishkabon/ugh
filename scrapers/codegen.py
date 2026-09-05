import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class CodeGenScraper(BaseScraper):
    """Static HTML scraper for CodeGen Careers."""

    URL = "https://codegen.co.uk/careers/"

    def __init__(self):
        super().__init__("CodeGen")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_urls = set()

        try:
            response = requests.get(self.URL, headers=DEFAULT_HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for job links or role cards
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Career role links on CodeGen: /en/company/careers/roles/... or similar
                if "careers/roles" in href or "careers" in href:
                    title = a.get("aria-label") or clean_text(a.get_text())
                    if not title or len(title) > 200:
                        continue

                    full_url = urllib.parse.urljoin(self.URL, href)
                    if full_url in seen_urls:
                        continue

                    if is_relevant_job(title):
                        seen_urls.add(full_url)
                        found_jobs.append(
                            Job(
                                title=title,
                                company="CodeGen",
                                url=full_url,
                                source="CodeGen",
                            )
                        )

            # Also check any headings in featured roles if links were overlayed
            for heading in soup.find_all(["h3", "h4", "h5"]):
                htext = clean_text(heading.get_text())
                if is_relevant_job(htext):
                    parent = heading.find_parent("div")
                    link = parent.find("a", href=True) if parent else None
                    job_url = urllib.parse.urljoin(self.URL, link["href"]) if link else self.URL
                    if job_url not in seen_urls:
                        seen_urls.add(job_url)
                        found_jobs.append(
                            Job(
                                title=htext,
                                company="CodeGen",
                                url=job_url,
                                source="CodeGen",
                            )
                        )

        except requests.RequestException as e:
            self.logger.error(f"CodeGen static scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"CodeGen parsing error: {e}")

        return found_jobs
