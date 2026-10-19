"""P1 regression tests for the ms365-ai-assistant-mcp security remediation.

Uses only the standard library (unittest + unittest.mock). All HTTP, sleep, and
notification side effects are mocked. No live Microsoft 365 credentials, network,
or email are required.

Note on patching strategy: tests patch the *methods* on the real ``requests``
module (``patch("requests.get")`` etc.) rather than replacing the whole module,
so that the production ``except requests.exceptions.Timeout`` / ``RequestException``
clauses still resolve against the real exception classes.

Run with:
    python -m unittest tests.test_p1 -v
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import requests as _real_requests  # real module; used only for exception classes

# Make the repo root importable so `import auth`, `import graph_client`, etc. work.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

# Production modules read some configuration from the environment at import time
# (auth.CLIENT_ID/TENANT_ID/CLIENT_SECRET; logger.VERBOSE/SILENT/REDACT_PII). Set
# deterministic non-secret test values BEFORE importing them.
os.environ.setdefault("CLIENT_ID", "test-client-id")
os.environ.setdefault("TENANT_ID", "test-tenant-id")
os.environ.setdefault("CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("MCP_API_KEY", "test-api-key")
os.environ.setdefault("REDACT_PII", "true")
os.environ.setdefault("VERBOSE_LOGGING", "false")
os.environ.setdefault("SILENT", "true")  # keep the test output clean

import auth  # noqa: E402
import graph_client  # noqa: E402
import logger  # noqa: E402
import notifier  # noqa: E402
import tools.health as health_mod  # noqa: E402
import tools.planner as planner_mod  # noqa: E402
import tools.onenote as onenote_mod  # noqa: E402
import tools.calendar as calendar_mod  # noqa: E402
import tools.todo as todo_mod  # noqa: E402
import tools.email as email_mod  # noqa: E402
import tools.teams as teams_mod  # noqa: E402
import tools.contacts as contacts_mod  # noqa: E402
import tools.meetings as meetings_mod  # noqa: E402
import tools.drafts as drafts_mod  # noqa: E402
import tools.shared_mailbox as shared_mailbox_mod  # noqa: E402
import tools.presence as presence_mod  # noqa: E402
import tools.onedrive as onedrive_mod  # noqa: E402
import tools.sharepoint as sharepoint_mod  # noqa: E402
import tools.users as users_mod  # noqa: E402
import tools.audit as audit_mod  # noqa: E402
import tools.excel as excel_mod  # noqa: E402
import tools.search as search_mod  # noqa: E402


class FakeMCP:
    """Minimal stand-in for FastMCP that captures @mcp.tool()-decorated functions."""

    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _ok_response(status=200, json_data=None, headers=None):
    """Build a Mock that behaves like a successful requests.Response."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{"x":1}' if json_data is not None else b""
    resp.headers = headers or {}
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


def _err_response(status, headers=None):
    """Build a Mock that behaves like an error request.Response (body never exposed)."""
    resp = MagicMock()
    resp.status_code = status
    resp.content = b'{"error":"internal"}'
    resp.headers = headers or {}
    resp.text = "INTERNAL ERROR BODY - MUST NOT LEAK"
    resp.json.return_value = {"error": "internal"}
    return resp


class _GraphClientTestBase(unittest.TestCase):
    """Common fixtures for graph_client tests: token cache + mocked time/log/alerts.

    Per-test HTTP behaviour is set up in each test by patching the specific
    requests method (requests.get / requests.post / ...) inside a `with` block.
    """

    def setUp(self):
        auth._token_cache = "fake-token"
        auth._token_expiry = sys.maxsize
        self._patches = [
            patch.object(graph_client, "get_token", return_value="fake-token"),
            patch.object(graph_client, "time"),
            patch.object(graph_client, "log_action"),
            patch("notifier.alert_api_error"),
        ]
        self.mocks = [p.start() for p in self._patches]
        for p in self._patches:
            self.addCleanup(p.stop)
        self.mock_time = self.mocks[1]


