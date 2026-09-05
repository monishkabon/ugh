"""
Backward-compatibility wrapper for scrapper.py.
Forwards execution to the modular main orchestrator.
"""
import sys
import logging
from main import run_scraper
from utils.matcher import is_relevant_job, matches_internship, matches_role
from utils.text import clean_text, generate_job_id
from services.storage import load_seen_jobs, save_seen_jobs
from services.notifier import send_email_notification, format_job_message

# Aliases matching camelCase naming for backward compatibility
runScraper = run_scraper
isRelevantJob = is_relevant_job
matchesInternship = matches_internship
matchesRole = matches_role
cleanText = clean_text
generateJobId = generate_job_id
loadSeenJobs = load_seen_jobs
saveSeenJobs = save_seen_jobs
sendEmailNotification = send_email_notification
formatJobMessage = format_job_message

if __name__ == "__main__":
    run_scraper()
