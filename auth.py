import os
import time
import requests

CLIENT_ID = os.getenv("CLIENT_ID")
TENANT_ID = os.getenv("TENANT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

TOKEN_URL = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"

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
    response = requests.post(TOKEN_URL, data=token_data)
    if response.status_code != 200:
        try:
            from notifier import alert_auth_failure
            alert_auth_failure(response.text)
        except Exception:
            pass
        raise Exception(f"Authentication failed: {response.text}")
    data = response.json()
    _token_cache = data["access_token"]
    _token_expiry = current_time + data["expires_in"] - 60
    return _token_cache


def verify_server_key():
    api_key = os.getenv("MCP_API_KEY")
    if not api_key:
        raise Exception("MCP_API_KEY environment variable not set. Server startup aborted.")
    return True