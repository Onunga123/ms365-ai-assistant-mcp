"""Phase C2: focused mocked unit tests for the 15 previously under-tested
tool modules in the ms365-ai-assistant-mcp repository.

Each test verifies **request construction** — that the registered tool calls
the expected ``graph_get``/``graph_post``/``graph_patch``/``graph_delete``/
``graph_get_all`` helper with the expected endpoint string and (where
applicable) the expected ``data`` dict. All HTTP, Microsoft Graph, sleep, and
notification side effects are mocked. No live credentials, network, or email.

Reuses the patterns (FakeMCP, env-setup block, ``patch.object(mod, "graph_*")``)
established in ``tests/test_p1.py``. The timezone behaviour of
``tools/calendar.py`` and ``tools/todo.py`` and the planner/onenote/health
flows are already covered by ``tests/test_p1.py`` and are NOT duplicated here.

Run with:
    python3 -m unittest tests.test_tools -v
"""

import os
import sys
import unittest
from unittest.mock import patch

# Make the repo root importable so `import auth`, `import graph_client`,
# `import tools.email`, etc. work.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# Production modules read some configuration from the environment at import
# time (auth.CLIENT_ID/TENANT_ID/CLIENT_SECRET; logger.VERBOSE/SILENT/REDACT_PII).
# Set deterministic non-secret test values BEFORE importing them.
os.environ.setdefault("CLIENT_ID", "test-client-id")
os.environ.setdefault("TENANT_ID", "test-tenant-id")
os.environ.setdefault("CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("MCP_API_KEY", "test-api-key")
os.environ.setdefault("REDACT_PII", "true")
os.environ.setdefault("VERBOSE_LOGGING", "false")
os.environ.setdefault("SILENT", "true")  # keep the test output clean

# Tool modules under test (each module does `from graph_client import graph_*`
# at the top, so patching `tools.<mod>.graph_*` is the correct interception
# point — exactly the pattern used in tests/test_p1.py).
import tools.email as email_mod  # noqa: E402
import tools.calendar as calendar_mod  # noqa: E402
import tools.teams as teams_mod  # noqa: E402
import tools.contacts as contacts_mod  # noqa: E402
import tools.meetings as meetings_mod  # noqa: E402
import tools.drafts as drafts_mod  # noqa: E402
import tools.shared_mailbox as shared_mailbox_mod  # noqa: E402
import tools.presence as presence_mod  # noqa: E402
import tools.onedrive as onedrive_mod  # noqa: E402
import tools.sharepoint as sharepoint_mod  # noqa: E402
import tools.todo as todo_mod  # noqa: E402
import tools.excel as excel_mod  # noqa: E402
import tools.search as search_mod  # noqa: E402
import tools.users as users_mod  # noqa: E402
import tools.audit as audit_mod  # noqa: E402


class FakeMCP:
    """Minimal stand-in for FastMCP that captures @mcp.tool()-decorated functions.

    Copied verbatim from tests/test_p1.py to reuse the established pattern without
    importing that module (which would pull in its full test surface).
    """

    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _register(mod, register_fn_name):
    """Register a module's tools on a fresh FakeMCP and return the captured dict."""
    fake = FakeMCP()
    getattr(mod, register_fn_name)(fake)
    return fake.tools


# ---------------------------------------------------------------------------
# tools/email.py — send_email payload, get_email format branching, list_emails
# ---------------------------------------------------------------------------

class TestEmailTools(unittest.TestCase):

    def test_send_email_routes_through_graph_post_with_message_payload(self):
        tools = _register(email_mod, "register_email_tools")
        with patch.object(email_mod, "graph_post", return_value={"status": "ok"}) as m:
            tools["send_email"]("user-1", "to@x.com", "subj", "body")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/sendMail")
        self.assertEqual(data["message"]["subject"], "subj")
        self.assertEqual(data["message"]["body"],
                         {"contentType": "Text", "content": "body"})
        self.assertEqual(data["message"]["toRecipients"][0]["emailAddress"]["address"],
                         "to@x.com")

    def test_get_email_text_vs_html_format_selects_different_fields(self):
        tools = _register(email_mod, "register_email_tools")
        # Default (text) -> selects bodyPreview
        with patch.object(email_mod, "graph_get", return_value={"id": "m1"}) as m:
            tools["get_email"]("user-1", "msg-9")
        self.assertIn("bodyPreview", m.call_args[0][0])
        # EMAIL_BODY_FORMAT env override forces the html branch (selects `body`)
        with patch.dict(os.environ, {"EMAIL_BODY_FORMAT": "html"}), \
             patch.object(email_mod, "graph_get", return_value={"id": "m1"}) as m:
            tools["get_email"]("user-1", "msg-9")
        endpoint = m.call_args[0][0]
        self.assertNotIn("bodyPreview", endpoint)
        self.assertTrue(endpoint.endswith(",body"))

    def test_list_emails_passes_top_into_endpoint_and_max_items(self):
        tools = _register(email_mod, "register_email_tools")
        with patch.object(email_mod, "graph_get_all", return_value={"value": []}) as m:
            tools["list_emails"]("user-1", top=25)
        # endpoint is positional; max_items is keyword
        self.assertEqual(
            m.call_args[0][0],
            "users/user-1/messages?$top=25&$orderby=receivedDateTime desc",
        )
        self.assertEqual(m.call_args[1]["max_items"], 25)


# ---------------------------------------------------------------------------
# tools/calendar.py — NON-timezone tools (timezone behaviour covered in test_p1)
# ---------------------------------------------------------------------------

class TestCalendarTools(unittest.TestCase):

    def test_read_endpoints_and_delete_event_route_through_graph(self):
        tools = _register(calendar_mod, "register_calendar_tools")
        with patch.object(calendar_mod, "graph_get", return_value={"value": []}) as m_get, \
             patch.object(calendar_mod, "graph_delete",
                          return_value={"status": "deleted successfully"}) as m_del:
            tools["list_events"]("user-1", top=15)
            tools["get_event"]("user-1", "ev-9")
            tools["list_calendars"]("user-1")
            tools["delete_event"]("user-1", "ev-9")
        self.assertEqual(m_get.call_args_list[0][0][0],
                         "users/user-1/events?$top=15&$orderby=start/dateTime")
        self.assertEqual(m_get.call_args_list[1][0][0], "users/user-1/events/ev-9")
        self.assertEqual(m_get.call_args_list[2][0][0], "users/user-1/calendars")
        self.assertEqual(m_del.call_args[0][0], "users/user-1/events/ev-9")

    def test_create_event_with_attendees_constructs_attendees_list(self):
        # Timezone behaviour is covered by tests/test_p1.py — here we verify
        # that the comma-separated `attendees` argument is parsed into a list
        # of {emailAddress, type:"required"} entries.
        tools = _register(calendar_mod, "register_calendar_tools")
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "UTC"}), \
             patch.object(calendar_mod, "graph_post", return_value={"id": "ev-1"}) as m:
            tools["create_event"]("user-1", "Sync", "2026-01-01T10:00:00",
                                  "2026-01-01T11:00:00",
                                  attendees="a@x.com, b@x.com")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/events")
        self.assertEqual(len(data["attendees"]), 2)
        self.assertEqual(data["attendees"][0]["emailAddress"]["address"], "a@x.com")
        self.assertEqual(data["attendees"][0]["type"], "required")
        self.assertEqual(data["attendees"][1]["emailAddress"]["address"], "b@x.com")
        self.assertEqual(data["attendees"][1]["type"], "required")

    def test_update_event_omits_unset_fields(self):
        tools = _register(calendar_mod, "register_calendar_tools")
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "UTC"}), \
             patch.object(calendar_mod, "graph_patch", return_value={"status": "success"}) as m:
            tools["update_event"]("user-1", "ev-9", subject="New",
                                  end="2026-01-01T12:00:00")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/events/ev-9")
        self.assertEqual(data["subject"], "New")
        self.assertEqual(data["end"], {"dateTime": "2026-01-01T12:00:00",
                                       "timeZone": "UTC"})
        self.assertNotIn("start", data)


