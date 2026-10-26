# Permissions Guide — Microsoft 365 MCP AI Assistant

This guide condenses `docs/azure-app-setup.md` and `docs/ARCHITECTURE.md` on
Microsoft Graph permissions. The server uses OAuth 2.0 **client-credentials
(app-only)** flow, so it authenticates as an Azure Entra ID application, not a
user. All permissions below are **application permissions** (`*.All` scope),
which always require **tenant-wide administrator consent**.

## Application vs delegated permissions

- **Delegated** — the app acts on behalf of a signed-in user (e.g. `Mail.Read`,
  `Tasks.Read`, `ChannelMessage.Send`). **Not used by this server.**
- **Application** — the app acts as itself, with no signed-in user, across the
  **entire tenant** (e.g. `Mail.ReadWrite`, `User.Read.All`, `Files.ReadWrite.All`).
  **This is what the server requires.**

Several delegated-only scopes (`Mail.Read.Shared`, `Tasks.Read`, `Presence.Read`,
`ChannelMessage.Send`, `User.Read`, etc.) are **not available** to this server
(their `Application` column is `-`). Use the `*.All` application equivalents.

## Tenant-wide access (security implication)

Granting an application permission permits access across the **whole tenant** —
e.g. `Mail.ReadWrite` covers **every** mailbox, `Files.ReadWrite.All` covers
all OneDrive/SharePoint files, `User.Read.All` all user profiles. There is **no
per-user isolation**. Apply least privilege (below) and, for shared-mailbox
scenarios, an **Application Access Policy** to restrict `Mail.*` to specific
mailboxes.

## Least-privilege configuration (recommended)

- Grant permissions **only for the modules you will run** (match the entry point).
- Prefer `Read` over `ReadWrite` when a module is used read-only.
- Prefer `Sites.Selected` over `Sites.ReadWrite.All` for scoped SharePoint access.
- Use an Application Access Policy to scope `Mail.*` to specific mailboxes.
- Prefer certificates / Workload Identity Federation over client secrets in production.

## Mapping modules → application permissions

The table maps each tool module's Graph operations to the application permission(s)
Microsoft documents for them. **Admin consent = Yes for all application permissions.**

| Module | Application permission(s) | Notes |
|---|---|---|
| `tools/email.py`, `tools/shared_mailbox.py` | `Mail.Read` (read), `Mail.Send` (send) | shared mailbox: consider Application Access Policy |
| `tools/calendar.py` | `Calendars.Read` / `Calendars.ReadWrite` | |
| `tools/contacts.py` | `Contacts.Read` / `Contacts.ReadWrite` | |
| `tools/presence.py` | `Presence.Read.All` | high-impact; sensitive |
| `tools/meetings.py` | `OnlineMeetings.Read.All` / `OnlineMeetings.ReadWrite.All`, `CallRecords.Read.All` | subject to Application Access Policy |
| `tools/onedrive.py` | `Files.Read.All` / `Files.ReadWrite.All` | |
| `tools/sharepoint.py` | `Sites.Read.All` / `Sites.ReadWrite.All` (or `Sites.Selected`) | |
| `tools/todo.py` | `Tasks.Read.All` / `Tasks.ReadWrite.All` | |
| `tools/onenote.py` | `Notes.Read.All` / `Notes.ReadWrite.All` | `create_page` uses XHTML |
| `tools/excel.py` | ⚠ **Application: Not supported** | see limitations |
| `tools/users.py` | `User.Read.All` | `manager` endpoint: see limitations |
| `tools/planner.py` | `Tasks.Read.All` / `Tasks.ReadWrite.All` | same family as To Do |
| `tools/teams.py` (read) | `Team.ReadBasic.All`, `ChannelMessage.Read.All`, `TeamMember.Read.All` | |
| `tools/teams.py` (send) | ⚠ **no general app-only permission** | see limitations |
| `tools/search.py` | `Files.Read.All` (least, for file search) | |
| `tools/audit.py` | none (reads local `audit.log`) | |
| `tools/health.py` | none (beyond the app registration) | run `health_check` |

For the full operation→permission trace + official Microsoft Learn URLs, see
`docs/azure-app-setup.md` (accessed 2026-10-19).

## How to determine which permissions for a chosen entry point

Match permissions to the modules in the entry point you run:

| Entry point | Modules | Permissions to grant (least-privilege) |
|---|---|---|
| `servers/core_server.py` | planner, users, audit, health | `Tasks.Read.All`, `User.Read.All` |
| `servers/communication_server.py` | email, calendar, teams, contacts, meetings, drafts, shared_mailbox, presence | `Mail.Read`+`Mail.Send`, `Calendars.ReadWrite`, `Contacts.ReadWrite`, `Team.ReadBasic.All`+`ChannelMessage.Read.All`+`TeamMember.Read.All`, `OnlineMeetings.Read.All`+`CallRecords.Read.All`, `Presence.Read.All` |
| `servers/files_server.py` | onedrive, sharepoint, todo, onenote, excel, search | `Files.ReadWrite.All`, `Sites.Read.All`, `Tasks.ReadWrite.All`, `Notes.ReadWrite.All` |
| `planner_server.py` (combined) | planner, email, calendar, users, teams, onedrive, sharepoint, contacts, todo | the union of the above subsets |

Grant only what the modules you actually use require. Do **not** grant every
available permission by default.

## `MCP_API_KEY` is not Graph authorisation

`MCP_API_KEY` is a local startup guard — it prevents the server from running
without it configured. It does **not** authenticate the agent, does **not**
authorise any Graph call, and does **not** replace Microsoft Entra ID
authentication. Graph access is governed entirely by the Entra ID app's
application permissions.

## Known permission + feature limitations (app-only flow)

These are limitations of the app-only flow, not bugs. Do not assume they work:

1. **Excel workbook endpoints** (`tools/excel.py`) — Microsoft documents these as
   `Application: Not supported`; the Excel tools will fail at runtime.
   Workaround: edit the `.xlsx` directly via `Files.ReadWrite.All`, or use a
   delegated flow.
2. **Sending Teams channel messages** (`tools/teams.py`) — only
   `Teamwork.Migrate.All` supports app-only, restricted to migration-mode
   channels. Use a Teams app/bot with resource-specific consent, or a delegated
   flow, to post channel messages.
3. **`GET /users/{id}/manager`** (`tools/users.py`) — app-only unsupported per
   Microsoft's "Get manager" API page; prefer `$expand=manager` (supported with
   `User.Read.All`).
4. **`Calendars.ReadBasic`** appears on some API pages but is delegated-only —
   use `Calendars.Read` / `Calendars.ReadWrite` for app-only.

If documentation and implementation appear to disagree on a permission, record
the discrepancy for review rather than silently choosing one. Confirm any
uncertain permission against the official Microsoft Graph permissions reference
(<https://learn.microsoft.com/en-us/graph/permissions-reference>) before
deploying.
