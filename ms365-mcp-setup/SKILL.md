---
name: ms365-mcp-setup
description: Help the user configure, set up, troubleshoot, and use the self-hosted Microsoft 365 MCP AI Assistant server (ms365-ai-assistant-mcp). Activate when the user asks to install or configure the M365 MCP server, register a Microsoft Entra ID application for it, choose Microsoft Graph application permissions, connect an AI agent (e.g. Claude Desktop) to the server, diagnose server/authentication/Microsoft Graph errors, or understand which Microsoft 365 features work with app-only (client-credentials) authentication. Do not activate for general Microsoft 365 product questions unrelated to running this specific server.
---

# Microsoft 365 MCP AI Assistant — Setup & Usage Skill

This skill guides an AI coding agent to help a user install, configure, and run the
self-hosted `ms365-ai-assistant-mcp` server — a Python MCP (Model Context Protocol)
server that connects an AI agent to the user's own Microsoft 365 tenant via the
Microsoft Graph API, using OAuth 2.0 client-credentials (app-only) authentication.

## When to activate

Activate this skill when the user is working with the `ms365-ai-assistant-mcp`
repository and asks to:
- install, configure, or run the MCP server;
- register or configure a Microsoft Entra ID (Azure AD) application for it;
- choose or grant Microsoft Graph application permissions;
- connect an MCP-aware agent (e.g. Claude Desktop, Cursor) to the server;
- diagnose authentication, token, Graph API, or server startup errors;
- understand which Microsoft 365 features are supported with app-only auth.

Do not activate for unrelated Microsoft 365 product questions, general Python
help, or work unrelated to this server.

## Before recommending changes

1. **Inspect the existing repository first.** Read `README.md`, `docs/ARCHITECTURE.md`,
   `docs/azure-app-setup.md`, and `.env.example` in the project root before suggesting
   code or configuration changes. Do not assume the repository state — verify it.
2. **Use the supporting guides in this skill:**
   - `references/setup-guide.md` — prerequisites, install, config, server start, troubleshooting.
   - `references/permissions-guide.md` — Microsoft Graph application permissions, least privilege, limitations.
3. **Do not invent** tools, API endpoints, configuration variables, commands, or setup
   steps. Use only the variables, entry points, and commands documented in the repository
   (see `.env.example`, `docs/ARCHITECTURE.md`, and the 4 server entry points:
   `servers/core_server.py`, `servers/communication_server.py`, `servers/files_server.py`,
   and `planner_server.py`).

## Security — protect credentials

- **Never place secrets in source control.** `CLIENT_SECRET`, `MCP_API_KEY`, and
  `ALERT_EMAIL_PASSWORD` belong in `.env` only (which is gitignored). Never commit,
  paste, or print them.
- Do not echo tokens, client secrets, or tenant credentials into terminal transcripts,
  logs, or chat. The server redacts secrets in its audit log; the agent must not undo that.
- Help the user populate `.env` locally without revealing values in chat or diffs.

## Explicit approval before destructive actions

Require explicit user approval before any of:
- deleting or overwriting files;
- modifying source code, tests, dependencies, or configuration;
- running `git commit`, `git push`, `git reset`, `git checkout`/`git restore` over
  uncommitted work, `git clean`, or history rewrites;
- deploying the server or publishing anything to a marketplace.

Default to read-only inspection. Propose the smallest safe change and wait for approval.

## Preserve unrelated work

When performing a scoped task, do not modify unrelated code, tests, docs, or
configuration. Preserve all uncommitted and untracked files unless the user
explicitly authorizes touching them.

## Microsoft Graph access depends on granted permissions

The server authenticates as an Azure Entra ID application (app-only / client-credentials).
**Which M365 data the server can read or write is determined entirely by the application
permissions granted to that Entra ID app by a tenant administrator** — not by this skill
or the server code. Guide the user to grant only the permissions needed for the modules
they intend to run (see `references/permissions-guide.md`). App-only permissions grant
**tenant-wide** access (e.g. `Mail.ReadWrite` covers every mailbox), so least privilege
matters.

## Unsupported features and known limitations (app-only flow)

Do **not** promise the user that these work — they are limitations of the app-only
(client-credentials) flow, documented in `docs/ARCHITECTURE.md` and `docs/azure-app-setup.md`:

- **Excel workbook endpoints** (`tools/excel.py`) — Microsoft documents these as
  `Application: Not supported` for app-only flow. The Excel tools will fail at runtime.
- **Sending Teams channel messages** (`tools/teams.py`) — no general app-only permission
  exists (only `Teamwork.Migrate.All`, restricted to migration-mode channels).
- **`GET /users/{id}/manager`** (`tools/users.py`) — app-only unsupported per Microsoft's
  "Get manager" API page; prefer `$expand=manager`.
- No per-user isolation — granted permissions apply across the whole tenant.
- Live Microsoft 365 round-trips are not verified by the project's tests (which are mocked);
  have the user run the `health_check` tool against their tenant before relying on data tools.

If a feature is not documented as supported in the repository, treat it as unverified.

## Practical guidance

- Start with `references/setup-guide.md` for install + config.
- Use `references/permissions-guide.md` when the user asks about permissions or which
  modules to enable.
- Run the mocked test suite (`python -m unittest tests.test_p1 tests.test_tools`) to
  verify the code; run the `health_check` tool to verify live auth + Graph reachability.
- Keep instructions concise and grounded in the actual repository.
