from graph_client import graph_get, graph_post, graph_patch, graph_delete

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
        data = {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "start": {
                "dateTime": start,
                "timeZone": "Africa/Nairobi"
            },
            "end": {
                "dateTime": end,
                "timeZone": "Africa/Nairobi"
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
        data = {}
        if subject:
            data["subject"] = subject
        if start:
            data["start"] = {"dateTime": start, "timeZone": "Africa/Nairobi"}
        if end:
            data["end"] = {"dateTime": end, "timeZone": "Africa/Nairobi"}
        return graph_patch(f"users/{user_id}/events/{event_id}", data)

    @mcp.tool()
    def delete_event(user_id: str, event_id: str):
        """Delete a calendar event"""
        return graph_delete(f"users/{user_id}/events/{event_id}")

    @mcp.tool()
    def list_calendars(user_id: str):
        """List all calendars for a user"""
        return graph_get(f"users/{user_id}/calendars")