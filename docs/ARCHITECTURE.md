# Architecture — Microsoft 365 AI Assistant (MCP Server)

This document describes the architecture of the `ms365-ai-assistant-mcp` project as
implemented by the current source code. It is intended for operators who want to
run the server self-hosted with their own Microsoft Entra ID application.

> **Not verified against a live tenant.** The behaviour described here is derived
> from the source code and from mocked automated tests. No live Microsoft 365
> tenant was used to validate runtime Graph operations. Treat the runtime
> behaviour of the 97 tools as inferred, not proven, until you run the
> `health_check` tool against your own tenant.

## 1. Self-hosted MCP architecture

The project is a set of Python MCP (Model Context Protocol) servers built on the
`mcp` SDK's `FastMCP` class. Each server runs as a local process (stdio transport
by default) that an MCP-aware agent (for example Claude Desktop) launches and
communicates with over standard input/output.

The servers translate natural-language tool calls from the agent into Microsoft
Graph API v1.0 requests against the operator's own Microsoft 365 tenant, using
OAuth 2.0 client-credentials (app-only) authentication.

```
            ┌───────────────────────────┐
            │  MCP-aware agent           │
            │  (e.g. Claude Desktop)     │
            └─────────────┬──────────────┘
                          │ stdio (JSON-RPC over stdin/stdout)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Self-hosted MCP server (this project, Python + FastMCP)      │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ auth.py    │  │ graph_client │  │ tools/*.py (18 mods)  │  │
│  │ token mgt  │◄─┤ request helper├─┤ 97 @mcp.tool() fns   │  │
│  └─────┬──────┘  └──────┬───────┘  └──────────────────────┘  │
│        │                 │ verify_server_key() guard on startup│
│        ▼                 ▼                                    │
│  login.microsoftonline.com  graph.microsoft.com               │
│  (token endpoint)           (Graph v1.0 resources)            │
└───────────────────────────────────────────────────────────────┘
```

The server process holds the operator's Azure app credentials in environment
variables (never committed; see `.env.example` for the full list). It never
accepts inbound network connections; it only makes outbound HTTPS calls to
`login.microsoftonline.com` (token) and `graph.microsoft.com` (Graph), and
optionally `smtp.gmail.com` for operational alert emails.

## 2. Authentication and Microsoft Graph token acquisition

`auth.py` implements the OAuth 2.0 client-credentials flow:

- `CLIENT_ID`, `TENANT_ID`, `CLIENT_SECRET` are read from the environment at
  module import time.
- `get_token()` POSTs to `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
  with `grant_type=client_credentials` and `scope=https://graph.microsoft.com/.default`.
- The returned access token is cached in module-level `_token_cache` with an
  expiry computed as `now + expires_in - 60` seconds, so a cached token is reused
  until 60 seconds before it expires, after which a new token is requested.
- All outbound HTTP (the token POST) uses a finite `REQUEST_TIMEOUT = 30` seconds.
- Errors are sanitised: a non-200 status raises
  `"Authentication failed with HTTP status {status}."` (no response body); a
  timeout raises `"Authentication service timed out."`; a network error raises
  `"Authentication service is unavailable."`; malformed JSON raises
  `"Authentication service returned an invalid response."`.
- On auth failure, `notifier.alert_auth_failure` is best-effort invoked.

> **Important — app-only / tenant-wide scope.** Client-credentials authenticates
> the *application*, not a user. The permissions granted to the Azure app (see
> `docs/azure-app-setup.md`) therefore apply across the entire tenant — for
> example `Mail.ReadWrite` permits reading/sending mail in **every** mailbox,
> not just one user's. There is no per-user isolation. Operators must apply
> least privilege and, for shared-mailbox scenarios, an Application Access
> Policy.

## 3. The MCP API key guard (`verify_server_key`)

`auth.verify_server_key()` reads `MCP_API_KEY` from the environment and raises
if it is unset/empty, aborting server startup. Every server entry point calls
it at import time, before any tool is registered, so the server cannot start
without the key configured.

> **Scope of the guard.** `MCP_API_KEY` is a startup-configuration check that
> prevents the server from running without the key set. It is **not** a
> replacement for Microsoft Graph authentication or authorization, and it is
> not a per-request auth gate on Graph calls. Graph access is governed entirely
> by the Azure app's permissions. The `MCP_API_KEY` only ensures the operator
> has explicitly configured the local server.

## 4. Server entry points — three modular servers + one combined entry

The README states "three MCP servers". Inspecting the code, there are **four**
`.py` entry-point files, but they are not four independent servers in the
documented sense — three are the modular servers, and the fourth is a combined
convenience entry that overlaps with them:

