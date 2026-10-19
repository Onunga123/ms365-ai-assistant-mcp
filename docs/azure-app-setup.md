# Microsoft Entra ID App Setup — Application Permissions

This document explains how to register the Microsoft Entra ID (Azure AD)
application required by the self-hosted `ms365-ai-assistant-mcp` server, and
maps each tool module's Microsoft Graph operations to the **application
permissions** the app must be granted.

The server uses the OAuth 2.0 **client-credentials (app-only) flow**, so it
authenticates as the application, not as a user. All permissions below are
**application permissions** (the `*.All` scope), which always require
**tenant-wide administrator consent**.

> **Access date for all Microsoft Learn URLs in this document:** 2026-10-19.
> The authoritative source is the Microsoft Graph permissions reference:
> <https://learn.microsoft.com/en-us/graph/permissions-reference> (there is no
> separate page that lists only application permissions — use the
> "Application" column on that page).

---

## 1. Application vs delegated permissions — why this matters here

Microsoft Graph permissions come in two flavours:

- **Delegated permissions** — the app acts *on behalf of* a signed-in user.
  The effective access is the intersection of the app's permission and the
  user's. Names like `Mail.Read`, `Mail.Read.Shared`, `Tasks.Read`,
  `ChannelMessage.Send`.
- **Application permissions** — the app acts *as itself*, with no signed-in
  user. The effective access is the **full** scope granted to the app, across
  the **entire tenant**. Names like `Mail.ReadWrite`, `User.Read.All`,
  `Files.ReadWrite.All`, `Tasks.ReadWrite.All`.

Because this server uses the **client-credentials (app-only) flow**, only
**application permissions** apply. Several delegated-only scopes the reader may
expect — `Mail.Read.Shared`, `Mail.Send.Shared`, `Tasks.Read`, `Files.Read`,
`Presence.Read`, `OnlineMeetings.Read`, `ChannelMessage.Send`, `User.Read` —
are **not available** to this server (their `Application` column is `-`). The
server must use the `*.All` application equivalents below.

> **Tenant-wide access.** Granting `Mail.ReadWrite` to an application permits
> reading/sending mail in **every** mailbox in the tenant — not one user's.
> The same is true for `Files.ReadWrite.All` (all OneDrive/SharePoint files),
> `User.Read.All` (all user profiles), `Presence.Read.All` (all users' presence),
> etc. Apply least privilege (§4), and for shared-mailbox-only scenarios apply
> an **Application Access Policy** to restrict `Mail.*` to specific mailboxes.

---

## 2. Step-by-step app registration

1. **Register the app.** In the Entra ID / Azure portal, go to
   **App registrations → New registration**, give it a name, choose
   *Accounts in this organizational directory only* (single-tenant), and
   create it. <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app>
2. **Add application permissions.** Under **API permissions → Add a permission
   → Microsoft Graph → Application permissions**, add the permissions from
   the table in §3 that correspond to the tool modules you intend to enable.
   Do **not** add permissions for modules you will not run — see §4 (least
   privilege). <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis>
3. **Grant admin consent.** Each application permission requires
   tenant-wide administrator consent. In the portal, click
   **Grant admin consent for <tenant>** on the API permissions blade, or use
   the admin-consent endpoint. <https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent>
4. **Create a client secret.** Under **Certificates & secrets → Client secrets
   → New client secret**, create a secret, record its `Value` immediately (it is
   only shown once) and its expiry. For production, prefer a **certificate** or
   **Workload Identity Federation / managed identity** over a secret — see §5.
5. **Record the three identifiers** for your `.env`:
   - `CLIENT_ID` = the app's Application (client) ID (Overview blade)
   - `TENANT_ID` = the Directory (tenant) ID (Overview blade)
   - `CLIENT_SECRET` = the secret Value from step 4 (or configure a certificate)
6. **Set `SECRET_EXPIRY_DATE`** in `.env` to the secret's expiry date so the
   server's `check_secret_expiry` tool can warn before rotation is due.

---

## 3. Tool-module → Graph application-permission mapping

This table traces each tool module's actual Graph operations (verified from the
source code) to the **application permission(s)** Microsoft documents for those
operations. Use the **least-privileged** permission that covers what the module
does (read-only modules need `Read` only; modules that create/update/delete need
`ReadWrite`).