# ---------------------------------------------------------------------------
# tools/teams.py
# ---------------------------------------------------------------------------

class TestTeamsTools(unittest.TestCase):

    def test_list_teams_uses_groups_filter_for_team_provisioning(self):
        tools = _register(teams_mod, "register_teams_tools")
        with patch.object(teams_mod, "graph_get_all", return_value={"value": []}) as m:
            tools["list_teams"]()
        self.assertEqual(
            m.call_args[0][0],
            "groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
            "&$select=id,displayName,description",
        )

    def test_send_channel_message_data_structure(self):
        tools = _register(teams_mod, "register_teams_tools")
        with patch.object(teams_mod, "graph_post", return_value={"id": "msg"}) as m:
            tools["send_channel_message"]("team-1", "ch-1", "hello")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "teams/team-1/channels/ch-1/messages")
        self.assertEqual(data["body"], {"contentType": "text", "content": "hello"})

    def test_list_channel_messages_passes_top_and_max_items(self):
        tools = _register(teams_mod, "register_teams_tools")
        with patch.object(teams_mod, "graph_get_all", return_value={"value": []}) as m:
            tools["list_channel_messages"]("team-1", "ch-1", top=30)
        self.assertEqual(m.call_args[0][0],
                         "teams/team-1/channels/ch-1/messages?$top=30")
        # max_items is passed as a keyword argument (matches email.list_emails)
        self.assertEqual(m.call_args[1]["max_items"], 30)


