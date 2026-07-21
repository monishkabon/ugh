
import os
import re
import json
import unicodedata
import hashlib
import logging
import smtplib
import urllib.parse
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout



load_dotenv()

SEEN_JOBS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seenjobs.txt")

gmailAddress = os.getenv("GMAIL_ADDRESS", "")
gmailAppPassword = os.getenv("GMAIL_APP_PASSWORD", "")
notifyEmail = os.getenv("NOTIFY_EMAIL", "")  # recipient (defaults to sender)
strictRoleMatch = os.getenv("STRICT_ROLE_MATCH", "false").lower() == "true"


internKeywords = ["intern", "internship", "trainee", "industrial training"]


roleKeywords = [
    "data analyst",
    "data scientist",
    "machine learning",
    "big data",
    "business intelligence",
    "data engineer",
    "ai engineer",
    "artificial intelligence",
    "data architect",
    "business analytics",
    "back-end",
    "backend",
    "software develop",
    "software engineer",
    "database admin",
    "cloud engineer",
    "cloud computing",
    "devops",
    "deep learning",
    "nlp",
    "computer vision",
    "cyber security",
    "cybersecurity",
    "information security",
    "secure software",
    "network security",
    "security operations",
    "soc",
    "digital forensics",
    "vulnerability assessment",
    "penetration testing",
    "incident handling",
    "incident response",
    "secure system",
    "data intelligence",
    "platform security",
    "cloud security",
    "security pre-sales",
    "data privacy",
    "cyber defense",
    "health information security",
    "iot security",
    "industrial security",
    "hardware security",
]


targetSites = [
    {
        "name": "TopJobs",
        "url": "https://www.topjobs.lk",
        "method": "topjobs",
    },
    {
        "name": "Virtusa",
        "url": "https://www.virtusa.com/careers/lk",
        "method": "playwright",
    },
    {
        "name": "WSO2",
        "url": "https://wso2.com/careers",
        "method": "playwright",
    },
    {
        "name": "Sysco Labs",
        "url": "https://syscolabs.lk/careers",
        "method": "playwright",
    },
    {
        "name": "99x",
        "url": "https://99x.io/careers/open-positions",
        "method": "99x",
    },
    {
        "name": "IFS",
        "url": "https://careers.smartrecruiters.com/ifs1",
        "method": "smartrecruiters",
    },
    {
        "name": "CodeGen",
        "url": "https://codegen.co.uk/careers/",
        "method": "playwright",
    },
    {
        "name": "LSEG",
        "url": "https://lseg.wd3.myworkdayjobs.com/Careers",
        "method": "workday",
    },
    {
        "name": "Rooster",
        "url": "https://rooster.jobs",
        "method": "rooster",
    },
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)





def generateJobId(title, company, url=""):
    """Create a unique hash for a job to avoid duplicate notifications."""
    rawString = f"{title.strip().lower()}|{company.strip().lower()}|{url.strip().lower()}"
    return hashlib.md5(rawString.encode("utf-8")).hexdigest()


def loadSeenJobs():
    """Load previously seen job IDs from disk."""
    seenJobs = set()
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    seenJobs.add(stripped)
    return seenJobs


def saveSeenJobs(seenJobs):
    """Persist seen job IDs to disk."""
    with open(SEEN_JOBS_FILE, "w") as f:
        for jobId in seenJobs:
            f.write(jobId + "\n")