Legend: **Required** = the module calls endpoints that need this permission.
**Admin consent** = Yes for all application permissions.

| Module | Graph operations (from code) | Application permission(s) | Admin consent | Notes / least-privilege |
|---|---|---|---|---|
| `tools/email.py` | `users/{id}/messages` (read), `users/{id}/mailFolders`, `users/{id}/sendMail`, `users/{id}/messages/{id}/reply` | `Mail.Read` (read), `Mail.Send` (send/reply) | Yes | Use `Mail.Read` if read-only; add `Mail.Send` only if sending. `Mail.ReadBasic.All` is even lower for metadata. |
| `tools/shared_mailbox.py` | `users/{mailbox}/messages`, `users/{mailbox}/sendMail`, `users/{mailbox}/mailFolders` | `Mail.Read` + `Mail.Send` | Yes | Same as email; consider an **Application Access Policy** to scope to the shared mailbox only. |
| `tools/calendar.py` | `users/{id}/events` (CRUD), `users/{id}/calendars` | `Calendars.Read` (read), `Calendars.ReadWrite` (CRUD) | Yes | Use `Calendars.Read` if read-only. |
| `tools/contacts.py` | `users/{id}/contacts` (CRUD), `users/{id}/contactFolders` | `Contacts.Read` (read), `Contacts.ReadWrite` (CRUD) | Yes | |
| `tools/presence.py` | `users/{id}/presence`, `communications/getPresencesByUserId` | `Presence.Read.All` | Yes | High-impact; presence is sensitive org data. |
| `tools/meetings.py` | `users/{id}/onlineMeetings` (CRUD), `communications/callRecords/{id}`, `communications/callRecords` | `OnlineMeetings.Read.All` / `OnlineMeetings.ReadWrite.All`, `CallRecords.Read.All` | Yes | Subject to Application Access Policy. |
| `tools/onedrive.py` | `users/{id}/drive/...` (CRUD), `users/{id}/drives` | `Files.Read.All` (read), `Files.ReadWrite.All` (CRUD) | Yes | |
| `tools/sharepoint.py` | `sites`, `sites/{id}/lists`, `sites/{id}/drives` | `Sites.Read.All` (read), `Sites.ReadWrite.All` (CRUD); scoped alt: `Sites.Selected` | Yes | Prefer `Sites.Selected` for scoped access. |
| `tools/todo.py` | `users/{id}/todo/lists` (CRUD), `users/{id}/todo/lists/{id}/tasks` (CRUD) | `Tasks.Read.All` (read), `Tasks.ReadWrite.All` (CRUD) | Yes | |
| `tools/onenote.py` | `users/{id}/onenote/notebooks/sections/pages` (CRUD), page content | `Notes.Read.All` (read), `Notes.ReadWrite.All` (CRUD) | Yes | `create_page` uses `graph_post_raw` with `application/xhtml+xml`. |
| `tools/excel.py` | `users/{id}/drive/items/{id}/workbook/worksheets|range|tables/...` | ⚠ **`Application: Not supported`** | — | See §6 limitation 1 — these endpoints are **not available to app-only flow**. The Excel tools will fail at runtime against a live tenant. |
| `tools/users.py` | `users`, `users/{id}`, `users/{id}/directReports`, `users/{id}/manager` | `User.Read.All` (least for app) | Yes | `directReports` works app-only; `manager` see §6 limitation 3. `User.ReadWrite.All` is higher — avoid. |
| `tools/planner.py` | `groups/{id}/planner/plans`, `planner/plans/{id}/buckets|tasks`, `planner/tasks` (POST/PATCH) | `Tasks.Read.All` (read), `Tasks.ReadWrite.All` (CRUD) | Yes | Same permission family as To Do. |
| `tools/teams.py` (read) | `teams/{id}/channels`, `teams/{id}/channels/{id}/messages` (GET), `teams/{id}/members`, `groups?$filter=...Team` | `Team.ReadBasic.All`, `ChannelMessage.Read.All`, `TeamMember.Read.All`, `Channel.ReadBasic.All` | Yes | |
| `tools/teams.py` (send) | `POST teams/{id}/channels/{id}/messages` | ⚠ **No general app-only permission** | — | See §6 limitation 2 — only `Teamwork.Migrate.All` (migration-mode channels). Send channel messages via a Teams app/bot (RSC) or delegated flow. |
| `tools/search.py` | `POST search/query` | `Files.Read.All` (least, for file search) | Yes | The search API requires the permission matching the content source searched. |
| `tools/audit.py` | (no Graph calls — reads local `audit.log`) | none | — | No Graph permission needed. |
| `tools/health.py` | `GET $metadata` (no auth required), token check | none (beyond the app registration itself) | — | Run `health_check` to validate auth + reachability. |