# ---------------------------------------------------------------------------
# tools/contacts.py
# ---------------------------------------------------------------------------

class TestContactsTools(unittest.TestCase):

    def test_create_contact_with_email_constructs_email_payload(self):
        tools = _register(contacts_mod, "register_contacts_tools")
        with patch.object(contacts_mod, "graph_post", return_value={"id": "c1"}) as m:
            tools["create_contact"]("user-1", "Jane", "Doe",
                                    email="jane@x.com", mobile="+1000",
                                    job_title="Eng", company="Acme")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/contacts")
        self.assertEqual(data["givenName"], "Jane")
        self.assertEqual(data["surname"], "Doe")
        self.assertEqual(data["emailAddresses"],
                         [{"address": "jane@x.com", "name": "Jane Doe"}])
        self.assertEqual(data["mobilePhone"], "+1000")
        self.assertEqual(data["jobTitle"], "Eng")
        self.assertEqual(data["companyName"], "Acme")

    def test_update_contact_omits_unset_fields(self):
        tools = _register(contacts_mod, "register_contacts_tools")
        with patch.object(contacts_mod, "graph_patch",
                          return_value={"status": "success"}) as m:
            tools["update_contact"]("user-1", "c-9", job_title="Boss")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/contacts/c-9")
        # only jobTitle was supplied → data contains only jobTitle
        self.assertEqual(data, {"jobTitle": "Boss"})

    def test_delete_contact_routes_through_graph_delete(self):
        tools = _register(contacts_mod, "register_contacts_tools")
        with patch.object(contacts_mod, "graph_delete",
                          return_value={"status": "deleted successfully"}) as m:
            tools["delete_contact"]("user-1", "c-9")
        self.assertEqual(m.call_args[0][0], "users/user-1/contacts/c-9")


# ---------------------------------------------------------------------------
# tools/meetings.py
# ---------------------------------------------------------------------------

class TestMeetingsTools(unittest.TestCase):

    def test_create_online_meeting_appends_z_suffix_to_datetimes(self):
        tools = _register(meetings_mod, "register_meetings_tools")
        with patch.object(meetings_mod, "graph_post", return_value={"id": "m1"}) as m:
            tools["create_online_meeting"]("user-1", "Standup",
                                          "2026-06-12T10:00:00",
                                          "2026-06-12T10:30:00")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/onlineMeetings")
        self.assertEqual(data["subject"], "Standup")
        self.assertEqual(data["startDateTime"], "2026-06-12T10:00:00Z")
        self.assertEqual(data["endDateTime"], "2026-06-12T10:30:00Z")

    def test_get_meeting_transcript_expands_sessions_segments(self):
        tools = _register(meetings_mod, "register_meetings_tools")
        with patch.object(meetings_mod, "graph_get", return_value={"id": "tr-1"}) as m:
            tools["get_meeting_transcript"]("rec-9")
        self.assertEqual(
            m.call_args[0][0],
            "communications/callRecords/rec-9?$expand=sessions($expand=segments)",
        )

    def test_list_call_records_endpoint_with_top_and_orderby(self):
        tools = _register(meetings_mod, "register_meetings_tools")
        with patch.object(meetings_mod, "graph_get", return_value={"value": []}) as m:
            tools["list_call_records"]()
        self.assertEqual(
            m.call_args[0][0],
            "communications/callRecords?$top=10&$orderby=startDateTime desc",
        )


