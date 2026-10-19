import os
import zoneinfo  # Python 3.9+ standard library

from graph_client import graph_get, graph_post, graph_patch, graph_delete

_DEFAULT_TIMEZONE_FALLBACK = "Africa/Nairobi"


def _get_default_timezone() -> str:
    """Return the configured default IANA timezone for calendar events.

    Reads DEFAULT_TIMEZONE from the environment, falling back to Africa/Nairobi
    when unset or empty. An explicitly configured value is validated against the
    IANA timezone database via zoneinfo; an invalid value raises a clear,
    non-sensitive error rather than silently substituting another timezone.
    """
    configured = os.getenv("DEFAULT_TIMEZONE")
    if not configured or not configured.strip():
        return _DEFAULT_TIMEZONE_FALLBACK
    tz_name = configured.strip()
    try:
        zoneinfo.ZoneInfo(tz_name)
    except Exception as exc:
        raise Exception(
            f"DEFAULT_TIMEZONE is set to an invalid IANA timezone '{tz_name}'. "
            f"Use a valid timezone name (for example 'Africa/Nairobi', 'UTC', "
            f"'Europe/London') or leave it unset to use the default."
        ) from exc
    return tz_name


def register_calendar_tools(mcp):

    @mcp.tool()
    def list_events(user_id: str, top: int = 10):
        """List upcoming calendar events for a user"""
        return graph_get(f"users/{user_id}/events?$top={top}&$orderby=start/dateTime")

    @mcp.tool()
    def get_event(user_id: str, event_id: str):
        """Get details of a specific calendar event"""
        return graph_get(f"users/{user_id}/events/{event_id}")

    @mcp.tool()
    def create_event(user_id: str, subject: str, start: str, end: str, body: str = "", attendees: str = ""):
        """Create a new calendar event. start and end format: '2026-06-12T10:00:00'. attendees: comma separated emails"""
        tz = _get_default_timezone()
        data = {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "start": {
                "dateTime": start,
                "timeZone": tz
            },
            "end": {
                "dateTime": end,
                "timeZone": tz
            }
        }
        if attendees:
            data["attendees"] = [
                {
                    "emailAddress": {"address": email.strip()},
                    "type": "required"
                }
                for email in attendees.split(",")
            ]
        return graph_post(f"users/{user_id}/events", data)

    @mcp.tool()
    def update_event(user_id: str, event_id: str, subject: str = None, start: str = None, end: str = None):
        """Update an existing calendar event"""
        tz = _get_default_timezone()
        data = {}
        if subject:
            data["subject"] = subject
        if start:
            data["start"] = {"dateTime": start, "timeZone": tz}
        if end:
            data["end"] = {"dateTime": end, "timeZone": tz}
        return graph_patch(f"users/{user_id}/events/{event_id}", data)

    @mcp.tool()
    def delete_event(user_id: str, event_id: str):
        """Delete a calendar event"""
        return graph_delete(f"users/{user_id}/events/{event_id}")

    @mcp.tool()
    def list_calendars(user_id: str):
        """List all calendars for a user"""
        return graph_get(f"users/{user_id}/calendars")