| File | `FastMCP` name | Tool modules registered | Role |
|---|---|---|---|
| `servers/core_server.py` | `M365 Core` | planner, users, audit, health (4) | Modular server — core/admin |
| `servers/communication_server.py` | `M365 Communication` | email, calendar, teams, contacts, meetings, drafts, shared_mailbox, presence (8) | Modular server — communication |
| `servers/files_server.py` | `M365 Files` | onedrive, sharepoint, todo, onenote, excel, search (6) | Modular server — files/content |
| `planner_server.py` (repo root) | `M365 AI Assistant` | planner, email, calendar, users, teams, onedrive, sharepoint, contacts, todo (9) | **Combined** convenience entry — a subset of the 18 modules in one server |

The three modular servers together cover all 18 tool modules (4 + 8 + 6 = 18);
`planner_server.py` is a fourth, single-process entry that bundles 9 of those
modules together. Run **either** the three modular servers (for a split
deployment) **or** `planner_server.py` (for a single-process subset) — do not run
both simultaneously against the same agent unless you understand the overlap.

Every entry point calls `verify_server_key()` at startup and runs
`if __name__ == "__main__": mcp.run()`, which starts the FastMCP stdio transport.

## 5. Graph request helpers — retry, timeout, and error behaviour

`graph_client.py` is the shared request layer used by all tool modules. It
exposes:

- `graph_get(endpoint)`, `graph_post(endpoint, data)`,
  `graph_patch(endpoint, data, etag=None)`, `graph_delete(endpoint, etag=None)`
  — all routed through `_make_request`.
- `graph_get_all(endpoint, max_items=None)` — paged fetch following
  `@odata.nextLink` until the page count or `MAX_TOP` (default 200) is reached.
- `graph_get_etag(endpoint)` — fetches the `ETag` header for a resource without
  exposing the response body; used by Planner's optimistic-concurrency updates.
- `graph_post_raw(endpoint, body, content_type)` — POSTs a non-JSON body (used
  by OneNote page creation, which requires `application/xhtml+xml`).

Behaviour:

- **Timeouts.** Every outbound `requests.*` call uses `REQUEST_TIMEOUT = 30` s.
- **429 rate-limit retry.** Honours the `Retry-After` header. The value is
  parsed safely: `None`/malformed → default 10 s; negative → 0 s; oversized →
  capped at `MAX_RETRY_AFTER = 60` s. Retries are bounded by `MAX_RETRIES = 3`.
- **Transient 5xx retry.** `500/502/503/504` are retried **only for idempotent
  GET** (`graph_get`, `graph_get_etag`), with a linear backoff capped at 60 s,
  bounded by `MAX_RETRIES`. **POST/PATCH/DELETE are not retried on 5xx** (they
  are non-idempotent — retrying could duplicate writes); they alert and raise a
  sanitised error.
- **Errors are sanitised.** No `response.text` is ever raised or logged. Errors
  carry only the HTTP status code (e.g. `"Graph API request failed with HTTP
  status 503."`). 5xx responses best-effort alert via `notifier.alert_api_error`.

## 6. Error handling and log redaction

`logger.py` provides:

- `redact(text)` — **unconditionally** redacts sensitive patterns (the earlier
  `if not REDACT_PII: return text` short-circuit was removed). Redactions cover
  email addresses, JWT access tokens, UUIDs, `authorization`/`client_secret`/
  `password`/`access_token`/`refresh_token` assignments, `tenant_id`/`client_id`
  assignments, `?access_token=`/`code=`/`sig=` query parameters, and
  `response body`/`error body`/`exception details` lines.
- `log_action(tool_name, parameters)` — appends a JSON line to `audit.log` (in
  the repo root), redacting parameters and stripping query strings from
  endpoints. Verbosity is controlled by `VERBOSE_LOGGING`/`SILENT` env vars.
- `read_logs(last_n=50)` — reads the last N audit entries (used by the audit
  tool module).

`notifier.py` sends operational alert emails (auth failure, 5xx API error,
client-secret-expiry warning) via SMTP SSL. Subject and message are passed
through `redact()` before transmission. SMTP host/port are configurable
(`SMTP_HOST`/`SMTP_PORT`, defaulting to `smtp.gmail.com:465`); credentials come
from `ALERT_EMAIL`/`ALERT_EMAIL_PASSWORD`/`ALERT_RECIPIENT`. A 1-hour cooldown
per `alert_type` prevents alert storms.

## 7. Tool-module groupings

There are **18 tool modules** under `tools/` (excluding `__init__.py`), exposing
**97 `@mcp.tool()` functions** in total (counted via `@mcp.tool()` decorators
across the 18 modules). Per-module counts:

```
audit:2  calendar:6  contacts:6  drafts:6  email:6  excel:7  health:3
meetings:6  onedrive:6  onenote:7  planner:6  presence:3  search:4
shared_mailbox:5  sharepoint:7  teams:6  todo:7  users:4
```