class TestAuthToken(unittest.TestCase):
    """1. auth.get_token: success, non-success, timeout, network error, malformed JSON."""

    def setUp(self):
        auth._token_cache = None
        auth._token_expiry = 0

    def test_get_token_success(self):
        with patch("requests.post") as mock_post, \
             patch("notifier.alert_auth_failure") as mock_alert:
            mock_post.return_value = _ok_response(
                200, json_data={"access_token": "tok-123", "expires_in": 3600}
            )
            token = auth.get_token()
        self.assertEqual(token, "tok-123")
        mock_post.assert_called_once()
        mock_alert.assert_not_called()

    def test_get_token_non_success_status_sanitized(self):
        with patch("requests.post") as mock_post, \
             patch("notifier.alert_auth_failure") as mock_alert:
            mock_post.return_value = _err_response(401)
            with self.assertRaises(Exception) as ctx:
                auth.get_token()
        msg = str(ctx.exception)
        self.assertIn("401", msg)
        self.assertNotIn("INTERNAL ERROR BODY", msg)
        mock_alert.assert_called_once()
        self.assertIn("401", mock_alert.call_args[0][0])

    def test_get_token_timeout(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = _real_requests.exceptions.Timeout()
            with self.assertRaises(Exception) as ctx:
                auth.get_token()
        self.assertIn("timed out", str(ctx.exception).lower())

    def test_get_token_network_error(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = _real_requests.exceptions.RequestException()
            with self.assertRaises(Exception) as ctx:
                auth.get_token()
        self.assertIn("unavailable", str(ctx.exception).lower())

    def test_get_token_malformed_json(self):
        resp = _ok_response(200, json_data=None)
        resp.json.side_effect = ValueError("not json")
        with patch("requests.post") as mock_post:
            mock_post.return_value = resp
            with self.assertRaises(Exception) as ctx:
                auth.get_token()
        self.assertIn("invalid response", str(ctx.exception).lower())


class TestGraphClient(_GraphClientTestBase):
    """2-3. graph_client: success, timeout, 429 bounded retry, malformed/negative
    Retry-After, max retries, transient 5xx (idempotent GET only; POST/PATCH/DELETE
    are not retried on 5xx)."""

    def test_graph_get_success(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = _ok_response(200, json_data={"value": [1, 2]})
            result = graph_client.graph_get("me")
        self.assertEqual(result, {"value": [1, 2]})

    def test_graph_get_timeout(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = _real_requests.exceptions.Timeout()
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_get("me")
        self.assertIn("timed out", str(ctx.exception).lower())

    def test_graph_get_429_oversized_retry_after_capped(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _err_response(429, headers={"Retry-After": "999999"}),
                _ok_response(200, json_data={"ok": True}),
            ]
            result = graph_client.graph_get("me")
        self.assertEqual(result, {"ok": True})
        # The 999999s Retry-After must be capped to MAX_RETRY_AFTER (60).
        self.mock_time.sleep.assert_called_once_with(graph_client.MAX_RETRY_AFTER)

    def test_graph_get_429_malformed_retry_after_uses_default(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _err_response(429, headers={"Retry-After": "not-a-number"}),
                _ok_response(200, json_data={"ok": True}),
            ]
            graph_client.graph_get("me")
        self.mock_time.sleep.assert_called_once_with(graph_client.DEFAULT_RETRY_AFTER)

    def test_graph_get_429_negative_retry_after_zero(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _err_response(429, headers={"Retry-After": "-5"}),
                _ok_response(200, json_data={"ok": True}),
            ]
            graph_client.graph_get("me")
        self.mock_time.sleep.assert_called_once_with(0)

    def test_graph_get_429_max_retries_exceeded(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = _err_response(429)
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_get("me")
        self.assertIn("Max retries exceeded", str(ctx.exception))
        self.assertEqual(mock_get.call_count, graph_client.MAX_RETRIES)

    def test_graph_get_5xx_retry_then_success(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _err_response(503),
                _err_response(502),
                _ok_response(200, json_data={"ok": True}),
            ]
            result = graph_client.graph_get("me")
        self.assertEqual(result, {"ok": True})
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(self.mock_time.sleep.call_count, 2)

    def test_graph_post_5xx_not_retried(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _err_response(500)
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_post("me/messages", {"x": 1})
        self.assertIn("500", str(ctx.exception))
        self.assertNotIn("INTERNAL ERROR BODY", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)
        self.mock_time.sleep.assert_not_called()

    def test_graph_patch_5xx_not_retried(self):
        with patch("requests.patch") as mock_patch:
            mock_patch.return_value = _err_response(503)
            with self.assertRaises(Exception):
                graph_client.graph_patch("me/events/1", {"x": 1}, etag="W/\"1\"")
        self.assertEqual(mock_patch.call_count, 1)

    def test_graph_delete_5xx_not_retried(self):
        with patch("requests.delete") as mock_delete:
            mock_delete.return_value = _err_response(500)
            with self.assertRaises(Exception):
                graph_client.graph_delete("me/events/1", etag="W/\"1\"")
        self.assertEqual(mock_delete.call_count, 1)


class TestGraphGetEtag(_GraphClientTestBase):
    """4. graph_get_etag + Planner If-Match concurrency protection."""

    def test_graph_get_etag_returns_etag(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = _ok_response(
                200, json_data=None, headers={"ETag": "W/\"etag-xyz\""}
            )
            etag = graph_client.graph_get_etag("planner/tasks/task-1")
        self.assertEqual(etag, "W/\"etag-xyz\"")

    def test_graph_get_etag_5xx_retries(self):
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _err_response(503),
                _ok_response(200, json_data=None, headers={"ETag": "W/\"v2\""}),
            ]
            etag = graph_client.graph_get_etag("planner/tasks/task-1")
        self.assertEqual(etag, "W/\"v2\"")
        self.assertEqual(mock_get.call_count, 2)

    def test_graph_get_etag_404_not_retried(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value = _err_response(404)
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_get_etag("planner/tasks/missing")
        self.assertIn("404", str(ctx.exception))
        self.assertEqual(mock_get.call_count, 1)

    def test_planner_update_task_preserves_if_match(self):
        """update_task must fetch the ETag via graph_get_etag and pass it to
        graph_patch so the If-Match concurrency header is preserved."""
        fake = FakeMCP()
        planner_mod.register_planner_tools(fake)
        update_task = fake.tools["update_task"]

        with patch.object(planner_mod, "graph_get_etag", return_value="W/\"etag-1\"") as m_etag, \
             patch.object(planner_mod, "graph_patch", return_value={"status": "success"}) as m_patch:
            result = update_task("task-1", title="new title", percent_complete=50)

        self.assertEqual(result, {"status": "success"})
        m_etag.assert_called_once_with("planner/tasks/task-1")
        self.assertEqual(m_patch.call_args[0][0], "planner/tasks/task-1")
        self.assertEqual(m_patch.call_args[0][1], {"title": "new title", "percentComplete": 50})
        self.assertEqual(m_patch.call_args[0][2], "W/\"etag-1\"")


class TestGraphPostRawOnenote(_GraphClientTestBase):
    """5. graph_post_raw + OneNote: XHTML content-type, UTF-8 payload, endpoint,
    successful response parsing. POST is non-idempotent => no 5xx retry."""

    def test_graph_post_raw_xhtml_content_type_and_body(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _ok_response(201, json_data={"id": "page-1"})
            result = graph_client.graph_post_raw(
                "users/U/onenote/sections/S/pages",
                body=b"<html><body>x</body></html>",
                content_type="application/xhtml+xml",
            )
        self.assertEqual(result, {"id": "page-1"})
        _args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"], b"<html><body>x</body></html>")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/xhtml+xml")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer fake-token")
        self.assertEqual(kwargs["timeout"], graph_client.REQUEST_TIMEOUT)
        self.assertNotIn("json", kwargs)

    def test_graph_post_raw_5xx_not_retried(self):
        with patch("requests.post") as mock_post:
            mock_post.return_value = _err_response(500)
            with self.assertRaises(Exception):
                graph_client.graph_post_raw("ep", body=b"x", content_type="application/xhtml+xml")
        self.assertEqual(mock_post.call_count, 1)
        self.mock_time.sleep.assert_not_called()

    def test_graph_post_raw_429_retries(self):
        with patch("requests.post") as mock_post:
            mock_post.side_effect = [
                _err_response(429, headers={"Retry-After": "1"}),
                _ok_response(201, json_data={"id": "p"}),
            ]
            result = graph_client.graph_post_raw("ep", body=b"x", content_type="application/xhtml+xml")
        self.assertEqual(result, {"id": "p"})
        self.assertEqual(mock_post.call_count, 2)
        self.mock_time.sleep.assert_called_once_with(1)

    def test_onenote_create_page_routes_through_graph_post_raw(self):
        """OneNote create_page must use graph_post_raw with the XHTML content type
        and a UTF-8-encoded body, preserving the OneNote endpoint contract."""
        fake = FakeMCP()
        onenote_mod.register_onenote_tools(fake)
        create_page = fake.tools["create_page"]

        with patch.object(onenote_mod, "graph_post_raw", return_value={"id": "p1"}) as m:
            result = create_page("user-1", "sec-1", "My Title", "Hello body")

        self.assertEqual(result, {"id": "p1"})
        _args, kwargs = m.call_args
        self.assertEqual(_args[0], "users/user-1/onenote/sections/sec-1/pages")
        self.assertEqual(kwargs["content_type"], "application/xhtml+xml")
        body = kwargs["body"]
        self.assertIsInstance(body, (bytes, bytearray))
        decoded = body.decode("utf-8")
        self.assertIn("<title>My Title</title>", decoded)
        self.assertIn("<p>Hello body</p>", decoded)


class TestLoggerRedact(unittest.TestCase):
    """6. logger.redact: secret, identifier, query-token patterns redacted;
    ordinary text preserved; redaction is unconditional (no REDACT_PII=false bypass)."""

    def test_redact_email(self):
        self.assertEqual(
            logger.redact("contact admin@pharo.org now"),
            "contact [EMAIL] now",
        )

    def test_redact_jwt_token(self):
        out = logger.redact("Bearer eyJhbGciOiJIUzI1NiJ9.abc.def payload")
        self.assertIn("[TOKEN]", out)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", out)

    def test_redact_uuid(self):
        out = logger.redact("tenant 12345678-1234-1234-1234-123456789abc here")
        self.assertIn("[UUID]", out)
        self.assertNotIn("12345678-1234-1234-1234-123456789abc", out)

    def test_redact_secret_assignment(self):
        out = logger.redact("client_secret=hunter2-secret-value")
        self.assertIn("client_secret=[REDACTED]", out)
        self.assertNotIn("hunter2-secret-value", out)

    def test_redact_tenant_client_id(self):
        out = logger.redact("tenant_id=abc-123 client_id=def-456")
        self.assertIn("tenant_id=[REDACTED]", out)
        self.assertIn("client_id=[REDACTED]", out)
        self.assertNotIn("abc-123", out)
        self.assertNotIn("def-456", out)

    def test_redact_query_token(self):
        out = logger.redact("https://graph.microsoft.com/v1.0/me?access_token=tok123&x=1")
        self.assertIn("access_token=[REDACTED]", out)
        self.assertNotIn("tok123", out)

    def test_redact_response_body_line(self):
        out = logger.redact("response body: sensitive internal diagnostics here")
        self.assertIn("response body=[REDACTED]", out)
        self.assertNotIn("sensitive internal diagnostics", out)

    def test_redact_preserves_ordinary_text(self):
        self.assertEqual(
            logger.redact("Scheduled meeting for tomorrow at 10am"),
            "Scheduled meeting for tomorrow at 10am",
        )

    def test_redact_is_unconditional(self):
        """Redaction applies even when REDACT_PII is set to false — the
        pre-1d0e7c8 `if not REDACT_PII: return text` short-circuit was removed."""
        with patch.dict(os.environ, {"REDACT_PII": "false"}):
            out = logger.redact("client_secret=secret-value")
            self.assertIn("client_secret=[REDACTED]", out)
            self.assertNotIn("secret-value", out)


class TestHealthCheck(unittest.TestCase):
    """7. tools/health.py: raw exception messages and tenant/client identifiers
    are not exposed in the result."""

    def setUp(self):
        auth._token_cache = "fake-token"
        auth._token_expiry = sys.maxsize
        notifier._last_notification_time.clear()

    def _register(self):
        fake = FakeMCP()
        health_mod.register_health_tools(fake)
        return fake.tools["health_check"]

    def test_results_contain_no_tenant_or_client_id(self):
        health_check = self._register()
        with patch.object(health_mod, "get_token", return_value="fake-token"), \
             patch("requests.get") as mock_get, \
             patch.object(health_mod, "log_action"):
            mock_get.return_value = _ok_response(200, json_data={"$metadata": True})
            result = health_check()
        self.assertNotIn("tenant_id", result)
        self.assertNotIn("client_id", result)
        self.assertEqual(result["authentication"], "success")
        self.assertEqual(result["graph_api"], "reachable")

    def test_auth_failure_is_sanitized(self):
        health_check = self._register()
        with patch.object(health_mod, "get_token", side_effect=Exception(
            "Authentication failed with HTTP status 401. Token=supersecret"
        )), patch.object(health_mod, "log_action"):
            result = health_check()
        self.assertEqual(result["authentication"], "failed")
        for value in result.values():
            self.assertNotIn("supersecret", str(value))
            self.assertNotIn("401", str(value))

    def test_graph_unreachable_is_sanitized(self):
        health_check = self._register()
        with patch.object(health_mod, "get_token", return_value="fake-token"), \
             patch("requests.get") as mock_get, \
             patch.object(health_mod, "log_action"):
            mock_get.side_effect = _real_requests.exceptions.Timeout(
                "connection to graph.microsoft.com timed out — internal host detail"
            )
            result = health_check()
        self.assertEqual(result["graph_api"], "unreachable: request timed out")
        for value in result.values():
            self.assertNotIn("internal host detail", str(value))

    def test_graph_status_code_returned_without_body(self):
        health_check = self._register()
        with patch.object(health_mod, "get_token", return_value="fake-token"), \
             patch("requests.get") as mock_get, \
             patch.object(health_mod, "log_action"):
            mock_get.return_value = _err_response(503)
            result = health_check()
        self.assertEqual(result["graph_api"], "error: 503")
        for value in result.values():
            self.assertNotIn("INTERNAL ERROR BODY", str(value))


class TestNotifierSendAlert(unittest.TestCase):
    """8. notifier.send_alert: sanitized content + safe handling of unconfigured
    notification settings (no real email sent)."""

    def setUp(self):
        notifier._last_notification_time.clear()

    def test_unconfigured_returns_false_without_email(self):
        with patch.object(notifier, "ALERT_EMAIL", None), \
             patch.object(notifier, "ALERT_EMAIL_PASSWORD", None), \
             patch.object(notifier, "ALERT_RECIPIENT", None), \
             patch.object(notifier, "smtplib") as mock_smtp:
            result = notifier.send_alert("subj", "msg", alert_type="unconfigured")
        self.assertFalse(result)
        mock_smtp.SMTP_SSL.assert_not_called()

    def test_configured_redacts_subject_and_message(self):
        with patch.object(notifier, "ALERT_EMAIL", "sender@example.com"), \
             patch.object(notifier, "ALERT_EMAIL_PASSWORD", "pw"), \
             patch.object(notifier, "ALERT_RECIPIENT", "recipient@example.com"), \
             patch.object(notifier, "smtplib") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.SMTP_SSL.return_value.__enter__.return_value = mock_server
            result = notifier.send_alert(
                "subj with admin@pharo.org email",
                "msg with client_secret=hunter2 value",
                alert_type="redacted-test",
            )
        self.assertTrue(result)
        sent_string = mock_server.sendmail.call_args[0][2]
        self.assertIn("[EMAIL]", sent_string)
        self.assertIn("client_secret=[REDACTED]", sent_string)
        self.assertNotIn("admin@pharo.org", sent_string)
        self.assertNotIn("hunter2", sent_string)

    def test_failure_does_not_leak_exception(self):
        with patch.object(notifier, "ALERT_EMAIL", "sender@example.com"), \
             patch.object(notifier, "ALERT_EMAIL_PASSWORD", "pw"), \
             patch.object(notifier, "ALERT_RECIPIENT", "recipient@example.com"), \
             patch.object(notifier, "smtplib") as mock_smtp:
            mock_smtp.SMTP_SSL.side_effect = RuntimeError(
                "SMTPAUTHfail internal host=mail.internal.local creds=admin:pass"
            )
            result = notifier.send_alert("subj", "msg", alert_type="fail-test")
        self.assertFalse(result)


class TestStartupKeyVerification(unittest.TestCase):
    """9. Startup-key verification: verify_server_key behavior without M365, plus
    static consistency across all four entry points."""

    def test_verify_server_key_missing_raises(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MCP_API_KEY", None)
            with self.assertRaises(Exception) as ctx:
                auth.verify_server_key()
        self.assertIn("MCP_API_KEY", str(ctx.exception))

    def test_verify_server_key_present_returns_true(self):
        with patch.dict(os.environ, {"MCP_API_KEY": "a-real-key"}):
            self.assertTrue(auth.verify_server_key())

    def test_all_entry_points_call_verify_server_key(self):
        """Static consistency check: planner_server.py and the three modular
        servers under servers/ must each call verify_server_key() at import time
        (the modular servers can't be imported here without the mcp package, so
        we verify from source instead of executing them)."""
        entry_points = [
            os.path.join(REPO_ROOT, "planner_server.py"),
            os.path.join(REPO_ROOT, "servers", "core_server.py"),
            os.path.join(REPO_ROOT, "servers", "communication_server.py"),
            os.path.join(REPO_ROOT, "servers", "files_server.py"),
        ]
        for path in entry_points:
            with open(path, "r") as f:
                source = f.read()
            self.assertIn(
                "from auth import verify_server_key\nverify_server_key()",
                source,
                msg=f"{path} does not enforce verify_server_key() at startup",
            )



class TestTimezoneConfig(unittest.TestCase):
    """Phase A1: DEFAULT_TIMEZONE env configuration for calendar + To Do."""

    def setUp(self):
        self._orig_tz = os.environ.get("DEFAULT_TIMEZONE")
        os.environ.pop("DEFAULT_TIMEZONE", None)

    def tearDown(self):
        if self._orig_tz is not None:
            os.environ["DEFAULT_TIMEZONE"] = self._orig_tz
        else:
            os.environ.pop("DEFAULT_TIMEZONE", None)

    def test_default_timezone_when_env_unset(self):
        self.assertEqual(calendar_mod._get_default_timezone(), "Africa/Nairobi")
        self.assertEqual(todo_mod._get_default_timezone(), "Africa/Nairobi")

    def test_explicit_timezone_respected(self):
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "Europe/London"}):
            self.assertEqual(calendar_mod._get_default_timezone(), "Europe/London")
            self.assertEqual(todo_mod._get_default_timezone(), "Europe/London")

    def test_empty_timezone_preserves_default(self):
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": ""}):
            self.assertEqual(calendar_mod._get_default_timezone(), "Africa/Nairobi")
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "   "}):
            self.assertEqual(todo_mod._get_default_timezone(), "Africa/Nairobi")

    def test_invalid_timezone_raises_clearly(self):
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "Invalid/Zone"}):
            with self.assertRaises(Exception) as ctx:
                calendar_mod._get_default_timezone()
        msg = str(ctx.exception)
        self.assertIn("invalid IANA timezone", msg)
        self.assertIn("Invalid/Zone", msg)

    def test_calendar_create_event_uses_configured_tz(self):
        fake = FakeMCP()
        calendar_mod.register_calendar_tools(fake)
        create_event = fake.tools["create_event"]
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "America/New_York"}), \
             patch.object(calendar_mod, "graph_post", return_value={"id": "ev-1"}) as m:
            create_event("user-1", "Meeting", "2026-01-01T10:00:00", "2026-01-01T11:00:00")
        data = m.call_args[0][1]  # graph_post(endpoint, data) — positional
        self.assertEqual(data["start"]["timeZone"], "America/New_York")
        self.assertEqual(data["end"]["timeZone"], "America/New_York")

    def test_calendar_create_event_default_tz_when_unset(self):
        fake = FakeMCP()
        calendar_mod.register_calendar_tools(fake)
        create_event = fake.tools["create_event"]
        with patch.object(calendar_mod, "graph_post", return_value={"id": "ev-1"}) as m:
            create_event("user-1", "Meeting", "2026-01-01T10:00:00", "2026-01-01T11:00:00")
        data = m.call_args[0][1]
        self.assertEqual(data["start"]["timeZone"], "Africa/Nairobi")
        self.assertEqual(data["end"]["timeZone"], "Africa/Nairobi")

    def test_todo_create_todo_task_uses_configured_tz(self):
        fake = FakeMCP()
        todo_mod.register_todo_tools(fake)
        create_todo_task = fake.tools["create_todo_task"]
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "Asia/Tokyo"}), \
             patch.object(todo_mod, "graph_post", return_value={"id": "t-1"}) as m:
            create_todo_task("user-1", "list-1", "Task", due_date="2026-06-12")
        data = m.call_args[0][1]
        self.assertEqual(data["dueDateTime"]["timeZone"], "Asia/Tokyo")

    def test_todo_create_todo_task_without_due_date_skips_tz_resolution(self):
        """When no due_date is supplied, _get_default_timezone() is never called,
        so an invalid DEFAULT_TIMEZONE must NOT raise."""
        fake = FakeMCP()
        todo_mod.register_todo_tools(fake)
        create_todo_task = fake.tools["create_todo_task"]
        with patch.dict(os.environ, {"DEFAULT_TIMEZONE": "Invalid/Zone"}), \
             patch.object(todo_mod, "graph_post", return_value={"id": "t-1"}) as m:
            create_todo_task("user-1", "list-1", "Task")  # no due_date
        data = m.call_args[0][1]
        self.assertNotIn("dueDateTime", data)


