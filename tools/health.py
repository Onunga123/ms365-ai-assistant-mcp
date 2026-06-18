import os
import time
import requests
from auth import get_token, TOKEN_URL, CLIENT_ID, TENANT_ID

def register_health_tools(mcp):

    @mcp.tool()
    def health_check():
        """Check if the MCP server is running and Microsoft Graph API is reachable"""
        results = {
            "server_status": "online",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "tenant_id": TENANT_ID,
            "client_id": CLIENT_ID,
            "authentication": "unknown",
            "graph_api": "unknown"
        }

        try:
            token = get_token()
            results["authentication"] = "success"
        except Exception as e:
            results["authentication"] = f"failed: {str(e)}"
            return results

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "https://graph.microsoft.com/v1.0/$metadata",
                headers=headers
            )
            if response.status_code == 200:
                results["graph_api"] = "reachable"
            else:
                results["graph_api"] = f"error: {response.status_code}"
        except Exception as e:
            results["graph_api"] = f"unreachable: {str(e)}"

        return results

    @mcp.tool()
    def check_secret_expiry():
        """Check when the current client secret expires and warn if expiry is within 60 days"""
        secret_expiry = os.getenv("SECRET_EXPIRY_DATE")

        if not secret_expiry:
            return {
                "status": "unknown",
                "message": "SECRET_EXPIRY_DATE environment variable not set. Add it to your .env file in format YYYY-MM-DD"
            }

        from datetime import datetime
        try:
            expiry_date = datetime.strptime(secret_expiry, "%Y-%m-%d")
            days_remaining = (expiry_date - datetime.utcnow()).days

            if days_remaining < 0:
                status = "expired"
                message = f"SECRET EXPIRED {abs(days_remaining)} days ago. Rotate immediately."
            elif days_remaining < 30:
                status = "critical"
                message = f"Secret expires in {days_remaining} days. Rotate immediately."
            elif days_remaining < 60:
                status = "warning"
                message = f"Secret expires in {days_remaining} days. Plan rotation soon."
            else:
                status = "ok"
                message = f"Secret expires in {days_remaining} days on {secret_expiry}."

            return {
                "status": status,
                "expiry_date": secret_expiry,
                "days_remaining": days_remaining,
                "message": message
            }
        except ValueError:
            return {
                "status": "error",
                "message": "SECRET_EXPIRY_DATE format incorrect. Use YYYY-MM-DD"
            }

    @mcp.tool()
    def test_notification():
        """Send a test alert notification to verify the email notification system is working"""
        from notifier import send_alert
        result = send_alert(
            subject="Test Notification",
            message="This is a test notification from the Pharo AI Chief of Staff system. If you received this email the notification system is working correctly.",
            alert_type="test"
        )
        if result:
            return {"status": "success", "message": "Test notification sent successfully"}
        else:
            return {
                "status": "not_configured",
                "message": "Notification sent to console only. To enable email alerts add ALERT_EMAIL, ALERT_EMAIL_PASSWORD and ALERT_RECIPIENT to your .env file and Claude Desktop config."
            }