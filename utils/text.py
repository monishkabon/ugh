import re
import hashlib


def clean_text(text: str) -> str:
    """Normalize whitespace, strip newlines, and clean up scraped text."""
    if not text:
        return ""
    cleaned = re.sub(r"[\n\r\t]+", " ", text)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


def generate_job_id(title: str, company: str, url: str = "") -> str:
    """Create a unique MD5 hash for a job to avoid duplicate notifications."""
    raw_string = f"{title.strip().lower()}|{company.strip().lower()}|{url.strip().lower()}"
    return hashlib.md5(raw_string.encode("utf-8")).hexdigest()