---

## 4. Principle of least privilege

Microsoft's guidance (<https://learn.microsoft.com/en-us/graph/auth/auth-concepts>):

> *"As a best practice, request the least privileged permissions that your app
> needs in order to access data and function correctly. Requesting permissions
> with more than the necessary privileges is poor security practice…"*

Concrete least-privilege recommendations for this server:

- **Grant only for the modules you will run.** If you will not use Teams,
  do not grant `ChannelMessage.Read.All` / `TeamMember.Read.All`. The modular
  server layout lets you run a subset (e.g. only `core_server.py` +
  `files_server.py`) — match permissions to what you expose.
- **Prefer `Read` over `ReadWrite`** when a module is used read-only.
- **Prefer `Sites.Selected` over `Sites.ReadWrite.All`** for scoped SharePoint
  access (configure the selected sites in SharePoint first).
- **Use an Application Access Policy** to restrict `Mail.Read`/`Mail.ReadWrite`/
  `Mail.Send` to specific mailboxes (including a single shared mailbox).
- **Prefer certificates / Workload Identity Federation / managed identities**
  over a client secret in production (see §5).

Several of the broad tenant-wide scopes this server may need —
`Mail.ReadWrite`, `Mail.Send`, `User.Read.All`, `Presence.Read.All`,
`Files.ReadWrite.All`, `Sites.ReadWrite.All`, `Group.ReadWrite.All` — are
commonly treated as **high-impact** by Microsoft and warrant admin review,
monitoring, and the *Detect and Remediate Illicit Consent Grants* guidance
(<https://learn.microsoft.com/en-us/microsoft-365/security/office-365-security/detect-and-remediate-illicit-consent-grants>).

---

## 5. Client-secret storage, rotation, and credential safety

- **Never commit credentials.** `.env` is gitignored in this repository; keep
  `CLIENT_SECRET` and `MCP_API_KEY` out of source control, out of logs, and out
  of agent transcripts. The server redacts secrets in the audit log, but that
  does not help if the secret is committed or pasted.
- **Use a secrets manager** (Azure Key Vault, etc.) for production, not a
  plaintext `.env`.
- **Prefer certificates** over client secrets in production —
  <https://learn.microsoft.com/en-us/entra/identity-platform/certificate-credentials>.
  Certificates can be used "anywhere a client secret could be used" and are not
  bounded by the secret lifetime cap.
- **Client-secret lifetime** — Microsoft caps client secrets at a maximum
  lifetime (≤ 397 days under current policy). Set a shorter expiry (e.g. 90
  days), record it in `SECRET_EXPIRY_DATE`, and rotate before expiry. The
  server's `check_secret_expiry` tool warns at 60 days (warning), 30 days
  (critical), and after expiry (expired). There is no single dedicated
  "secret-rotation" page; rotation guidance is distributed across:
  - <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis>
    (Add credentials)
  - <https://learn.microsoft.com/en-us/entra/identity-platform/certificate-credentials>
  - <https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow>
- **Rotation procedure:** create the new secret/certificate in the portal,
  record the new value, update `CLIENT_SECRET` + `SECRET_EXPIRY_DATE` in `.env`,
  restart the server, then revoke the old secret once the server is healthy.
  Never delete the old secret before the new one is verified working.

---

## 6. The role of `MCP_API_KEY` (does NOT replace Graph auth)

`MCP_API_KEY` is a **local startup-configuration check**, not a Graph
authentication or authorization mechanism. `auth.verify_server_key()` raises at
server startup if `MCP_API_KEY` is unset/empty, ensuring the operator has
explicitly configured the local server before it registers any tools.

- It does **not** authenticate the agent to the MCP server on a per-request
  basis (the server is a local stdio process launched by the agent).
- It does **not** authorize any Microsoft Graph call — Graph access is governed
  entirely by the Azure app's application permissions (§3).
- It does **not** replace Microsoft Entra ID authentication.

Do not rely on `MCP_API_KEY` as a security boundary against Graph access; treat
the Azure app's permission scope (§4) as the real authorization surface.

---

## 7. Known permission/feature limitations (verify before relying on them)

These were identified by tracing the code's Graph operations against the
official Microsoft Graph API reference pages. They are **limitations of the
app-only (client-credentials) flow**, not bugs in the server code:

1. **Excel workbook endpoints are app-only unsupported.** `tools/excel.py`
   calls `users/{id}/drive/items/{id}/workbook/...`; Microsoft documents these
   as `Application: Not supported` (confirmed on the `workbook-list-worksheets`
   and `workbook-list-tables` API pages). The Excel tools will fail at runtime
   against a live tenant with client-credentials. Workaround: use delegated
   permissions, or edit the `.xlsx` file content directly via `Files.ReadWrite.All`
   (e.g. OpenXML).
2. **Sending Teams channel messages has no general app-only permission.**
   `tools/teams.py` POSTs to `teams/{id}/channels/{id}/messages`. The only
   application permission that allows this is `Teamwork.Migrate.All`, which is
   restricted to channels in migration mode. There is no general tenant-wide
   application permission for a daemon to post channel messages; the delegated
   equivalent is `ChannelMessage.Send`. Use a Teams app/bot with
   resource-specific consent (RSC), or a delegated flow, for posting.
3. **`GET /users/{id}/manager` is app-only unsupported** per Microsoft's
   "Get manager" API page. `tools/users.py` calls this; runtime behaviour is
   unverified. Prefer `$expand=manager` (which the permissions reference lists
   as supported with `User.Read.All`) and confirm against the reference.
4. **`Calendars.ReadBasic`** appears on some API pages but is delegated-only
   (Application column = `-`). Use `Calendars.Read` / `Calendars.ReadWrite` for
   app-only calendar access.
5. **Online meetings app-only form** — `OnlineMeetings.Read.All` /
   `OnlineMeetings.ReadWrite.All` exist as application permissions and govern
   `/users/{id}/onlineMeetings` + `/communications/onlineMeetings` subject to an
   Application Access Policy; confirm the exact endpoint form against the
   cloud-communications API overview.

If any of the above is material to your use case, verify against the official
Microsoft Graph permissions reference
(<https://learn.microsoft.com/en-us/graph/permissions-reference>) and the
specific API reference page before deploying.

---

## 8. Official documentation links (accessed 2026-10-19)

- Microsoft Graph permissions reference (master, with the `Application` column):
  <https://learn.microsoft.com/en-us/graph/permissions-reference>
- Auth concepts (app-only access + least-privilege best practice):
  <https://learn.microsoft.com/en-us/graph/auth/auth-concepts>
- App registration quickstart:
  <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app>
- Configure application permissions + client credentials:
  <https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-configure-app-access-web-apis>
- Client-credentials (app-only) flow:
  <https://learn.microsoft.com/en-us/entra/identity-platform/v2-oauth2-client-creds-grant-flow>
- Grant tenant-wide admin consent:
  <https://learn.microsoft.com/en-us/entra/identity/enterprise-apps/grant-admin-consent>
- Certificate credentials (recommended over client secrets):
  <https://learn.microsoft.com/en-us/entra/identity-platform/certificate-credentials>
- Detect and remediate illicit consent grants:
  <https://learn.microsoft.com/en-us/microsoft-365/security/office-365-security/detect-and-remediate-illicit-consent-grants>
