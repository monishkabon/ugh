import urllib.parse
import requests
from bs4 import BeautifulSoup
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class WSO2Scraper(BaseScraper):
    """Static HTML scraper for WSO2 Careers (replaces heavy Playwright browser)."""

    URL = "https://wso2.com/careers"

    def __init__(self):
        super().__init__("WSO2")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_urls = set()

        try:
            response = requests.get(self.URL, headers=DEFAULT_HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for job links (/careers/<id>/...)
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if not href.startswith("/careers/") and "wso2.com/careers/" not in href:
                    continue

                full_url = urllib.parse.urljoin(self.URL, href)
                if full_url in seen_urls:
                    continue

                # Title is typically in h5 inside pd-card, or direct text
                title_tag = a.find("h5")
                title = clean_text(title_tag.get_text()) if title_tag else clean_text(a.get_text())
                if not title or len(title) > 200:
                    continue

                # Optional location tag
                location_tag = a.find("span", class_="cCountry")
                if location_tag:
                    loc = clean_text(location_tag.get_text())
                    if loc and loc not in title:
                        title = f"{title} ({loc})"

                if is_relevant_job(title):
                    seen_urls.add(full_url)
                    found_jobs.append(
                        Job(
                            title=title,
                            company="WSO2",
                            url=full_url,
                            source="WSO2",
                        )
                    )

        except requests.RequestException as e:
            self.logger.error(f"WSO2 static scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"WSO2 parsing error: {e}")

        return found_jobs
