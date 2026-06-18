import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import requests
from auth import get_token
from logger import log_action

BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_RETRIES = 3

def _make_request(method: str, endpoint: str, data=None, etag=None):
    for attempt in range(MAX_RETRIES):
        token = get_token()
        headers = {
            "Authorization": f"Bearer {token}"
        }
        if data is not None:
            headers["Content-Type"] = "application/json"
        if etag:
            headers["If-Match"] = etag

        url = f"{BASE_URL}/{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)

        log_action(method, {
            "endpoint": endpoint,
            "status": response.status_code,
            "attempt": attempt + 1
        })

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            print(f"Rate limited. Waiting {retry_after} seconds before retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            try:
                from notifier import alert_api_error
                alert_api_error(endpoint, response.status_code, response.text)
            except Exception:
                pass

        if method == "DELETE" and response.status_code in [200, 204]:
            return {"status": "deleted successfully"}

        if method == "PATCH" and response.status_code in [200, 201, 204]:
            return {"status": "success"}

        if response.status_code in [200, 201]:
            if response.content:
                return response.json()
            return {"status": "success"}

        raise Exception(f"Graph API error {response.status_code}: {response.text}")

    raise Exception(f"Max retries exceeded after {MAX_RETRIES} attempts")

def graph_get_all(endpoint, max_items=None):
    """Fetch all pages of results from a Graph API endpoint"""
    all_items = []
    url = f"{BASE_URL}/{endpoint}"
    max_items = max_items or int(os.getenv("MAX_TOP", "200"))

    while url and len(all_items) < max_items:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)

        log_action("GET_PAGED", {
            "endpoint": endpoint,
            "status": response.status_code,
            "items_so_far": len(all_items)
        })

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 10))
            print(f"Rate limited. Waiting {retry_after} seconds")
            time.sleep(retry_after)
            continue

        if response.status_code not in [200, 201]:
            raise Exception(f"Graph API error {response.status_code}: {response.text}")

        data = response.json()
        items = data.get("value", [])
        all_items.extend(items)

        url = data.get("@odata.nextLink")

        if len(all_items) >= max_items:
            all_items = all_items[:max_items]
            break

    return {
        "@odata.context": f"Paginated results from {endpoint}",
        "total_returned": len(all_items),
        "value": all_items
    }
def graph_get(endpoint):
    return _make_request("GET", endpoint)

def graph_post(endpoint, data):
    return _make_request("POST", endpoint, data=data)

def graph_patch(endpoint, data, etag=None):
    return _make_request("PATCH", endpoint, data=data, etag=etag)

def graph_delete(endpoint, etag=None):
    return _make_request("DELETE", endpoint, etag=etag)