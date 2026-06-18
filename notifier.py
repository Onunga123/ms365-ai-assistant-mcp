import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

ALERT_EMAIL = os.getenv("ALERT_EMAIL")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT")

_last_notification_time = {}
NOTIFICATION_COOLDOWN = 3600

def send_alert(subject: str, message: str, alert_type: str = "general"):
    current_time = time.time()
    last_time = _last_notification_time.get(alert_type, 0)
    if current_time - last_time < NOTIFICATION_COOLDOWN:
        return False

    if not all([ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_RECIPIENT]):
        print(f"ALERT [{subject}]: {message}")
        print("Email notifications not configured — add ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_RECIPIENT to .env")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = ALERT_EMAIL
        msg["To"] = ALERT_RECIPIENT
        msg["Subject"] = f"[M365 AI Assistant] {subject}"

        body = f"""
Microsoft 365 AI Assistant-System Alert

{message}

Time: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
Server: M365 Server
        """
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.sendmail(ALERT_EMAIL, ALERT_RECIPIENT, msg.as_string())

        _last_notification_time[alert_type] = current_time
        print(f"Alert sent: {subject}")
        return True

    except Exception as e:
        print(f"Failed to send alert: {str(e)}")
        return False


def alert_auth_failure(error: str):
    send_alert(
        subject="Authentication Failure",
        message=f"Microsoft Graph authentication failed.\n\nError: {error}\n\nAction required: Check CLIENT_SECRET validity in Azure portal.",
        alert_type="auth_failure"
    )


def alert_api_error(endpoint: str, status_code: int, error: str):
    if status_code >= 500:
        send_alert(
            subject=f"API Error {status_code}",
            message=f"Microsoft Graph API returned error {status_code}.\n\nEndpoint: {endpoint}\nError: {error}\n\nThis may indicate a Microsoft service issue.",
            alert_type="api_error"
        )


def alert_secret_expiry(days_remaining: int, expiry_date: str):
    if days_remaining < 30:
        send_alert(
            subject=f"Client Secret Expiring in {days_remaining} Days",
            message=f"The Microsoft 365 client secret expires on {expiry_date}.\n\nAction required: Rotate the secret in Azure Entra ID and update the configuration before expiry.",
            alert_type="secret_expiry"
        )