Functional grouping (matching the modular servers):

- **Core/admin** — `planner`, `users`, `audit`, `health`
- **Communication** — `email`, `calendar`, `teams`, `contacts`, `meetings`,
  `drafts`, `shared_mailbox`, `presence`
- **Files/content** — `onedrive`, `sharepoint`, `todo`, `onenote`, `excel`,
  `search`

The default timezone for calendar/To-Do event creation is configurable via the
`DEFAULT_TIMEZONE` environment variable (defaults to `Africa/Nairobi`; validated
against the IANA database via `zoneinfo`).

## 8. Configuration and deployment boundaries

All configuration is via environment variables (see `.env.example`):

| Variable | Purpose | Secret? |
|---|---|---|
| `CLIENT_ID` | Azure app (Entra ID) application (client) ID | identifier |
| `TENANT_ID` | Azure tenant ID | identifier |
| `CLIENT_SECRET` | Azure app client secret | **secret** |
| `MCP_API_KEY` | Local MCP server startup key | **secret** |
| `SECRET_EXPIRY_DATE` | `YYYY-MM-DD` for expiry monitoring | — |
| `REDACT_PII` | (legacy, redaction is now unconditional) | — |
| `VERBOSE_LOGGING` / `SILENT` | Audit-log verbosity | — |
| `EMAIL_BODY_FORMAT` | `text`/`html` for `get_email` | — |
| `MAX_TOP` | Page-size cap for paged reads (default 200) | — |
| `DEFAULT_TIMEZONE` | IANA timezone for calendar/To-Do events | — |
| `SMTP_HOST` / `SMTP_PORT` | Alert email SMTP server | — |
| `ALERT_EMAIL` / `ALERT_EMAIL_PASSWORD` / `ALERT_RECIPIENT` | Alert sender/recipient | `ALERT_EMAIL_PASSWORD` is a **secret** |

Deployment: the server is a long-running local process launched by an MCP-aware
agent over stdio. There is no inbound network listener. Outbound HTTPS only
(token + Graph); optional SMTP for alerts. Secrets live in the operator's
`.env` (gitignored) — never commit them.

## 9. Known limitations and unverified behaviour

These limitations are **not** fixed by the source code and must be communicated
to operators:

1. **Excel workbook Graph endpoints are not supported by app-only flow.**
   `tools/excel.py` calls `users/{id}/drive/items/{id}/workbook/...`, which
   Microsoft documents as `Application: Not supported`. The client-credentials
   flow cannot drive these endpoints; the Excel tools will fail at runtime
   against a live tenant. (Workaround: use delegated permissions, or edit the
   .xlsx file directly via `Files.ReadWrite.All`.) See `docs/azure-app-setup.md`.
2. **Sending Teams channel messages has no general app-only permission.**
   `tools/teams.py` POSTs to `teams/{id}/channels/{id}/messages`. The only
   app-only permission that allows this is `Teamwork.Migrate.All`, restricted to
   migration-mode channels. There is no general tenant-wide application
   permission for a daemon to post channel messages. See
   `docs/azure-app-setup.md`.
3. **`GET /users/{id}/manager` is app-only unsupported** per Microsoft's
   "Get manager" API page. `tools/users.py` calls this; runtime behaviour
   against a live tenant is unverified. Prefer `$expand=manager` where possible.
4. **app-only = tenant-wide.** There is no per-user isolation; granted
   permissions apply across the whole tenant.
5. **Single-tenant only.** The client-credentials app operates on the tenant it
   is registered in; multi-tenant operation requires per-tenant app
   configuration.
6. **Python version.** The repository declares no `python_requires` (no
   `setup.py`/`pyproject.toml`). Verified on Python 3.12 only. The `zoneinfo`
   module (stdlib 3.9+) is used for timezone validation; on Windows, the `tzdata`
   pip package may be required for IANA name resolution.
7. **Live Graph round-trips unverified.** The 97 tool endpoints are inferred to
   work from their `graph_client` routing; they have not been exercised against
   an authorised tenant. Run `health_check` first to validate auth + reachability.
8. **No licence file.** The README references an MIT licence, but no `LICENSE`
   file is tracked and ownership/licensing authority is unresolved. Do not
   redistribute without resolving licensing (see the licensing-readiness note in
   the project audit report).

## 10. Related documents

- `docs/azure-app-setup.md` — Microsoft Entra ID app registration + the exact
  Graph application permissions per tool module + least-privilege guidance.
- `docs/claude_desktop_config.example.json` — minimal example agent
  configuration for connecting Claude Desktop to the local MCP server.
- `README.md` — setup quick-start (kept deliberately short).
