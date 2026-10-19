import os
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from logger import redact

ALERT_EMAIL = os.getenv("ALERT_EMAIL")
ALERT_EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT")

_last_notification_time = {}
NOTIFICATION_COOLDOWN = 3600

_DEFAULT_SMTP_HOST = "smtp.gmail.com"
_DEFAULT_SMTP_PORT = 465


def _get_smtp_host() -> str:
    """Return the configured SMTP host, defaulting to smtp.gmail.com when unset or empty."""
    host = os.getenv("SMTP_HOST")
    if not host or not host.strip():
        return _DEFAULT_SMTP_HOST
    return host.strip()


def _get_smtp_port() -> int:
    """Return the configured SMTP port, defaulting to 465 when unset or empty.

    Validates SMTP_PORT as an integer in the valid TCP port range (1-65535). An
    invalid or out-of-range value raises a clear, non-sensitive error rather than
    silently substituting a port. Credentials are never included in the message.
    """
    raw = os.getenv("SMTP_PORT")
    if raw is None or raw.strip() == "":
        return _DEFAULT_SMTP_PORT
    raw = raw.strip()
    try:
        port = int(raw)
    except ValueError:
        raise Exception(f"SMTP_PORT must be an integer in the range 1-65535 (got '{raw}').")
    if not (1 <= port <= 65535):
        raise Exception(f"SMTP_PORT {port} is out of range; must be an integer in 1-65535.")
    return port

def send_alert(subject: str, message: str, alert_type: str = "general"):
    subject = redact(subject)
    message = redact(message)
    current_time = time.time()
    last_time = _last_notification_time.get(alert_type, 0)
    if current_time - last_time < NOTIFICATION_COOLDOWN:
        return False

    if not all([ALERT_EMAIL, ALERT_EMAIL_PASSWORD, ALERT_RECIPIENT]):
        print("Alert notification was not sent because email notifications are not configured.")
        return False

    # Resolve and validate SMTP configuration before the try block so an invalid
    # port/host raises a clear error rather than being swallowed into a generic
    # notification-service failure.
    smtp_host = _get_smtp_host()
    smtp_port = _get_smtp_port()

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

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(ALERT_EMAIL, ALERT_EMAIL_PASSWORD)
            server.sendmail(ALERT_EMAIL, ALERT_RECIPIENT, msg.as_string())

        _last_notification_time[alert_type] = current_time
        print("Alert notification sent.")
        return True

    except Exception:
        print("Failed to send alert due to a notification service error.")
        return False


def alert_auth_failure(error: str):
    send_alert(
        subject="Authentication Failure",
        message=f"Microsoft Graph authentication failed.\n\nError: {error}\n\nAction required: Check CLIENT_SECRET validity in Azure portal.",
        alert_type="auth_failure"
    )


def alert_api_error(status_code: int):
    if status_code >= 500:
        send_alert(
            subject=f"API Error {status_code}",
            message=f"Microsoft Graph API returned HTTP status {status_code}.\n\nThis may indicate a Microsoft service issue.",
            alert_type="api_error"
        )


def alert_secret_expiry(days_remaining: int, expiry_date: str):
    if days_remaining < 30:
        send_alert(
            subject=f"Client Secret Expiring in {days_remaining} Days",
            message=f"The Microsoft 365 client secret expires on {expiry_date}.\n\nAction required: Rotate the secret in Azure Entra ID and update the configuration before expiry.",
            alert_type="secret_expiry"
        )