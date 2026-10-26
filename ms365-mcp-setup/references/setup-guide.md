# Setup Guide — Microsoft 365 MCP AI Assistant

This guide condenses the repository's `README.md`, `docs/ARCHITECTURE.md`,
`docs/azure-app-setup.md`, and `.env.example` into a quick setup reference. For
full detail, read those files in the cloned repository.

## Prerequisites

- **Python 3.12 or later** (verified on 3.12). On Windows, the `tzdata` package
  is required for IANA timezone validation; it is declared in `requirements.txt`
  as `tzdata; sys_platform == 'win32'`, so `pip install` gets it automatically.
- **A Microsoft Entra ID (Azure AD) application** the user is authorised to
  register and use, with application permissions granted by a tenant
  administrator (see `references/permissions-guide.md` and `docs/azure-app-setup.md`).
- **An MCP-aware agent** (e.g. Claude Desktop, Cursor) that can launch a stdio
  MCP server.

## 1. Get the repository

Clone the repository (use the actual remote if it differs):

```
git clone https://github.com/Onunga123/ms365-ai-assistant-mcp.git
cd ms365-ai-assistant-mcp
```

## 2. Create a Python virtual environment + install dependencies

```
python -m venv .venv
# activate:
#   Windows PowerShell:  .\.venv\Scripts\Activate.ps1
#   macOS/Linux:         source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` installs the `mcp` SDK, `requests`, `pydantic`, `starlette`,
`uvicorn`, `cryptography`, `PyJWT`, and (on Windows) `tzdata`. On Windows, `mcp`
also pulls `pywin32` as a transitive dependency — this is expected.

> **OneDrive note:** if the repo is inside a OneDrive-synced folder, `.venv` will
> sync and may cause file-lock errors during `pip install`. If that happens,
> recreate the venv outside OneDrive.

## 3. Configure `.env`

Copy `.env.example` to `.env` and fill in the values. **Never commit `.env`.**

```
cp .env.example .env      # Windows PowerShell: Copy-Item .env.example .env
```

Required variables (from `.env.example`):

| Variable | Purpose | Secret? |
|---|---|---|
| `CLIENT_ID` | Azure Entra ID app (client) ID | identifier |
| `TENANT_ID` | Azure tenant ID | identifier |
| `CLIENT_SECRET` | Azure app client secret | **secret** |
| `MCP_API_KEY` | Local MCP server startup key | **secret** |
| `SECRET_EXPIRY_DATE` | `YYYY-MM-DD` for expiry monitoring | — |
| `DEFAULT_TIMEZONE` | IANA timezone for calendar/To-Do events (default `Africa/Nairobi`) | — |
| `SMTP_HOST` / `SMTP_PORT` | Alert email SMTP server (default `smtp.gmail.com` / `465`) | — |
| `ALERT_EMAIL` / `ALERT_EMAIL_PASSWORD` / `ALERT_RECIPIENT` | Operational alert sender/recipient | `ALERT_EMAIL_PASSWORD` is **secret** |
| `REDACT_PII` / `VERBOSE_LOGGING` / `SILENT` | Audit-log behaviour | — |
| `EMAIL_BODY_FORMAT` / `MAX_TOP` | Email body format + page-size cap | — |

Populate sensitive values locally — do not paste them into chat or diffs.

## 4. Register the Microsoft Entra ID application

Follow `docs/azure-app-setup.md` and `references/permissions-guide.md` for the
exact steps: register the app, add the required **application** permissions,
grant **admin consent**, create a client secret, then set `CLIENT_ID`,
`TENANT_ID`, `CLIENT_SECRET`, and `SECRET_EXPIRY_DATE` in `.env`.

## 5. Choose + start an MCP server entry point

The project has 4 entry points (each is a stdio MCP server). Run **one** per agent
(they overlap — see `docs/ARCHITECTURE.md` §4):

| Entry point | Modules (tool count) |
|---|---|
| `servers/core_server.py` | Planner, Users, Audit, Health (15) |
| `servers/communication_server.py` | Email, Calendar, Teams, Contacts, Meetings, Drafts, Shared mailbox, Presence (44) |
| `servers/files_server.py` | OneDrive, SharePoint, To Do, OneNote, Excel, Search (38) |
| `planner_server.py` | a combined 9-module entry (54) |

Start it (with `.venv` active):

```
python servers/core_server.py
```

`verify_server_key()` runs at startup and aborts if `MCP_API_KEY` is unset. The
server runs over stdio (no inbound network listener).

## 6. Connect your agent

Use `docs/claude_desktop_config.example.json` as a template for the agent's MCP
config. Replace every `REPLACE_WITH_*` placeholder and the absolute path with
your own values. The example configures the `core_server.py` entry; replicate
the pattern for other entry points if needed.

## 7. Verify

- **Code (mocked, no credentials):** `python -m unittest tests.test_p1 tests.test_tools`
  → expect 115 tests OK.
- **Live auth + Graph reachability:** run the `health_check` tool (exposed by
  `core_server.py`) against your tenant. This requires a validly-configured
  `.env` and admin-consented permissions.

## Troubleshooting (safe, read-first)

- **`MCP_API_KEY environment variable not set. Server startup aborted.`** — set
  `MCP_API_KEY` in `.env` (it is a startup guard, not a Graph auth mechanism).
- **`Authentication failed with HTTP status …`** — check `CLIENT_ID`,
  `TENANT_ID`, `CLIENT_SECRET` validity; the client secret may be expired
  (run the `check_secret_expiry` tool).
- **`Graph API request failed with HTTP status 401/403`** — the Entra ID app
  lacks the required application permission or admin consent; see
  `references/permissions-guide.md`.
- **Excel / Teams-send / manager tools fail at runtime** — these are documented
  app-only limitations, not configuration issues; see `references/permissions-guide.md`.
- **Windows timezone error (`No time zone found with key …`)** — install `tzdata`
  (`pip install tzdata`); it is already declared in `requirements.txt` for Windows.

## What is documented vs needs a live tenant

The setup steps above are documented in the repository. **Live Microsoft Graph
round-trips have not been verified by the project's tests** (the 115 tests are
mocked). Run `health_check` against your own tenant to confirm auth + reachability
before relying on data tools.
