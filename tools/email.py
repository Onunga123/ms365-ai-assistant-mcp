from graph_client import graph_get, graph_post, graph_get_all

def register_email_tools(mcp):

    @mcp.tool()
    def list_emails(user_id: str, top: int = 50):
        """List the most recent emails for a user. top = number of emails to return (default 50)"""
        return graph_get_all(f"users/{user_id}/messages?$top={top}&$orderby=receivedDateTime desc", max_items=top)

    @mcp.tool()
    def get_email(user_id: str, message_id: str, format: str = "text"):
        """Get the full content of a specific email. format options: text or html"""
        import os
        body_format = os.getenv("EMAIL_BODY_FORMAT", format)
        if body_format == "html":
            return graph_get(f"users/{user_id}/messages/{message_id}?$select=id,subject,from,toRecipients,receivedDateTime,body")
        return graph_get(f"users/{user_id}/messages/{message_id}?$select=id,subject,from,toRecipients,receivedDateTime,bodyPreview")
    
    @mcp.tool()
    def send_email(user_id: str, to_address: str, subject: str, body: str):
        """Send an email from a user"""
        data = {
            "message": {
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
        }
        return graph_post(f"users/{user_id}/sendMail", data)

    @mcp.tool()
    def reply_to_email(user_id: str, message_id: str, reply_body: str):
        """Reply to an existing email"""
        data = {
            "message": {
                "body": {
                    "contentType": "Text",
                    "content": reply_body
                }
            }
        }
        return graph_post(f"users/{user_id}/messages/{message_id}/reply", data)

    @mcp.tool()
    def search_emails(user_id: str, search_query: str):
        """Search emails by keyword"""
        return graph_get_all(f"users/{user_id}/messages?$search=\"{search_query}\"")

    @mcp.tool()
    def list_mail_folders(user_id: str):
        """List all mail folders for a user"""
        return graph_get(f"users/{user_id}/mailFolders")