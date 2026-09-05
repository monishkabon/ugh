import hashlib
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Job:
    """Represents a single job posting."""
    title: str
    company: str
    url: str
    source: str
    job_id: str = field(default="")

    def __post_init__(self):
        if not self.job_id:
            self.job_id = self.compute_job_id(self.title, self.company, self.url)

    @staticmethod
    def compute_job_id(title: str, company: str, url: str = "") -> str:
        """Create a unique MD5 hash for a job matching the original format."""
        raw_string = f"{title.strip().lower()}|{company.strip().lower()}|{url.strip().lower()}"
        return hashlib.md5(raw_string.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        """Serialize job to dictionary."""
        return {
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "source": self.source,
            "job_id": self.job_id,
        }
