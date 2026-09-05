import os
import logging
from config.settings import SEEN_JOBS_FILE

logger = logging.getLogger(__name__)


def load_seen_jobs(file_path: str = SEEN_JOBS_FILE) -> set[str]:
    """Load previously seen job IDs from disk."""
    seen_jobs = set()
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        seen_jobs.add(stripped)
            logger.info(f"Loaded {len(seen_jobs)} seen job IDs from {file_path}")
        except Exception as e:
            logger.error(f"Error reading seen jobs file {file_path}: {e}")
    else:
        logger.info(f"No existing seen jobs file found at {file_path}. Starting fresh.")
    return seen_jobs


def save_seen_jobs(seen_jobs: set[str], file_path: str = SEEN_JOBS_FILE) -> None:
    """Persist seen job IDs to disk."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            for job_id in sorted(seen_jobs):
                f.write(f"{job_id}\n")
        logger.info(f"Saved {len(seen_jobs)} seen job IDs to {file_path}")
    except Exception as e:
        logger.error(f"Error saving seen jobs to {file_path}: {e}")
