from graph_client import graph_get, graph_post

def register_shared_mailbox_tools(mcp):

    @mcp.tool()
    def list_shared_mailbox_messages(mailbox_address: str, top: int = 10):
        """List messages in a shared mailbox. mailbox_address is the email e.g. info@company.com"""
        return graph_get(f"users/{mailbox_address}/messages?$top={top}&$orderby=receivedDateTime desc")

    @mcp.tool()
    def send_from_shared_mailbox(mailbox_address: str, to_address: str, subject: str, body: str):
        """Send an email from a shared mailbox"""
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
            },
            "saveToSentItems": True
        }
        return graph_post(f"users/{mailbox_address}/sendMail", data)

    @mcp.tool()
    def list_shared_mailbox_folders(mailbox_address: str):
        """List all mail folders in a shared mailbox"""
        return graph_get(f"users/{mailbox_address}/mailFolders")

    @mcp.tool()
    def get_shared_mailbox_message(mailbox_address: str, message_id: str):
        """Get full content of a specific message in a shared mailbox"""
        return graph_get(f"users/{mailbox_address}/messages/{message_id}")

    @mcp.tool()
    def reply_shared_mailbox(mailbox_address: str, message_id: str, reply_body: str):
        """Reply to an email in a shared mailbox"""
        data = {
            "message": {
                "body": {
                    "contentType": "Text",
                    "content": reply_body
                }
            }
        }
        return graph_post(f"users/{mailbox_address}/messages/{message_id}/reply", data)