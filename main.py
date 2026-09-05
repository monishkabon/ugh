import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from models.job import Job
from services.storage import load_seen_jobs, save_seen_jobs
from services.notifier import format_job_message, send_email_notification
from scrapers import (
    TopJobsScraper,
    RoosterScraper,
    WSO2Scraper,
    CodeGenScraper,
    NinetyNineXScraper,
    SmartRecruitersScraper,
    WorkdayScraper,
    ITProScraper,
    PlaywrightScraper,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_scraper():
    """Main entry point — orchestrates concurrent scrapers, deduplicates, and notifies."""
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("🚀 Starting Internship Job Scraper (Modular & Concurrent)")
    logger.info("=" * 60)

    seen_jobs = load_seen_jobs()
    all_found_jobs: List[Job] = []

    # 1. Concurrent HTTP & API scrapers
    http_scrapers = [
        TopJobsScraper(),
        RoosterScraper(),
        WSO2Scraper(),
        CodeGenScraper(),
        NinetyNineXScraper(),
        SmartRecruitersScraper(),
        WorkdayScraper(),
        ITProScraper(),
    ]

    logger.info(f"⚡ Launching {len(http_scrapers)} HTTP/API scrapers in parallel...")
    http_start = time.time()

    with ThreadPoolExecutor(max_workers=len(http_scrapers)) as executor:
        future_to_scraper = {executor.submit(s.scrape): s for s in http_scrapers}
        for future in as_completed(future_to_scraper):
            scraper = future_to_scraper[future]
            try:
                results = future.result()
                logger.info(f"  ✓ {scraper.name}: Found {len(results)} matching job(s)")
                all_found_jobs.extend(results)
            except Exception as e:
                logger.error(f"  ✗ {scraper.name} scraper threw an exception: {e}")

    logger.info(f"⚡ HTTP/API scraping completed in {time.time() - http_start:.2f}s")

    # 2. Browser-based scrapers (Playwright)
    playwright_scraper = PlaywrightScraper()
    logger.info(f"🌐 Running browser-based scraper ({playwright_scraper.name})...")
    browser_start = time.time()
    try:
        browser_results = playwright_scraper.scrape()
        logger.info(f"  ✓ Browser scraper: Found {len(browser_results)} matching job(s)")
        all_found_jobs.extend(browser_results)
    except Exception as e:
        logger.error(f"  ✗ Browser scraper failed: {e}")
    logger.info(f"🌐 Browser scraping completed in {time.time() - browser_start:.2f}s")

    # 3. Deduplicate and detect new jobs
    logger.info("\n🔍 Processing and deduplicating results...")
    new_jobs: List[Job] = []
    for job in all_found_jobs:
        if job.job_id not in seen_jobs:
            new_jobs.append(job)
            seen_jobs.add(job.job_id)

    logger.info(f"   Total matching jobs found: {len(all_found_jobs)}")
    logger.info(f"   New (unseen) jobs:        {len(new_jobs)}")

    # 4. Notify if new jobs found
    if new_jobs:
        logger.info("\n📧 Sending notification for new jobs...")
        for job in new_jobs:
            logger.info(f"   🆕 {job.title} @ {job.source}")
            logger.info(f"      {job.url}")

        html_body = format_job_message(new_jobs)
        timestamp_str = datetime.now().strftime("%I:%M %p")
        subject = f"🔔 {len(new_jobs)} New Internship(s) Found! ({timestamp_str})"
        send_email_notification(html_body, subject)
    else:
        logger.info("\n✅ No new internship postings found. Will check again next run.")

    # 5. Persist seen jobs
    save_seen_jobs(seen_jobs)

    total_duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"🏁 Finished in {total_duration:.2f}s!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_scraper()
