import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# =========================
# CONFIG
# =========================
JOB_KEYWORDS = [
    "data analyst", "entry level", "ml intern", "machine learning",
    "ml engineer", "data engineer", "bde", "business development executive",
    "e-learning", "content developer"
]

COMPANY_URLS = {
    "Zensar": "https://zensar.com/careers",
    "Persistent Systems": "https://www.persistent.com/careers/",
    "Infosys": "https://career.infosys.com/joblist",
    "Tech Mahindra": "https://careers.techmahindra.com/",
    "TCS": "https://www.tcs.com/careers",
    "Cognizant": "https://careers.cognizant.com/global-en/jobs",
    "Wipro": "https://careers.wipro.com/careers-home/",
    "Capgemini": "https://www.capgemini.com/careers/"
}

# =========================
# SCRAPER FUNCTION
# =========================
def scrape_jobs():
    job_results = []

    for company, url in COMPANY_URLS.items():
        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text().lower()

            for keyword in JOB_KEYWORDS:
                if keyword in text:
                    job_results.append(f"{company}: Found '{keyword}' → {url}")
        except Exception as e:
            job_results.append(f"{company}: Error fetching → {e}")

    return job_results


# =========================
# EMAIL FUNCTION
# =========================
def send_email(jobs, sender, password, receiver):
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    subject = f"Daily Job Alert - {now}"

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject

    body = "\n".join(jobs) if jobs else "No relevant jobs found today."
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    jobs = scrape_jobs()

    import os
    sender = os.getenv("SENDER_EMAIL")
    password = os.getenv("SENDER_PASS")
    receiver = os.getenv("RECEIVER_EMAIL")

    send_email(jobs, sender, password, receiver)
    print(" Job email sent")
