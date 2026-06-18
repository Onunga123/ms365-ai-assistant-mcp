import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from auth import get_token
from logger import log_action

BASE_URL = "https://graph.microsoft.com/v1.0"

def graph_get(endpoint):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers=headers
    )
    log_action("GET", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201]:
        raise Exception(f"Graph API error: {response.text}")
    return response.json()

def graph_post(endpoint, data):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        json=data
    )
    log_action("POST", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201]:
        raise Exception(f"Graph API error: {response.text}")
    return response.json()

def graph_patch(endpoint, data, etag=None):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    if etag:
        headers["If-Match"] = etag
    response = requests.patch(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        json=data
    )
    log_action("PATCH", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201, 204]:
        raise Exception(f"Graph API error: {response.text}")
    return {"status": "success"}

def graph_delete(endpoint, etag=None):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    if etag:
        headers["If-Match"] = etag
    response = requests.delete(
        f"{BASE_URL}/{endpoint}",
        headers=headers
    )
    log_action("DELETE", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 204]:
        raise Exception(f"Graph API error: {response.text}")
    return {"status": "deleted successfully"}