# ---------------------------------------------------------------------------
# tools/drafts.py
# ---------------------------------------------------------------------------

class TestDraftsTools(unittest.TestCase):

    def test_create_draft_email_data_structure(self):
        tools = _register(drafts_mod, "register_drafts_tools")
        with patch.object(drafts_mod, "graph_post", return_value={"id": "d1"}) as m:
            tools["create_draft_email"]("user-1", "to@x.com", "subj", "body")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/messages")
        self.assertEqual(data["subject"], "subj")
        self.assertEqual(data["body"], {"contentType": "Text", "content": "body"})
        self.assertEqual(data["toRecipients"][0]["emailAddress"]["address"], "to@x.com")

    def test_send_draft_and_move_email_endpoints_and_payloads(self):
        tools = _register(drafts_mod, "register_drafts_tools")
        with patch.object(drafts_mod, "graph_post", return_value={"status": "ok"}) as m:
            tools["send_draft_email"]("user-1", "msg-9")
            tools["move_email"]("user-1", "msg-9", "folder-7")
        send_endpoint, send_data = m.call_args_list[0][0][0], m.call_args_list[0][0][1]
        move_endpoint, move_data = m.call_args_list[1][0][0], m.call_args_list[1][0][1]
        self.assertEqual(send_endpoint, "users/user-1/messages/msg-9/send")
        self.assertEqual(send_data, {})
        self.assertEqual(move_endpoint, "users/user-1/messages/msg-9/move")
        self.assertEqual(move_data, {"destinationId": "folder-7"})

    def test_update_draft_email_partial_fields(self):
        tools = _register(drafts_mod, "register_drafts_tools")
        with patch.object(drafts_mod, "graph_patch",
                          return_value={"status": "success"}) as m:
            tools["update_draft_email"]("user-1", "msg-9", body="new body")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/messages/msg-9")
        self.assertEqual(data,
                         {"body": {"contentType": "Text", "content": "new body"}})


# ---------------------------------------------------------------------------
# tools/shared_mailbox.py
# ---------------------------------------------------------------------------

class TestSharedMailboxTools(unittest.TestCase):

    def test_send_from_shared_mailbox_includes_saveToSentItems_true(self):
        tools = _register(shared_mailbox_mod, "register_shared_mailbox_tools")
        with patch.object(shared_mailbox_mod, "graph_post",
                          return_value={"status": "ok"}) as m:
            tools["send_from_shared_mailbox"]("info@acme.com", "to@x.com",
                                              "subj", "body")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/info@acme.com/sendMail")
        # saveToSentItems must be present and True (Graph expects a boolean)
        self.assertEqual(data["saveToSentItems"], True)
        self.assertEqual(data["message"]["subject"], "subj")
        self.assertEqual(data["message"]["toRecipients"][0]["emailAddress"]["address"],
                         "to@x.com")

    def test_list_shared_mailbox_messages_uses_mailbox_as_user_with_top(self):
        tools = _register(shared_mailbox_mod, "register_shared_mailbox_tools")
        with patch.object(shared_mailbox_mod, "graph_get",
                          return_value={"value": []}) as m:
            tools["list_shared_mailbox_messages"]("info@acme.com", top=5)
        self.assertEqual(
            m.call_args[0][0],
            "users/info@acme.com/messages?$top=5&$orderby=receivedDateTime desc",
        )

    def test_reply_shared_mailbox_endpoint_and_payload(self):
        tools = _register(shared_mailbox_mod, "register_shared_mailbox_tools")
        with patch.object(shared_mailbox_mod, "graph_post",
                          return_value={"status": "ok"}) as m:
            tools["reply_shared_mailbox"]("info@acme.com", "msg-9", "thanks")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/info@acme.com/messages/msg-9/reply")
        self.assertEqual(data["message"]["body"]["content"], "thanks")


# ---------------------------------------------------------------------------
# tools/presence.py
# ---------------------------------------------------------------------------

