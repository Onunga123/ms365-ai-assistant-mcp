from graph_client import graph_get, graph_post

def register_meetings_tools(mcp):

    @mcp.tool()
    def list_online_meetings(user_id: str):
        """List all online meetings for a user"""
        return graph_get(f"users/{user_id}/onlineMeetings")

    @mcp.tool()
    def get_online_meeting(user_id: str, meeting_id: str):
        """Get details of a specific online meeting"""
        return graph_get(f"users/{user_id}/onlineMeetings/{meeting_id}")

    @mcp.tool()
    def create_online_meeting(user_id: str, subject: str, start: str, end: str):
        """Create a new online Teams meeting. start and end format: '2026-06-12T10:00:00'"""
        data = {
            "subject": subject,
            "startDateTime": f"{start}Z",
            "endDateTime": f"{end}Z"
        }
        return graph_post(f"users/{user_id}/onlineMeetings", data)

    @mcp.tool()
    def get_meeting_transcript(meeting_id: str):
        """Get the transcript of a Teams meeting by meeting ID"""
        return graph_get(f"communications/callRecords/{meeting_id}?$expand=sessions($expand=segments)")

    @mcp.tool()
    def list_meeting_attendance(meeting_id: str):
        """Get attendance report for a Teams meeting"""
        return graph_get(f"communications/callRecords/{meeting_id}")

    @mcp.tool()
    def list_call_records():
        """List recent Teams call and meeting records in the tenant"""
        return graph_get("communications/callRecords?$top=10&$orderby=startDateTime desc")