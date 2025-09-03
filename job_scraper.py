# job_scraper.py
import os, re, json, time
from urllib.parse import urljoin
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

# ------------ CONFIG ------------
KEYWORDS = [
    "entry level", "fresher", "graduate",
    "data analyst", "data analytics",
    "ml intern", "machine learning intern",
    "ml engineer", "machine learning engineer",
    "data engineer",
    "bde", "business development executive",
    "e-learning", "content developer"
]

# Prioritize company career pages (add more later)
COMPANY_PAGES = {
    "Zensar": "https://www.zensar.com/careers",
    "Persistent Systems": "https://www.persistent.com/careers/",
    "Infosys": "https://career.infosys.com/joblist",
    "Tech Mahindra": "https://careers.techmahindra.com/",
    "TCS": "https://www.tcs.com/careers",
    "Cognizant": "https://careers.cognizant.com/global-en/jobs",
    "Wipro": "https://careers.wipro.com/careers-home/",
    "Capgemini": "https://www.capgemini.com/careers/",
}

SEEN_FILE = "seen_jobs.txt"   # stored in repo to avoid duplicates day-to-day
MAX_LINKS_PER_SITE = 40       # safety cap
REQUEST_TIMEOUT = 20

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/119.0 Safari/537.36"
)

# ------------ UTILS ------------
def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(l.strip() for l in f if l.strip())

def save_seen(seen_set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        for item in sorted(seen_set):
            f.write(item + "\n")

def is_keyword_hit(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in KEYWORDS)

def fetch(url: str) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.text

def extract_links(base_url: str, html: str):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        title = (a.get_text() or "").strip()
        href = urljoin(base_url, a["href"].strip())
        # ignore anchors / mailto / js
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        links.append((title, href))
        if len(links) >= MAX_LINKS_PER_SITE:
            break
    return links

# ------------ SCRAPER ------------
def scrape_all():
    results = []  # list of dicts: {company,title,url}
    for company, url in COMPANY_PAGES.items():
        try:
            html = fetch(url)
            # quick whole-page hit (sometimes listings are rendered server-side)
            if is_keyword_hit(BeautifulSoup(html, "html.parser").get_text(" ")):
                results.append({"company": company, "title": f"[Page match] {company} Careers", "url": url})

            # scan links on that page and keyword-filter titles/hrefs
            for title, link in extract_links(url, html):
                hay = f"{title} {link}"
                if is_keyword_hit(hay):
                    results.append({"company": company, "title": title or "Open role", "url": link})
        except Exception as e:
            results.append({"company": company, "title": f"Error: {e}", "url": url})
    return dedupe(results)

def dedupe(items):
    seen = set()
    out = []
    for it in items:
        key = (it["company"], it["title"].lower(), it["url"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out

# ------------ EMAIL ------------
def send_email_html(rows):
    sender = os.getenv("EMAIL_USER")
    app_pass = os.getenv("EMAIL_PASS")
    receiver = os.getenv("RECEIVER_EMAIL") or sender

    if not sender or not app_pass:
        raise RuntimeError("EMAIL_USER / EMAIL_PASS not set as env vars (GitHub Secrets).")

    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    subject = f"Daily Job Alert — {now} (IST)"

    if rows:
        table_rows = "".join(
            f"<tr><td>{r['company']}</td><td>{escape_html(r['title'])}</td>"
            f"<td><a href='{r['url']}' target='_blank'>{r['url']}</a></td></tr>"
            for r in rows
        )
        html_body = f"""
        <html><body>
        <h3>Fresh roles matching your filters</h3>
        <table border="1" cellpadding="6" cellspacing="0">
          <tr><th>Company</th><th>Title</th><th>Link</th></tr>
          {table_rows}
        </table>
        <p style="color:#666;font-size:12px">Keywords: {", ".join(KEYWORDS)}</p>
        </body></html>
        """
        text_body = "\n".join([f"{r['company']} | {r['title']} | {r['url']}" for r in rows])
    else:
        html_body = "<html><body><p>No new roles today.</p></body></html>"
        text_body = "No new roles today."

    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(sender, app_pass)
        s.sendmail(sender, receiver, msg.as_string())

def escape_html(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# ------------ MAIN ------------
if __name__ == "__main__":
    all_hits = scrape_all()

    # filter out already-seen links
    seen = load_seen()
    fresh = []
    for r in all_hits:
        key = f"{r['company']}||{r['title']}||{r['url']}"
        if key not in seen and not r["title"].lower().startswith("error:"):
            fresh.append(r)
            seen.add(key)

    # send email (fresh only; if none, you'll get a "no new roles" message)
    send_email_html(fresh)

    # persist new seen set (so tomorrow you only get new stuff)
    save_seen(seen)

    # optional console log
    print(f"Found {len(all_hits)} hits; emailed {len(fresh)} fresh; seen_db size={len(seen)}")