class TestPresenceTools(unittest.TestCase):

    def test_get_user_presence_endpoint(self):
        tools = _register(presence_mod, "register_presence_tools")
        with patch.object(presence_mod, "graph_get",
                          return_value={"availability": "Available"}) as m:
            tools["get_user_presence"]("user-1")
        self.assertEqual(m.call_args[0][0], "users/user-1/presence")

    def test_get_multiple_presence_splits_and_strips_comma_separated_ids(self):
        tools = _register(presence_mod, "register_presence_tools")
        with patch.object(presence_mod, "graph_post",
                          return_value={"value": []}) as m:
            tools["get_multiple_presence"]("a, b ,c")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "communications/getPresencesByUserId")
        self.assertEqual(data, {"ids": ["a", "b", "c"]})

    def test_list_available_users_filters_available_only(self):
        tools = _register(presence_mod, "register_presence_tools")
        graph_result = {"value": [
            {"id": "a", "availability": "Available"},
            {"id": "b", "availability": "Busy"},
            {"id": "c", "availability": "Available"},
        ]}
        with patch.object(presence_mod, "graph_post",
                          return_value=graph_result) as m:
            result = tools["list_available_users"]("a,b,c")
        # underlying call still splits+strips ids into a list
        self.assertEqual(m.call_args[0][1], {"ids": ["a", "b", "c"]})
        self.assertEqual(result["total_checked"], 3)
        self.assertEqual(result["total_available"], 2)
        self.assertEqual([p["id"] for p in result["available_users"]], ["a", "c"])


# ---------------------------------------------------------------------------
# tools/onedrive.py
# ---------------------------------------------------------------------------

class TestOnedriveTools(unittest.TestCase):

    def test_list_drive_items_default_folder_is_root(self):
        tools = _register(onedrive_mod, "register_onedrive_tools")
        with patch.object(onedrive_mod, "graph_get_all",
                          return_value={"value": []}) as m:
            tools["list_drive_items"]("user-1")
        self.assertEqual(m.call_args[0][0], "users/user-1/drive/root/children")

    def test_create_folder_data_structure_and_conflict_behavior(self):
        tools = _register(onedrive_mod, "register_onedrive_tools")
        with patch.object(onedrive_mod, "graph_post", return_value={"id": "f1"}) as m:
            tools["create_folder"]("user-1", "Reports", parent_id="item-7")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/drive/items/item-7/children")
        self.assertEqual(data["name"], "Reports")
        self.assertEqual(data["folder"], {})
        self.assertEqual(data["@microsoft.graph.conflictBehavior"], "rename")

    def test_search_drive_quoted_query(self):
        tools = _register(onedrive_mod, "register_onedrive_tools")
        with patch.object(onedrive_mod, "graph_get_all",
                          return_value={"value": []}) as m:
            tools["search_drive"]("user-1", "report")
        self.assertEqual(m.call_args[0][0],
                         "users/user-1/drive/root/search(q='report')")


# ---------------------------------------------------------------------------
# tools/sharepoint.py
# ---------------------------------------------------------------------------

class TestSharepointTools(unittest.TestCase):

    def test_list_sharepoint_sites_uses_search_star(self):
        tools = _register(sharepoint_mod, "register_sharepoint_tools")
        with patch.object(sharepoint_mod, "graph_get_all",
                          return_value={"value": []}) as m:
            tools["list_sharepoint_sites"]()
        self.assertEqual(m.call_args[0][0], "sites?search=*")

    def test_list_site_list_items_expands_fields(self):
        tools = _register(sharepoint_mod, "register_sharepoint_tools")
        with patch.object(sharepoint_mod, "graph_get_all",
                          return_value={"value": []}) as m:
            tools["list_site_list_items"]("site-1", "list-9")
        self.assertEqual(m.call_args[0][0],
                         "sites/site-1/lists/list-9/items?$expand=fields")

    def test_create_list_item_wraps_fields_dict(self):
        tools = _register(sharepoint_mod, "register_sharepoint_tools")
        with patch.object(sharepoint_mod, "graph_post",
                          return_value={"id": "i1"}) as m:
            tools["create_list_item"]("site-1", "list-9",
                                      {"Title": "Hello", "Color": "Blue"})
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "sites/site-1/lists/list-9/items")
        self.assertEqual(data, {"fields": {"Title": "Hello", "Color": "Blue"}})


# ---------------------------------------------------------------------------
# tools/todo.py — NON-timezone tools (timezone behaviour covered in test_p1)
# ---------------------------------------------------------------------------

