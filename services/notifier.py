import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Union

from config.settings import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, NOTIFY_EMAIL
from models.job import Job

logger = logging.getLogger(__name__)


def format_job_message(new_jobs: List[Union[Job, dict]]) -> str:
    """Format matched jobs into an HTML email body."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    job_rows = ""
    for i, job in enumerate(new_jobs, 1):
        # Support both Job objects and dictionaries
        title = job.title if isinstance(job, Job) else job.get("title", "")
        company = job.company if isinstance(job, Job) else job.get("company", "")
        url = job.url if isinstance(job, Job) else job.get("url", "")
        source = job.source if isinstance(job, Job) else job.get("source", "")

        display_company = f" @ {company}" if company and company != source else ""

        job_rows += f"""
        <tr style="border-bottom: 1px solid #e0e0e0;">
            <td style="padding: 12px 8px; font-weight: bold; color: #1a1a2e; width: 30px;">{i}</td>
            <td style="padding: 12px 8px;">
                <a href="{url}" style="color: #0066cc; text-decoration: none; font-weight: 600;">
                    {title}
                </a>
                <span style="color: #666; font-size: 12px;">{display_company}</span>
            </td>
            <td style="padding: 12px 8px; color: #555;">{source}</td>
        </tr>"""

    html_body = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 0 auto; background: #f8f9fa; padding: 20px; border-radius: 12px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px; border-radius: 10px 10px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 22px;">🔔 Internship Alert</h1>
            <p style="margin: 8px 0 0; opacity: 0.9; font-size: 14px;">{timestamp}</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
            <p style="color: #333; font-size: 16px; margin-top: 0;">Found <strong>{len(new_jobs)}</strong> new internship posting(s):</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <thead>
                    <tr style="background: #f1f3f5; text-align: left;">
                        <th style="padding: 10px 8px; width: 30px;">#</th>
                        <th style="padding: 10px 8px;">Position</th>
                        <th style="padding: 10px 8px;">Source</th>
                    </tr>
                </thead>
                <tbody>
                    {job_rows}
                </tbody>
            </table>
            <p style="color: #888; font-size: 13px; margin-top: 20px; text-align: center;">Good luck with your applications! 🍀</p>
        </div>
    </div>
    """
    return html_body


def send_email_notification(html_body: str, subject: str = "🔔 New Internship Postings Found!") -> bool:
    """
    Send an email notification via Gmail SMTP.
    Requires a Gmail App Password.
    """
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        logger.warning(
            "Gmail credentials not configured. "
            "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env"
        )
        return False

    recipient_email = NOTIFY_EMAIL if NOTIFY_EMAIL else GMAIL_ADDRESS
    recipients = [r.strip() for r in recipient_email.split(",") if r.strip()]

    if not recipients:
        logger.warning("No valid recipients configured for notification.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject

        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, recipients, msg.as_string())

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