class TestSmtpConfig(unittest.TestCase):
    """Phase A2: SMTP_HOST/SMTP_PORT env configuration for notifier."""

    def setUp(self):
        notifier._last_notification_time.clear()
        self._orig_host = os.environ.get("SMTP_HOST")
        self._orig_port = os.environ.get("SMTP_PORT")
        os.environ.pop("SMTP_HOST", None)
        os.environ.pop("SMTP_PORT", None)

    def tearDown(self):
        for key, val in [("SMTP_HOST", self._orig_host), ("SMTP_PORT", self._orig_port)]:
            if val is not None:
                os.environ[key] = val
            else:
                os.environ.pop(key, None)

    def _send_configured(self, alert_type="smtp-test"):
        """Call send_alert with alerts enabled and smtplib mocked; return the smtplib mock."""
        with patch.object(notifier, "ALERT_EMAIL", "sender@example.com"), \
             patch.object(notifier, "ALERT_EMAIL_PASSWORD", "pw"), \
             patch.object(notifier, "ALERT_RECIPIENT", "recipient@example.com"), \
             patch.object(notifier, "smtplib") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.SMTP_SSL.return_value.__enter__.return_value = mock_server
            notifier.send_alert("subj", "msg", alert_type=alert_type)
            return mock_smtp

    def test_default_host_and_port(self):
        mock_smtp = self._send_configured()
        mock_smtp.SMTP_SSL.assert_called_once_with("smtp.gmail.com", 465)

    def test_env_overrides_respected(self):
        with patch.dict(os.environ, {"SMTP_HOST": "smtp.custom.example", "SMTP_PORT": "587"}):
            mock_smtp = self._send_configured(alert_type="smtp-override")
        mock_smtp.SMTP_SSL.assert_called_once_with("smtp.custom.example", 587)

    def test_valid_configured_port_passed_to_ssl(self):
        with patch.dict(os.environ, {"SMTP_PORT": "2525"}):
            mock_smtp = self._send_configured(alert_type="smtp-port")
        mock_smtp.SMTP_SSL.assert_called_once_with("smtp.gmail.com", 2525)

    def test_invalid_port_rejected(self):
        with patch.dict(os.environ, {"SMTP_PORT": "not-a-number"}):
            with patch.object(notifier, "ALERT_EMAIL", "sender@example.com"), \
                 patch.object(notifier, "ALERT_EMAIL_PASSWORD", "pw"), \
                 patch.object(notifier, "ALERT_RECIPIENT", "recipient@example.com"), \
                 patch.object(notifier, "smtplib") as mock_smtp:
                with self.assertRaises(Exception) as ctx:
                    notifier.send_alert("subj", "msg", alert_type="smtp-invalid")
        msg = str(ctx.exception)
        self.assertIn("SMTP_PORT", msg)
        self.assertIn("integer", msg)
        mock_smtp.SMTP_SSL.assert_not_called()

    def test_out_of_range_port_rejected(self):
        for bad in ["0", "65536", "-1", "99999"]:
            with self.subTest(port=bad):
                with patch.dict(os.environ, {"SMTP_PORT": bad}):
                    with patch.object(notifier, "ALERT_EMAIL", "sender@example.com"), \
                         patch.object(notifier, "ALERT_EMAIL_PASSWORD", "pw"), \
                         patch.object(notifier, "ALERT_RECIPIENT", "recipient@example.com"), \
                         patch.object(notifier, "smtplib") as mock_smtp:
                        with self.assertRaises(Exception):
                            notifier.send_alert("subj", "msg", alert_type=f"smtp-range-{bad}")
                    mock_smtp.SMTP_SSL.assert_not_called()

    def test_no_live_smtp_connection(self):
        # smtplib is fully mocked; the real smtplib.SMTP_SSL is never invoked.
        mock_smtp = self._send_configured(alert_type="smtp-nolive")
        self.assertTrue(mock_smtp.SMTP_SSL.called)
        self.assertIs(mock_smtp.SMTP_SSL.return_value.__enter__.return_value.sendmail.called, True)

    def test_credentials_not_exposed_in_port_error(self):
        with patch.dict(os.environ, {"SMTP_PORT": "bad"}):
            with patch.object(notifier, "ALERT_EMAIL", "secret-sender@example.com"), \
                 patch.object(notifier, "ALERT_EMAIL_PASSWORD", "super-secret-pw"), \
                 patch.object(notifier, "ALERT_RECIPIENT", "secret-recipient@example.com"), \
                 patch.object(notifier, "smtplib"):
                with self.assertRaises(Exception) as ctx:
                    notifier.send_alert("subj", "msg", alert_type="smtp-leak")
        msg = str(ctx.exception)
        self.assertNotIn("super-secret-pw", msg)
        self.assertNotIn("secret-sender", msg)
        self.assertNotIn("secret-recipient", msg)



