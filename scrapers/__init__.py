"""Scrapers package."""
from .base import BaseScraper
from .topjobs import TopJobsScraper
from .rooster import RoosterScraper
from .wso2 import WSO2Scraper
from .codegen import CodeGenScraper
from .ninety_nine_x import NinetyNineXScraper
from .smartrecruiters import SmartRecruitersScraper
from .workday import WorkdayScraper
from .itpro import ITProScraper
from .playwright_scraper import PlaywrightScraper

__all__ = [
    "BaseScraper",
    "TopJobsScraper",
    "RoosterScraper",
    "WSO2Scraper",
    "CodeGenScraper",
    "NinetyNineXScraper",
    "SmartRecruitersScraper",
    "WorkdayScraper",
    "ITProScraper",
    "PlaywrightScraper",
]
