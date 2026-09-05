import urllib.parse
from typing import List

from scrapers.base import BaseScraper
from models.job import Job
from utils.text import clean_text
from utils.matcher import is_relevant_job


class PlaywrightScraper(BaseScraper):
    """
    Optimized Playwright scraper for JavaScript-rendered sites.
    Blocks media and trackers to minimize CPU/bandwidth and loads with domcontentloaded.
    """

    TARGET_SITES = [
        {
            "name": "Virtusa",
            "url": "https://www.virtusa.com/careers",
        },
    ]

    def __init__(self):
        super().__init__("PlaywrightBrowser")

    def scrape(self) -> List[Job]:
        found_jobs: List[Job] = []

        try:
            from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        except ImportError:
            self.logger.warning("Playwright is not installed. Skipping browser-based scrapers.")
            return found_jobs

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 720},
                )

                # Block heavy assets & tracking domains to speed up execution
                def block_unnecessary_resources(route):
                    url = route.request.url.lower()
                    blocked_extensions = [
                        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                        ".woff", ".woff2", ".ttf", ".otf", ".mp4", ".mp3",
                    ]
                    blocked_domains = [
                        "google-analytics.com", "googletagmanager.com",
                        "facebook.net", "ads.linkedin.com", "doubleclick.net",
                    ]
                    if any(url.endswith(ext) or ext in url for ext in blocked_extensions):
                        route.abort()
                    elif any(domain in url for domain in blocked_domains):
                        route.abort()
                    else:
                        route.continue_()

                context.route("**/*", block_unnecessary_resources)
                page = context.new_page()

                for site in self.TARGET_SITES:
                    site_name = site["name"]
                    site_url = site["url"]
                    self.logger.info(f"Visiting {site_name} ({site_url})...")

                    try:
                        # Use domcontentloaded instead of networkidle for much faster response
                        page.goto(site_url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(2000)

                        # Extract all links on page
                        all_links = page.query_selector_all("a")
                        seen_titles = set()

                        for link in all_links:
                            try:
                                link_text = clean_text(link.inner_text())
                                href = link.get_attribute("href") or ""

                                if link_text and is_relevant_job(link_text):
                                    if link_text.lower() in seen_titles:
                                        continue

                                    job_url = href
                                    if href and not href.startswith("http"):
                                        base_parts = urllib.parse.urlparse(site_url)
                                        base_url = f"{base_parts.scheme}://{base_parts.netloc}"
                                        job_url = urllib.parse.urljoin(base_url, href)

                                    seen_titles.add(link_text.lower())
                                    found_jobs.append(
                                        Job(
                                            title=link_text,
                                            company=site_name,
                                            url=job_url or site_url,
                                            source=site_name,
                                        )
                                    )
                            except Exception:
                                continue

                    except PlaywrightTimeout:
                        self.logger.warning(f"Timeout loading {site_name} at {site_url}")
                    except Exception as e:
                        self.logger.error(f"Error scraping {site_name}: {e}")

                browser.close()

        except Exception as e:
            self.logger.error(f"Playwright execution failed: {e}")

        return found_jobs