class TestGraphGetAll(_GraphClientTestBase):
    """C1.1: graph_get_all pagination, continuation links, termination, errors."""

    def test_pagination_follows_next_link(self):
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "value": [{"id": 1}, {"id": 2}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me?next=2",
        }
        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {"value": [{"id": 3}]}
        with patch("requests.get", side_effect=[page1, page2]) as mock_get:
            result = graph_client.graph_get_all("me")
        self.assertEqual(result["total_returned"], 3)
        self.assertEqual([i["id"] for i in result["value"]], [1, 2, 3])
        self.assertEqual(mock_get.call_count, 2)

    def test_pagination_terminates_when_no_next_link(self):
        page = MagicMock()
        page.status_code = 200
        page.json.return_value = {"value": [{"id": 1}]}
        with patch("requests.get", return_value=page) as mock_get:
            result = graph_client.graph_get_all("me")
        self.assertEqual(result["total_returned"], 1)
        self.assertEqual(mock_get.call_count, 1)

    def test_max_items_truncates_results(self):
        page = MagicMock()
        page.status_code = 200
        page.json.return_value = {
            "value": [{"id": i} for i in range(10)],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/me?next=2",
        }
        with patch("requests.get", return_value=page) as mock_get:
            result = graph_client.graph_get_all("me", max_items=5)
        self.assertEqual(result["total_returned"], 5)
        self.assertEqual(len(result["value"]), 5)
        self.assertEqual(mock_get.call_count, 1)  # truncated before 2nd page

    def test_non_200_raises_sanitized(self):
        page = MagicMock()
        page.status_code = 404
        page.text = "NOT FOUND BODY - MUST NOT LEAK"
        with patch("requests.get", return_value=page):
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_get_all("me")
        self.assertIn("404", str(ctx.exception))
        self.assertNotIn("NOT FOUND BODY", str(ctx.exception))

    def test_malformed_json_raises_sanitized(self):
        page = MagicMock()
        page.status_code = 200
        page.json.side_effect = ValueError("bad json")
        with patch("requests.get", return_value=page):
            with self.assertRaises(Exception) as ctx:
                graph_client.graph_get_all("me")
        self.assertIn("invalid response", str(ctx.exception).lower())

    def test_429_bounded_retry_then_success(self):
        page429 = MagicMock()
        page429.status_code = 429
        page429.headers = {"Retry-After": "999999"}
        page_ok = MagicMock()
        page_ok.status_code = 200
        page_ok.json.return_value = {"value": [{"id": 1}]}
        with patch("requests.get", side_effect=[page429, page_ok]):
            result = graph_client.graph_get_all("me")
        self.assertEqual(result["total_returned"], 1)
        self.mock_time.sleep.assert_called_once_with(graph_client.MAX_RETRY_AFTER)


