import re
import requests
from bs4 import BeautifulSoup
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job
from config.settings import DEFAULT_HEADERS


class TopJobsScraper(BaseScraper):
    """Scrapes TopJobs.lk IT and Internship categories."""

    CATEGORY_URLS = [
        "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ",
        "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=INK",
    ]

    def __init__(self):
        super().__init__("TopJobs")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []
        seen_titles = set()

        for category_url in self.CATEGORY_URLS:
            try:
                response = requests.get(category_url, headers=DEFAULT_HEADERS, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")

                # TopJobs uses table rows with onclick handlers for job listings
                for tr in soup.find_all("tr", onclick=True):
                    onclick_attr = tr.get("onclick", "")
                    if "createAlert" in onclick_attr:
                        # Extract params: createAlert('34','0000000019','0001526380','0000000019','...')
                        match = re.search(
                            r"createAlert\('([^']*)','([^']*)','([^']*)','([^']*)'",
                            onclick_attr,
                        )
                        if match:
                            _, ac, jc, ec = match.groups()
                            # Omit 'rid' so dynamic row IDs don't break deduplication
                            job_url = (
                                f"https://www.topjobs.lk/employer/JobAdvertismentServlet?"
                                f"ac={ac}&jc={jc}&ec={ec}&pg=applicant/vacancybyfunctionalarea.jsp"
                            )

                            title_tag = tr.find("h2")
                            company_tag = tr.find("h1")

                            title = clean_text(title_tag.get_text()) if title_tag else ""
                            company = clean_text(company_tag.get_text()) if company_tag else "TopJobs Listing"

                            if title and is_relevant_job(title):
                                if title.lower() not in seen_titles:
                                    seen_titles.add(title.lower())
                                    found_jobs.append(
                                        Job(
                                            title=title,
                                            company=company,
                                            url=job_url,
                                            source="TopJobs",
                                        )
                                    )

            except requests.RequestException as e:
                self.logger.error(f"TopJobs scrape failed for {category_url}: {e}")
            except Exception as e:
                self.logger.error(f"TopJobs parsing error for {category_url}: {e}")

        return found_jobs
