import os
import smtplib
from email.message import EmailMessage

import requests


GREENHOUSE_URL = "https://boards-api.greenhouse.io/v1/boards/smartsheet/jobs?content=false"


def fetch_jobs():
    response = requests.get(GREENHOUSE_URL, timeout=20)
    response.raise_for_status()
    return response.json().get("jobs", [])


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


def send_email_alert(jobs):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    recipient = os.environ["EMAIL_RECIPIENT"]

    subject = f"🚨 Smartsheet SWE I Job Check: {len(jobs)} match(es)"

    body = "Current USA entry-level Smartsheet software job posting(s):\n\n"
    body += "\n\n---\n\n".join(format_job(job) for job in jobs)

    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        smtp.send_message(message)


def main():
    jobs = fetch_jobs()
    matching_jobs = [job for job in jobs if is_relevant_job(job)]

    if matching_jobs:
        send_email_alert(matching_jobs)
        print(f"Sent alert for {len(matching_jobs)} matching job(s).")
    else:
        print("No USA entry-level Smartsheet software jobs found.")


if __name__ == "__main__":
    main()