class TestServerRegistration(unittest.TestCase):
    """C1.2: each server entry point's registration sequence succeeds and exposes
    the expected number of tools. Replays the same register_*_tools sequence each
    entry point uses (does not import the entry-point files, which need the mcp
    package) — this still verifies that the composed registration surfaces all
    expected tools without error."""

    def _register(self, *register_fns):
        fake = FakeMCP()
        for fn in register_fns:
            fn(fake)
        return fake

    def test_planner_server_combined_entry_registers_54_tools(self):
        fake = self._register(
            planner_mod.register_planner_tools,
            email_mod.register_email_tools,
            calendar_mod.register_calendar_tools,
            users_mod.register_user_tools,
            teams_mod.register_teams_tools,
            onedrive_mod.register_onedrive_tools,
            sharepoint_mod.register_sharepoint_tools,
            contacts_mod.register_contacts_tools,
            todo_mod.register_todo_tools,
        )
        self.assertEqual(len(fake.tools), 54)
        for name in ["get_groups", "list_emails", "create_event", "list_todo_lists"]:
            self.assertIn(name, fake.tools)

    def test_core_server_registers_15_tools(self):
        fake = self._register(
            planner_mod.register_planner_tools,
            users_mod.register_user_tools,
            audit_mod.register_audit_tools,
            health_mod.register_health_tools,
        )
        self.assertEqual(len(fake.tools), 15)
        for name in ["get_groups", "health_check"]:
            self.assertIn(name, fake.tools)

    def test_communication_server_registers_44_tools(self):
        fake = self._register(
            email_mod.register_email_tools,
            calendar_mod.register_calendar_tools,
            teams_mod.register_teams_tools,
            contacts_mod.register_contacts_tools,
            meetings_mod.register_meetings_tools,
            drafts_mod.register_drafts_tools,
            shared_mailbox_mod.register_shared_mailbox_tools,
            presence_mod.register_presence_tools,
        )
        self.assertEqual(len(fake.tools), 44)
        for name in ["list_emails", "create_event"]:
            self.assertIn(name, fake.tools)

    def test_files_server_registers_38_tools(self):
        fake = self._register(
            onedrive_mod.register_onedrive_tools,
            sharepoint_mod.register_sharepoint_tools,
            todo_mod.register_todo_tools,
            onenote_mod.register_onenote_tools,
            excel_mod.register_excel_tools,
            search_mod.register_search_tools,
        )
        self.assertEqual(len(fake.tools), 38)
        for name in ["list_notebooks", "list_todo_lists"]:
            self.assertIn(name, fake.tools)


