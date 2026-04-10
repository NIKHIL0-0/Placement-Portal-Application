import csv
import json
import os
import smtplib
from urllib import request as urllib_request
from email.mime.text import MIMEText


def send_email(config, to_email: str, subject: str, html_body: str) -> bool:
    if not config.get("SMTP_USER") or not config.get("SMTP_PASS"):
        return False

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = config["SMTP_FROM"]
    msg["To"] = to_email

    try:
        with smtplib.SMTP(config["SMTP_HOST"], config["SMTP_PORT"]) as server:
            server.starttls()
            server.login(config["SMTP_USER"], config["SMTP_PASS"])
            server.sendmail(config["SMTP_FROM"], [to_email], msg.as_string())
        return True
    except (smtplib.SMTPException, OSError):
        # Keep background tasks resilient even when SMTP provider throttles.
        return False


def send_google_chat_message(config, text: str) -> bool:
    webhook_url = config.get("GOOGLE_CHAT_WEBHOOK_URL", "")
    if not webhook_url:
        return False

    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib_request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        return 200 <= response.status < 300


def write_csv(file_path: str, rows: list, headers: list) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