class TestTodoTools(unittest.TestCase):

    def test_list_get_list_tasks_endpoints(self):
        tools = _register(todo_mod, "register_todo_tools")
        with patch.object(todo_mod, "graph_get", return_value={"value": []}) as m:
            tools["list_todo_lists"]("user-1")
            tools["list_todo_tasks"]("user-1", "list-9")
        self.assertEqual(m.call_args_list[0][0][0], "users/user-1/todo/lists")
        self.assertEqual(m.call_args_list[1][0][0],
                         "users/user-1/todo/lists/list-9/tasks")
        with patch.object(todo_mod, "graph_get", return_value={"id": "l1"}) as m:
            tools["get_todo_list"]("user-1", "list-9")
        self.assertEqual(m.call_args[0][0], "users/user-1/todo/lists/list-9")

    def test_create_todo_list_data_payload(self):
        tools = _register(todo_mod, "register_todo_tools")
        with patch.object(todo_mod, "graph_post", return_value={"id": "l1"}) as m:
            tools["create_todo_list"]("user-1", "My Day")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "users/user-1/todo/lists")
        self.assertEqual(data, {"displayName": "My Day"})

    def test_update_and_delete_todo_task_route_through_graph(self):
        tools = _register(todo_mod, "register_todo_tools")
        with patch.object(todo_mod, "graph_patch",
                          return_value={"status": "success"}) as m_patch, \
             patch.object(todo_mod, "graph_delete",
                          return_value={"status": "deleted successfully"}) as m_del:
            tools["update_todo_task"]("user-1", "list-9", "task-9", status="completed")
            tools["delete_todo_task"]("user-1", "list-9", "task-9")
        ep, data = m_patch.call_args[0][0], m_patch.call_args[0][1]
        self.assertEqual(ep, "users/user-1/todo/lists/list-9/tasks/task-9")
        self.assertEqual(data, {"status": "completed"})
        self.assertEqual(m_del.call_args[0][0],
                         "users/user-1/todo/lists/list-9/tasks/task-9")


# ---------------------------------------------------------------------------
# tools/excel.py
# ---------------------------------------------------------------------------

class TestExcelTools(unittest.TestCase):

    def test_add_excel_row_wraps_values_in_outer_list(self):
        tools = _register(excel_mod, "register_excel_tools")
        with patch.object(excel_mod, "graph_post", return_value={"id": "r1"}) as m:
            tools["add_excel_row"]("user-1", "file-1", "Table1",
                                   ["John", 30, "Nairobi"])
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint,
                         "users/user-1/drive/items/file-1/workbook/tables/Table1/rows/add")
        # production wraps the single-row list inside another list
        self.assertEqual(data, {"values": [["John", 30, "Nairobi"]]})

    def test_create_excel_chart_payload(self):
        tools = _register(excel_mod, "register_excel_tools")
        with patch.object(excel_mod, "graph_post", return_value={"id": "c1"}) as m:
            tools["create_excel_chart"]("user-1", "file-1", "Sheet1",
                                        "ColumnClustered", "A1:B5")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint,
                         "users/user-1/drive/items/file-1/workbook/worksheets/Sheet1/charts/add")
        self.assertEqual(data["type"], "ColumnClustered")
        self.assertEqual(data["sourceData"], "A1:B5")
        self.assertEqual(data["seriesBy"], "Auto")

    def test_update_excel_range_data_values_and_endpoint(self):
        tools = _register(excel_mod, "register_excel_tools")
        with patch.object(excel_mod, "graph_patch",
                          return_value={"status": "success"}) as m:
            tools["update_excel_range"]("user-1", "file-1", "Sheet1", "A1:B2",
                                        [["x", "y"], [1, 2]])
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(
            endpoint,
            "users/user-1/drive/items/file-1/workbook/worksheets/Sheet1/range(address='A1:B2')",
        )
        self.assertEqual(data, {"values": [["x", "y"], [1, 2]]})


# ---------------------------------------------------------------------------
# tools/search.py
# ---------------------------------------------------------------------------