class TestTokenCache(unittest.TestCase):
    """C1.3: token cache reuse, expiry handling, and refresh behaviour."""

    def setUp(self):
        auth._token_cache = None
        auth._token_expiry = 0

    def test_cache_reuse_avoids_repeated_token_requests(self):
        with patch.object(auth, "requests") as mock_req:
            mock_req.post.return_value = _ok_response(
                200, json_data={"access_token": "cached-tok", "expires_in": 3600}
            )
            t1 = auth.get_token()
            t2 = auth.get_token()
        self.assertEqual(t1, "cached-tok")
        self.assertEqual(t2, "cached-tok")
        self.assertEqual(mock_req.post.call_count, 1)

    def test_token_refreshed_after_cache_expiry(self):
        with patch.object(auth, "requests") as mock_req:
            mock_req.post.return_value = _ok_response(
                200, json_data={"access_token": "tok", "expires_in": 3600}
            )
            auth.get_token()  # caches
            auth._token_expiry = 0  # force expiry
            t2 = auth.get_token()  # should re-request
        self.assertEqual(mock_req.post.call_count, 2)
        self.assertEqual(t2, "tok")

    def test_failed_auth_does_not_populate_cache(self):
        with patch.object(auth, "requests") as mock_req, \
             patch("notifier.alert_auth_failure"):
            mock_req.post.return_value = _err_response(401)
            with self.assertRaises(Exception):
                auth.get_token()
        self.assertIsNone(auth._token_cache)


if __name__ == "__main__":
    unittest.main()
