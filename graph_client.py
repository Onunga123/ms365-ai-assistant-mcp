import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import requests
from auth import get_token, REQUEST_TIMEOUT
from logger import log_action

BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_RETRIES = 3
MAX_RETRY_AFTER = 60  # Upper bound on a single Retry-After sleep (seconds)
DEFAULT_RETRY_AFTER = 10  # Fallback used when the header is absent or malformed
RETRYABLE_5XX = {500, 502, 503, 504}  # Transient server errors eligible for a bounded retry


def _parse_retry_after(raw):
    """Parse a Retry-After header safely into a bounded, non-negative number of seconds."""
    if raw is None:
        return DEFAULT_RETRY_AFTER
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_RETRY_AFTER
    if value < 0:
        return 0
    if value > MAX_RETRY_AFTER:
        return MAX_RETRY_AFTER
    return value


def _is_idempotent(method: str) -> bool:
    """GET is safe to retry on transient failures; POST/PATCH/DELETE are not retried on 5xx."""
    return method == "GET"


def _bounded_backoff(attempt: int) -> float:
    """Linear backoff in seconds, capped to MAX_RETRY_AFTER."""
    return min(DEFAULT_RETRY_AFTER * (attempt + 1), MAX_RETRY_AFTER)


def _alert_5xx(status_code: int):
    """Best-effort 5xx alert; never raises into the caller's request path."""
    try:
        from notifier import alert_api_error
        alert_api_error(status_code)
    except Exception:
        pass


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

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
            elif method == "PATCH":
                response = requests.patch(url, headers=headers, json=data, timeout=REQUEST_TIMEOUT)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=REQUEST_TIMEOUT)
            else:
                raise ValueError("Unsupported Graph request method")
        except requests.exceptions.Timeout:
            raise Exception("Graph API request timed out. Please try again later.")
        except requests.exceptions.RequestException:
            raise Exception("Graph API is unavailable. Please try again later.")

        log_action(method, {
            "endpoint": endpoint,
            "status": response.status_code,
            "attempt": attempt + 1
        })

        if response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            print(f"Rate limited. Waiting {retry_after} seconds before retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(retry_after)
            continue

        # Transient 5xx: retry only idempotent reads, with a bounded backoff and bounded count.
        if (
            response.status_code in RETRYABLE_5XX
            and _is_idempotent(method)
            and attempt < MAX_RETRIES - 1
        ):
            time.sleep(_bounded_backoff(attempt))
            continue

        # Non-retried 5xx (or the final attempt): alert and fall through to a sanitized raise.
        if response.status_code >= 500:
            _alert_5xx(response.status_code)

        if method == "DELETE" and response.status_code in [200, 204]:
            return {"status": "deleted successfully"}

        if method == "PATCH" and response.status_code in [200, 201, 204]:
            return {"status": "success"}

        if response.status_code in [200, 201]:
            if response.content:
                return response.json()
            return {"status": "success"}

        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")

    raise Exception(f"Max retries exceeded after {MAX_RETRIES} attempts")

def graph_get_all(endpoint, max_items=None):
    """Fetch all pages of results from a Graph API endpoint"""
    all_items = []
    url = f"{BASE_URL}/{endpoint}"
    max_items = max_items or int(os.getenv("MAX_TOP", "200"))

    while url and len(all_items) < max_items:
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            raise Exception("Graph API request timed out. Please try again later.")
        except requests.exceptions.RequestException:
            raise Exception("Graph API is unavailable. Please try again later.")

        log_action("GET_PAGED", {
            "endpoint": endpoint,
            "status": response.status_code,
            "items_so_far": len(all_items)
        })

        if response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            print(f"Rate limited. Waiting {retry_after} seconds")
            time.sleep(retry_after)
            continue

        if response.status_code not in [200, 201]:
            raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")

        try:
            data = response.json()
        except ValueError:
            raise Exception("Graph API returned an invalid response.")
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

def graph_get_etag(endpoint):
    """Fetch the current ETag for a Graph resource.

    Used by Planner PATCH flows that require an ``If-Match`` header for optimistic
    concurrency. Returns the ETag string (or ``None`` if absent) without exposing the
    response body, so callers can perform safe conditional updates.
    """
    for attempt in range(MAX_RETRIES):
        token = get_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{BASE_URL}/{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            raise Exception("Graph API request timed out. Please try again later.")
        except requests.exceptions.RequestException:
            raise Exception("Graph API is unavailable. Please try again later.")

        log_action("GET", {"endpoint": endpoint, "status": response.status_code, "attempt": attempt + 1})

        if response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            print(f"Rate limited. Waiting {retry_after} seconds before retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(retry_after)
            continue

        if response.status_code in RETRYABLE_5XX and attempt < MAX_RETRIES - 1:
            time.sleep(_bounded_backoff(attempt))
            continue

        if response.status_code >= 500:
            _alert_5xx(response.status_code)

        if response.status_code == 200:
            return response.headers.get("ETag")

        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")

    raise Exception(f"Max retries exceeded after {MAX_RETRIES} attempts")

def graph_post_raw(endpoint, body, content_type):
    """POST a raw (non-JSON) body to Graph.

    OneNote page creation requires an ``application/xhtml+xml`` body and returns the
    created page as JSON. The shared ``_make_request`` helper assumes JSON bodies
    (``json=data``), which would re-encode the XHTML and break OneNote's endpoint
    contract. This helper preserves the caller's payload encoding and Content-Type
    while inheriting the shared timeout, bounded retry, and sanitized-error behavior.
    POST is non-idempotent, so transient 5xx responses are alerted and raised rather
    than retried (avoids creating duplicate pages).
    """
    for attempt in range(MAX_RETRIES):
        token = get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": content_type,
        }
        url = f"{BASE_URL}/{endpoint}"
        try:
            response = requests.post(url, headers=headers, data=body, timeout=REQUEST_TIMEOUT)
        except requests.exceptions.Timeout:
            raise Exception("Graph API request timed out. Please try again later.")
        except requests.exceptions.RequestException:
            raise Exception("Graph API is unavailable. Please try again later.")

        log_action("POST", {"endpoint": endpoint, "status": response.status_code, "attempt": attempt + 1})

        if response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            print(f"Rate limited. Waiting {retry_after} seconds before retry {attempt + 1}/{MAX_RETRIES}")
            time.sleep(retry_after)
            continue

        if response.status_code >= 500:
            _alert_5xx(response.status_code)

        if response.status_code in [200, 201]:
            if response.content:
                return response.json()
            return {"status": "success"}

        raise Exception(f"Graph API request failed with HTTP status {response.status_code}.")

    raise Exception(f"Max retries exceeded after {MAX_RETRIES} attempts")
