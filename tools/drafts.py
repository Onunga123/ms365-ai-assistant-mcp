from graph_client import graph_get, graph_post, graph_patch, graph_delete

def register_drafts_tools(mcp):

    @mcp.tool()
    def create_draft_email(user_id: str, to_address: str, subject: str, body: str):
        """Create a draft email without sending it — for human review before sending"""
        data = {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": body
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": to_address
                    }
                }
            ]
        }
        return graph_post(f"users/{user_id}/messages", data)

    @mcp.tool()
    def send_draft_email(user_id: str, message_id: str):
        """Send a previously created draft email"""
        return graph_post(f"users/{user_id}/messages/{message_id}/send", {})

    @mcp.tool()
    def update_draft_email(user_id: str, message_id: str, subject: str = None, body: str = None, to_address: str = None):
        """Update an existing draft email before sending"""
        data = {}
        if subject:
            data["subject"] = subject
        if body:
            data["body"] = {"contentType": "Text", "content": body}
        if to_address:
            data["toRecipients"] = [{"emailAddress": {"address": to_address}}]
        return graph_patch(f"users/{user_id}/messages/{message_id}", data)

    @mcp.tool()
    def move_email(user_id: str, message_id: str, destination_folder_id: str):
        """Move an email to a different folder"""
        data = {"destinationId": destination_folder_id}
        return graph_post(f"users/{user_id}/messages/{message_id}/move", data)

    @mcp.tool()
    def delete_email(user_id: str, message_id: str):
        """Delete an email permanently"""
        return graph_delete(f"users/{user_id}/messages/{message_id}")

    @mcp.tool()
    def list_draft_emails(user_id: str):
        """List all draft emails for a user"""
        return graph_get(f"users/{user_id}/mailFolders/Drafts/messages")