def cleanText(text):
    """Normalize whitespace, strip newlines, and clean up scraped text."""
    cleaned = re.sub(r"[\n\r\t]+", " ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def matchesInternship(jobTitle):
    """
    Check if a job title contains internship-related keywords.
    Uses word-boundary matching to avoid false positives like
    'internal', 'international', etc.
    """
    titleLower = jobTitle.lower()
    for keyword in internKeywords:
        # Use word boundaries so 'intern' won't match 'internal'
        pattern = r"\b" + re.escape(keyword) + r"\b"
        if re.search(pattern, titleLower):
            return True
    return False


def matchesRole(jobTitle):
    """Check if a job title matches any of the target DS roles."""
    titleLower = jobTitle.lower()
    return any(keyword in titleLower for keyword in roleKeywords)


def isRelevantJob(jobTitle):
    """
    Determine if a job posting is relevant.
    If strictRoleMatch is True: must match BOTH intern keyword AND role keyword.
    If False: only needs to match an intern keyword.
    """
    if not matchesInternship(jobTitle):
        return False
    if strictRoleMatch:
        return matchesRole(jobTitle)
    return True


def createBrowser(playwright):
    """Launch a headless Chromium browser with stealth-like settings."""
    browser = playwright.chromium.launch(
        headless=True,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
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
    return browser, context


# ─── Site-Specific Scrapers ───────────────────────────────────────────────────


def scrapeTopJobs():
    """
    Scrape topjobs.lk for internship listings.
    TopJobs uses functional area pages. We scrape the IT/Software category
    and also check the Internship/Trainee category directly.
    """
    foundJobs = []
    categoryUrls = [
        # IT / Software functional area
        "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ",
        # Internships / Trainee category
        "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=INK",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    for categoryUrl in categoryUrls:
        try:
            response = requests.get(categoryUrl, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # TopJobs uses table rows with onclick handlers for job listings
            for tr in soup.find_all("tr", onclick=True):
                onclick_attr = tr.get("onclick", "")
                if "createAlert" in onclick_attr:
                    # Extract params: createAlert('34','0000000019','0001526380','0000000019','...')
                    match = re.search(r"createAlert\('([^']*)','([^']*)','([^']*)','([^']*)'", onclick_attr)
                    if match:
                        rid, ac, jc, ec = match.groups()
                        # We omit 'rid' (Row ID) from the URL because it changes as new jobs are posted,
                        # which causes the deduplication hash to treat the same job as a new one!
                        jobUrl = f"https://www.topjobs.lk/employer/JobAdvertismentServlet?ac={ac}&jc={jc}&ec={ec}&pg=applicant/vacancybyfunctionalarea.jsp"
                        
                        # Find title and company
                        title_tag = tr.find("h2")
                        company_tag = tr.find("h1")
                        
                        title = title_tag.get_text(strip=True) if title_tag else ""
                        company = company_tag.get_text(strip=True) if company_tag else "TopJobs Listing"
                        
                        if title:
                            cleanedJobText = cleanText(title)
                            if isRelevantJob(cleanedJobText):
                                isDuplicate = any(j["title"].lower() == cleanedJobText.lower() for j in foundJobs)
                                if not isDuplicate:
                                    foundJobs.append({
                                        "title": cleanedJobText,
                                        "company": cleanText(company),
                                        "url": jobUrl,
                                        "source": "TopJobs",
                                    })

        except requests.RequestException as e:
            logger.error(f"TopJobs scrape failed for {categoryUrl}: {e}")

    return foundJobs


def scrapeWithPlaywright(siteName, siteUrl, page):
    """
    Generic Playwright scraper for JS-heavy sites.
    Waits for page to load, then searches all visible text for matches.
    """
    foundJobs = []
    try:
        page.goto(siteUrl, wait_until="networkidle", timeout=45000)
        # Give extra time for dynamic content
        page.wait_for_timeout(3000)

        # Get all links and text on the page
        allLinks = page.query_selector_all("a")
        for link in allLinks:
            try:
                linkText = cleanText(link.inner_text())
                href = link.get_attribute("href") or ""

                if linkText and isRelevantJob(linkText):
                    jobUrl = href
                    if href and not href.startswith("http"):
                        # Resolve relative URLs
                        baseParts = urllib.parse.urlparse(siteUrl)
                        baseUrl = f"{baseParts.scheme}://{baseParts.netloc}"
                        jobUrl = urllib.parse.urljoin(baseUrl, href)

                    foundJobs.append({
                        "title": linkText,
                        "company": siteName,
                        "url": jobUrl or siteUrl,
                        "source": siteName,
                    })
            except Exception:
                continue

        # Also look for job cards / list items that might not be links
        jobCardSelectors = [
            "[class*='job']",
            "[class*='position']",
            "[class*='career']",
            "[class*='vacancy']",
            "[class*='opening']",
            "[class*='listing']",
            "li h3", "li h4",
            "[role='listitem']",
        ]

        for selector in jobCardSelectors:
            try:
                elements = page.query_selector_all(selector)
                for el in elements:
                    try:
                        elText = cleanText(el.inner_text())
                        if elText and isRelevantJob(elText) and len(elText) < 300:
                            # Check if this text is already captured
                            isDuplicate = any(
                                j["title"].lower() == elText.lower() for j in foundJobs
                            )
                            if not isDuplicate:
                                # Try to find a link within or parent
                                linkEl = el.query_selector("a")
                                jobUrl = siteUrl
                                if linkEl:
                                    href = linkEl.get_attribute("href") or ""
                                    if href and not href.startswith("http"):
                                        baseParts = urllib.parse.urlparse(siteUrl)
                                        baseUrl = f"{baseParts.scheme}://{baseParts.netloc}"
                                        jobUrl = urllib.parse.urljoin(baseUrl, href)
                                    elif href:
                                        jobUrl = href

                                foundJobs.append({
                                    "title": elText,
                                    "company": siteName,
                                    "url": jobUrl,
                                    "source": siteName,
                                })
                    except Exception:
                        continue
            except Exception:
                continue

    except PlaywrightTimeout:
        logger.warning(f"{siteName}: Page load timed out for {siteUrl}")
    except Exception as e:
        logger.error(f"{siteName}: Playwright scrape failed: {e}")

    return foundJobs


def scrape99x():
    """
    Scrape 99x.io careers page.
    Job data is embedded as JSON in React4XP hydration script tags.
    """
    foundJobs = []
    url = "https://99x.io/careers/open-positions"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the React4XP script tags containing job data
        scriptTags = soup.find_all("script", {"type": "application/json"})
        for scriptTag in scriptTags:
            try:
                jsonData = json.loads(scriptTag.string)
                props = jsonData.get("props", {})
                items = props.get("items", [])

                for item in items:
                    jobName = item.get("name", "")
                    jobHref = item.get("href", "")
                    jobIntro = item.get("intro", "")

                    if isRelevantJob(jobName) or isRelevantJob(jobIntro):
                        foundJobs.append({
                            "title": jobName,
                            "company": "99x",
                            "url": jobHref or url,
                            "source": "99x",
                        })
            except (json.JSONDecodeError, AttributeError):
                continue

    except requests.RequestException as e:
        logger.error(f"99x scrape failed: {e}")

    return foundJobs


def scrapeSmartRecruiters():
    """
    Scrape IFS careers via SmartRecruiters public API.
    API endpoint: https://api.smartrecruiters.com/v1/companies/IFS1/postings
    """
    foundJobs = []
    baseApiUrl = "https://api.smartrecruiters.com/v1/companies/IFS1/postings"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    try:
        # Fetch with pagination
        offset = 0
        limit = 100
        hasMore = True

        while hasMore:
            apiUrl = f"{baseApiUrl}?offset={offset}&limit={limit}"
            response = requests.get(apiUrl, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            postings = data.get("content", [])
            if not postings:
                break

            for posting in postings:
                jobTitle = posting.get("name", "")
                jobId = posting.get("id", "")
                companyName = posting.get("company", {}).get("name", "IFS")
                jobLocation = posting.get("location", {}).get("city", "")

                if isRelevantJob(jobTitle):
                    jobUrl = f"https://careers.smartrecruiters.com/IFS1/{jobId}"
                    locationStr = f" ({jobLocation})" if jobLocation else ""

                    foundJobs.append({
                        "title": f"{jobTitle}{locationStr}",
                        "company": companyName,
                        "url": jobUrl,
                        "source": "IFS (SmartRecruiters)",
                    })

            # Check if there are more pages
            totalCount = data.get("totalFound", 0)
            offset += limit
            hasMore = offset < totalCount

    except requests.RequestException as e:
        logger.error(f"IFS SmartRecruiters scrape failed: {e}")

    return foundJobs


def scrapeWorkday():
    """
    Scrape LSEG careers via Workday's internal API.
    API endpoint: https://lseg.wd3.myworkdayjobs.com/wday/cxs/lseg/Careers/jobs
    """
    foundJobs = []
    apiUrl = "https://lseg.wd3.myworkdayjobs.com/wday/cxs/lseg/Careers/jobs"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    # Search for intern-related jobs across multiple queries
    searchQueries = ["intern", "internship", "trainee"]

    for query in searchQueries:
        try:
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": query,
            }

            response = requests.post(
                apiUrl, headers=headers, json=payload, timeout=30
            )
            response.raise_for_status()
            data = response.json()

            jobPostings = data.get("jobPostings", [])
            for posting in jobPostings:
                jobTitle = posting.get("title", "")
                externalPath = posting.get("externalPath", "")
                bulletFields = posting.get("bulletFields", [])
                locationStr = ""
                if bulletFields:
                    locationStr = bulletFields[0] if bulletFields[0] else ""

                if isRelevantJob(jobTitle):
                    jobUrl = f"https://lseg.wd3.myworkdayjobs.com/Careers{externalPath}"
                    titleWithLocation = f"{jobTitle} ({locationStr})" if locationStr else jobTitle

                    # Avoid duplicates from different search queries
                    isDuplicate = any(
                        j["url"] == jobUrl for j in foundJobs
                    )
                    if not isDuplicate:
                        foundJobs.append({
                            "title": titleWithLocation,
                            "company": "LSEG",
                            "url": jobUrl,
                            "source": "LSEG (Workday)",
                        })

        except requests.RequestException as e:
            logger.error(f"LSEG Workday scrape failed for query '{query}': {e}")

    return foundJobs


def scrapeRooster(page):
    """
    Scrape rooster.jobs for internship listings.
    """
    foundJobs = []
    queries = ["intern", "trainee"]
    for query in queries:
        url = f"https://rooster.jobs/?query={query}&limit=50&page=1"
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(3000)

            # Find all job cards/headers
            headers = page.query_selector_all(".job-header-info")
            for header in headers:
                try:
                    title_el = header.query_selector("a.job-title")
                    company_el = header.query_selector(".company a")
                    
                    if title_el:
                        title = cleanText(title_el.inner_text())
                        href = title_el.get_attribute("href") or ""
                        
                        company = "Unknown Company"
                        if company_el:
                            company = cleanText(company_el.inner_text())
                        
                        if isRelevantJob(title):
                            jobUrl = href
                            if href and not href.startswith("http"):
                                jobUrl = f"https://rooster.jobs{href}"
                                
                            isDuplicate = any(
                                j["url"] == jobUrl for j in foundJobs
                            )
                            if not isDuplicate:
                                foundJobs.append({
                                    "title": title,
                                    "company": company,
                                    "url": jobUrl,
                                    "source": "Rooster",
                                })
                except Exception as e:
                    logger.debug(f"Error parsing Rooster job card: {e}")
        except Exception as e:
            logger.error(f"Rooster scrape failed for query '{query}': {e}")
            
    return foundJobs


# ─── Email Notification ───────────────────────────────────────────────────────


def sendEmailNotification(htmlBody, subject="🔔 New Internship Postings Found!"):
    """
    Send an email notification via Gmail SMTP.
    Requires a Gmail App Password (not your regular password).
    """
    if not gmailAddress or not gmailAppPassword:
        logger.warning(
            "Gmail credentials not configured. "
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"
        )
        return False

    recipientEmail = notifyEmail if notifyEmail else gmailAddress
    recipients = [r.strip() for r in recipientEmail.split(",") if r.strip()]

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = gmailAddress
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(htmlBody, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmailAddress, gmailAppPassword)
            server.sendmail(gmailAddress, recipients, msg.as_string())

        logger.info(f"✅ Email notification sent to {', '.join(recipients)}!")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed. Check your GMAIL_APP_PASSWORD. "
            "Make sure you're using an App Password, not your regular password."
        )
        return False
    except Exception as e:
        logger.error(f"Email notification error: {e}")
        return False


def formatJobMessage(newJobs):
    """Format matched jobs into an HTML email body."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    jobRows = ""
    for i, job in enumerate(newJobs, 1):
        jobRows += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px 8px; font-weight: bold; color: #1a1a2e;">{i}</td>
            <td style="padding: 12px 8px;">
                <a href="{job['url']}" style="color: #0066cc; text-decoration: none; font-weight: 600;">
                    {job['title']}
                </a>
            </td>
            <td style="padding: 12px 8px; color: #555;">{job['source']}</td>
        </tr>"""

    htmlBody = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 0 auto; background: #f8f9fa; padding: 20px; border-radius: 12px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 22px;">🔔 Internship Alert</h1>
            <p style="margin: 8px 0 0; opacity: 0.9; font-size: 14px;">{timestamp}</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #333; font-size: 16px; margin-top: 0;">Found <strong>{len(newJobs)}</strong> new internship posting(s):</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f1f3f5; text-align: left;">
                        <th style="padding: 10px 8px; width: 30px;">#</th>
                        <th style="padding: 10px 8px;">Position</th>
                        <th style="padding: 10px 8px;">Source</th>
                    </tr>
                </thead>
                <tbody>
                    {jobRows}
                </tbody>
            </table>
            <p style="color: #888; font-size: 13px; margin-top: 20px; text-align: center;">Good luck with your applications! 🍀</p>
        </div>
    </div>
    """
    return htmlBody


# ─── Main Orchestrator ────────────────────────────────────────────────────────


def runScraper():
    """Main entry point — orchestrates all scrapers, filters, deduplicates, and notifies."""
    logger.info("=" * 60)
    logger.info("🚀 Starting Internship Job Scraper")
    logger.info("=" * 60)

    seenJobs = loadSeenJobs()
    allFoundJobs = []

    # ── 1. Scrapers that use requests (no browser needed) ──
    logger.info("📡 Scraping sites with requests...")

    logger.info("  → TopJobs...")
    topJobsResults = scrapeTopJobs()
    logger.info(f"    Found {len(topJobsResults)} matching job(s)")
    allFoundJobs.extend(topJobsResults)

    logger.info("  → 99x (JSON parse)...")
    ninetyNineXResults = scrape99x()
    logger.info(f"    Found {len(ninetyNineXResults)} matching job(s)")
    allFoundJobs.extend(ninetyNineXResults)

    logger.info("  → IFS (SmartRecruiters API)...")
    ifsResults = scrapeSmartRecruiters()
    logger.info(f"    Found {len(ifsResults)} matching job(s)")
    allFoundJobs.extend(ifsResults)

    logger.info("  → LSEG (Workday API)...")
    lsegResults = scrapeWorkday()
    logger.info(f"    Found {len(lsegResults)} matching job(s)")
    allFoundJobs.extend(lsegResults)

    # ── 2. Scrapers that need Playwright (JS-rendered sites) ──
    playwrightSites = [
        site for site in targetSites if site["method"] in ["playwright", "rooster"]
    ]

    if playwrightSites:
        logger.info("🌐 Scraping JS-heavy sites with Playwright...")
        try:
            with sync_playwright() as pw:
                browser, context = createBrowser(pw)
                page = context.new_page()

                for site in playwrightSites:
                    logger.info(f"  → {site['name']}...")
                    if site["method"] == "rooster":
                        siteResults = scrapeRooster(page)
                    else:
                        siteResults = scrapeWithPlaywright(
                            site["name"], site["url"], page
                        )
                    logger.info(f"    Found {len(siteResults)} matching job(s)")
                    allFoundJobs.extend(siteResults)

                browser.close()
        except Exception as e:
            logger.error(f"Playwright initialization failed: {e}")
            logger.info(
                "💡 Run 'playwright install chromium' if browsers aren't installed."
            )

    # ── 3. Deduplicate and find NEW jobs ──
    logger.info("\n🔍 Processing results...")
    newJobs = []
    for job in allFoundJobs:
        jobId = generateJobId(job["title"], job["company"], job["url"])
        if jobId not in seenJobs:
            newJobs.append(job)
            seenJobs.add(jobId)

    logger.info(f"   Total matches found: {len(allFoundJobs)}")
    logger.info(f"   New (unseen) jobs:   {len(newJobs)}")

    # ── 4. Send notification if there are new jobs ──
    if newJobs:
        logger.info("\n📧 Sending email notification...")
        for job in newJobs:
            logger.info(f"   🆕 {job['title']} @ {job['source']}")
            logger.info(f"      {job['url']}")

        htmlBody = formatJobMessage(newJobs)
        timestamp_str = datetime.now().strftime("%I:%M %p")
        subject = f"🔔 {len(newJobs)} New Internship(s) Found! ({timestamp_str})"
        sendEmailNotification(htmlBody, subject)
    else:
        logger.info("\n✅ No new internship postings found. Will check again next run.")

    # ── 5. Save updated seen jobs ──
    saveSeenJobs(seenJobs)
    logger.info(f"\n💾 Saved {len(seenJobs)} job IDs to {SEEN_JOBS_FILE}")
    logger.info("=" * 60)
    logger.info("🏁 Scraper finished!")
    logger.info("=" * 60)


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    runScraper()
