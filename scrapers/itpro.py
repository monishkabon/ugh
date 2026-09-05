import requests
from bs4 import BeautifulSoup
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class ITProScraper(BaseScraper):
    """Scrapes itpro.lk using standard requests and BeautifulSoup."""

    URL = "https://itpro.lk/jobs/information-technology/"

    def __init__(self):
        super().__init__("ITPro")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []

        try:
            response = requests.get(self.URL, headers=DEFAULT_HEADERS, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            job_cards = soup.find_all("article", class_="job-card")
            for card in job_cards:
                try:
                    link_el = card.find("a", href=True)
                    title_el = card.find("h2", class_="jc-title")
                    company_el = card.find("span", class_="jc-company")

                    if link_el and title_el:
                        title = clean_text(title_el.text)
                        href = link_el["href"]
                        company = clean_text(company_el.text) if company_el else "Unknown Company"

                        if is_relevant_job(title):
                            found_jobs.append(
                                Job(
                                    title=title,
                                    company=company,
                                    url=href,
                                    source="ITPro",
                                )
                            )
                except Exception as e:
                    self.logger.debug(f"Error parsing ITPro job card: {e}")

        except requests.RequestException as e:
            self.logger.error(f"ITPro scrape failed: {e}")
        except Exception as e:
            self.logger.error(f"ITPro parsing error: {e}")

        return found_jobs
