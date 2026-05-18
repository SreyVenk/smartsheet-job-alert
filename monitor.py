import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

import requests


GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/smartsheet/jobs?content=false"
SEEN_FILE = Path("seen_jobs.json")


def load_seen_jobs():
    if not SEEN_FILE.exists():
        return set()

    with open(SEEN_FILE, "r", encoding="utf-8") as file:
        return set(json.load(file))


def save_seen_jobs(job_ids):
    with open(SEEN_FILE, "w", encoding="utf-8") as file:
        json.dump(sorted(list(job_ids)), file, indent=2)


def fetch_jobs():
    response = requests.get(GREENHOUSE_URL, timeout=20)
    response.raise_for_status()
    data = response.json()
    return data.get("jobs", [])


def is_usa_job(job):
    location = job.get("location", {}).get("name", "").lower()

    return (
        "usa" in location
        or "united states" in location
        or "remote, usa" in location
        or "-remote, usa-" in location
    )


def is_entry_level_software_job(job):
    title = job.get("title", "").lower()

    blocked_keywords = [
        "senior",
        "staff",
        "principal",
        "manager",
        "director",
        "lead",
        "architect",
        " ii",
        " iii",
        " iv",
    ]

    if any(blocked in title for blocked in blocked_keywords):
        return False

    desired_keywords = [
        "software engineer i",
        "associate software engineer",
        "new grad",
        "entry level",
    ]

    return any(keyword in title for keyword in desired_keywords)


def is_relevant_job(job):
    return is_usa_job(job) and is_entry_level_software_job(job)


def format_job(job):
    title = job.get("title", "Unknown Title")
    location = job.get("location", {}).get("name", "Unknown Location")
    url = job.get("absolute_url", "")

    return f"{title}\nLocation: {location}\nApply: {url}"


def send_email_alert(new_jobs):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    subject = f"🚨 New Smartsheet SWE I Job Alert: {len(new_jobs)} new match(es)"

    body = "New USA-based entry-level Smartsheet software job posting(s):\n\n"
    body += "\n\n---\n\n".join(format_job(job) for job in new_jobs)

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def main():
    seen_jobs = load_seen_jobs()
    jobs = fetch_jobs()

    current_job_ids = {str(job["id"]) for job in jobs}

    relevant_new_jobs = [
        job
        for job in jobs
        if str(job["id"]) not in seen_jobs and is_relevant_job(job)
    ]

    if relevant_new_jobs:
        send_email_alert(relevant_new_jobs)
        print(f"Sent alert for {len(relevant_new_jobs)} new relevant job(s).")
    else:
        print("No new relevant USA entry-level Smartsheet software jobs found.")

    save_seen_jobs(current_job_ids)


if __name__ == "__main__":
    main()