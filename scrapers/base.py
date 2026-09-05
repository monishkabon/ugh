import logging
from abc import ABC, abstractmethod
from typing import List
from models.job import Job

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Abstract base class for all site scrapers."""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"scraper.{self.name}")

    @abstractmethod
    def scrape(self) -> List[Job]:
        """Execute scraping logic and return a list of matched Job objects."""
        pass
