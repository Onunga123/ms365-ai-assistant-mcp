import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from auth import get_token, REQUEST_TIMEOUT
from logger import log_action

BASE_URL = "https://graph.microsoft.com/v1.0"

def graph_get(endpoint):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        raise Exception("Graph API request timed out. Please try again later.")
    except requests.exceptions.RequestException:
        raise Exception("Graph API is unavailable. Please try again later.")
    log_action("GET", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201]:
        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")
    return response.json()

def graph_post(endpoint, data):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            json=data,
            timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        raise Exception("Graph API request timed out. Please try again later.")
    except requests.exceptions.RequestException:
        raise Exception("Graph API is unavailable. Please try again later.")
    log_action("POST", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201]:
        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")
    return response.json()

def graph_patch(endpoint, data, etag=None):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    if etag:
        headers["If-Match"] = etag
    try:
        response = requests.patch(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            json=data,
            timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        raise Exception("Graph API request timed out. Please try again later.")
    except requests.exceptions.RequestException:
        raise Exception("Graph API is unavailable. Please try again later.")
    log_action("PATCH", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 201, 204]:
        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")
    return {"status": "success"}

def graph_delete(endpoint, etag=None):
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    if etag:
        headers["If-Match"] = etag
    try:
        response = requests.delete(
            f"{BASE_URL}/{endpoint}",
            headers=headers,
            timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.Timeout:
        raise Exception("Graph API request timed out. Please try again later.")
    except requests.exceptions.RequestException:
        raise Exception("Graph API is unavailable. Please try again later.")
    log_action("DELETE", {"endpoint": endpoint, "status": response.status_code})
    if response.status_code not in [200, 204]:
        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")
    return {"status": "deleted successfully"}