class TestSearchTools(unittest.TestCase):

    def test_search_all_content_default_content_types_split_and_request_shape(self):
        tools = _register(search_mod, "register_search_tools")
        with patch.object(search_mod, "graph_post", return_value={"value": []}) as m:
            tools["search_all_content"]("budget")
        endpoint, data = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(endpoint, "search/query")
        req = data["requests"][0]
        self.assertEqual(req["entityTypes"],
                         ["message", "driveItem", "listItem", "site"])
        self.assertEqual(req["query"], {"queryString": "budget"})
        self.assertEqual(req["from"], 0)
        self.assertEqual(req["size"], 10)

    def test_search_all_content_custom_content_types_are_split(self):
        tools = _register(search_mod, "register_search_tools")
        with patch.object(search_mod, "graph_post", return_value={"value": []}) as m:
            tools["search_all_content"]("hr", content_types="message,event")
        data = m.call_args[0][1]
        self.assertEqual(data["requests"][0]["entityTypes"], ["message", "event"])

    def test_search_files_uses_driveItem_only(self):
        tools = _register(search_mod, "register_search_tools")
        with patch.object(search_mod, "graph_post", return_value={"value": []}) as m:
            tools["search_files"]("report")
        data = m.call_args[0][1]
        self.assertEqual(data["requests"][0]["entityTypes"], ["driveItem"])


# ---------------------------------------------------------------------------
# tools/users.py
# ---------------------------------------------------------------------------

class TestUsersTools(unittest.TestCase):

    def test_list_users_endpoint_with_select(self):
        tools = _register(users_mod, "register_user_tools")
        with patch.object(users_mod, "graph_get_all", return_value={"value": []}) as m:
            tools["list_users"]()
        self.assertEqual(
            m.call_args[0][0],
            "users?$select=id,displayName,mail,jobTitle,department",
        )

    def test_get_user_selects_extended_fields_including_mobilePhone(self):
        tools = _register(users_mod, "register_user_tools")
        with patch.object(users_mod, "graph_get", return_value={"id": "u1"}) as m:
            tools["get_user"]("user-1")
        self.assertEqual(
            m.call_args[0][0],
            "users/user-1?$select=id,displayName,mail,jobTitle,department,mobilePhone",
        )

    def test_get_user_manager_and_direct_reports_endpoints(self):
        tools = _register(users_mod, "register_user_tools")
        # Both tools call graph_get; use a single mock with side_effect to
        # avoid two patches colliding on the same module attribute.
        with patch.object(users_mod, "graph_get",
                          side_effect=[{"id": "m1"}, {"value": []}]) as m:
            tools["get_user_manager"]("user-1")
            tools["list_user_direct_reports"]("user-1")
        self.assertEqual(m.call_args_list[0][0][0], "users/user-1/manager")
        self.assertEqual(m.call_args_list[1][0][0], "users/user-1/directReports")


# ---------------------------------------------------------------------------
# tools/audit.py — read_logs is mocked on the audit module; the real
# audit.log file is never opened.
# ---------------------------------------------------------------------------

class TestAuditTools(unittest.TestCase):

    def test_get_audit_logs_delegates_to_logger_read_logs(self):
        sample = [{"timestamp": "2026-01-01T00:00:00Z", "tool": "send_email",
                   "parameters": {}}]
        tools = _register(audit_mod, "register_audit_tools")
        with patch.object(audit_mod, "read_logs", return_value=sample) as m:
            result = tools["get_audit_logs"](last_n=25)
        m.assert_called_once_with(25)
        self.assertEqual(result, sample)

    def test_get_recent_actions_returns_total_shown_and_actions(self):
        sample = [
            {"timestamp": "2026-01-01T00:00:00Z", "tool": "send_email",
             "parameters": {}},
            {"timestamp": "2026-01-01T00:01:00Z", "tool": "list_users",
             "parameters": {}},
        ]
        tools = _register(audit_mod, "register_audit_tools")
        with patch.object(audit_mod, "read_logs", return_value=sample) as m:
            result = tools["get_recent_actions"](last_n=10)
        m.assert_called_once_with(10)
        self.assertEqual(result["total_shown"], 2)
        self.assertEqual(result["actions"], sample)

    def test_audit_tools_do_not_open_real_log_file(self):
        """Guard: audit tools must only call logger.read_logs — never open()
        the real audit.log file directly."""
        tools = _register(audit_mod, "register_audit_tools")
        with patch.object(audit_mod, "read_logs", return_value=[]) as m_read, \
             patch("builtins.open") as mock_open:
            tools["get_audit_logs"]()
            tools["get_recent_actions"]()
        m_read.assert_called()
        mock_open.assert_not_called()


if __name__ == "__main__":
    unittest.main()
