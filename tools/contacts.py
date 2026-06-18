from graph_client import graph_get, graph_post, graph_patch, graph_delete, graph_get_all
def register_contacts_tools(mcp):

    @mcp.tool()
    def list_contacts(user_id: str):
        """List all contacts for a user"""
        return graph_get_all(f"users/{user_id}/contacts?$select=id,displayName,emailAddresses,mobilePhone,jobTitle,companyName")
    @mcp.tool()
    def get_contact(user_id: str, contact_id: str):
        """Get details of a specific contact"""
        return graph_get(f"users/{user_id}/contacts/{contact_id}")

    @mcp.tool()
    def create_contact(user_id: str, first_name: str, last_name: str, email: str = "", mobile: str = "", job_title: str = "", company: str = ""):
        """Create a new contact for a user"""
        data = {
            "givenName": first_name,
            "surname": last_name,
            "emailAddresses": [
                {
                    "address": email,
                    "name": f"{first_name} {last_name}"
                }
            ] if email else [],
            "mobilePhone": mobile,
            "jobTitle": job_title,
            "companyName": company
        }
        return graph_post(f"users/{user_id}/contacts", data)

    @mcp.tool()
    def update_contact(user_id: str, contact_id: str, first_name: str = None, last_name: str = None, mobile: str = None, job_title: str = None):
        """Update an existing contact"""
        data = {}
        if first_name:
            data["givenName"] = first_name
        if last_name:
            data["surname"] = last_name
        if mobile:
            data["mobilePhone"] = mobile
        if job_title:
            data["jobTitle"] = job_title
        return graph_patch(f"users/{user_id}/contacts/{contact_id}", data)

    @mcp.tool()
    def delete_contact(user_id: str, contact_id: str):
        """Delete a contact"""
        return graph_delete(f"users/{user_id}/contacts/{contact_id}")

    @mcp.tool()
    def list_contact_folders(user_id: str):
        """List all contact folders for a user"""
        return graph_get(f"users/{user_id}/contactFolders")