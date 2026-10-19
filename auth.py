import os
import time
import requests
from logger import redact

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
REQUEST_TIMEOUT = 30

_token_cache = None
_token_expiry = 0


def get_token():
    global _token_cache, _token_expiry
    current_time = time.time()
    if _token_cache and current_time < _token_expiry:
        return _token_cache
    token_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }
    try:
        response = requests.post(TOKEN_URL, data=token_data, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.Timeout:
        raise Exception("Authentication service timed out. Please try again later.")
    except requests.exceptions.RequestException:
        raise Exception("Authentication service is unavailable. Please try again later.")
    if response.status_code != 200:
        try:
            from notifier import alert_auth_failure
            alert_auth_failure(f"HTTP status {response.status_code}")
        except Exception:
            pass
        raise Exception(f"Authentication failed with HTTP status {response.status_code}.")
    try:
        data = response.json()
        _token_cache = data["access_token"]
        _token_expiry = current_time + data["expires_in"] - 60
    except (ValueError, KeyError, TypeError):
        raise Exception("Authentication service returned an invalid response.")
    return _token_cache


def verify_server_key():
    api_key = os.getenv("MCP_API_KEY")
    if not api_key:
        raise Exception("MCP_API_KEY environment variable not set. Server startup aborted.")
    return True