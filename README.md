# Microsoft 365 AI Assistant (MCP Server)

A Model Context Protocol (MCP) server system that connects Claude AI to Microsoft 365, enabling AI-assisted management of emails, calendar, Planner tasks, Teams, OneDrive, SharePoint, OneNote, Excel, and more through natural language conversation.

## Overview

This system exposes 97 tools across 18 tool modules, exposed through three modular MCP servers (plus a combined convenience entry point). Counts are derived from the `@mcp.tool()` decorators and module files under `tools/`; see `docs/ARCHITECTURE.md` for the per-module breakdown and the entry-point relationship.

- **m365-core** — Planner, Users, Audit, Health monitoring
- **m365-communication** — Email, Calendar, Teams, Meetings, Contacts, Drafts, Shared mailbox, Presence
- **m365-files** — OneDrive, SharePoint, OneNote, Excel, To Do, Search

A fourth entry point, `planner_server.py` at the repository root, bundles 9 of the 18 modules into a single combined `M365 AI Assistant` server. Run **either** the three modular servers **or** the combined entry point — not both simultaneously against the same agent.

## Why This Project

Built to explore whether an organisation's Microsoft 365 environment could be made fully conversational through Claude — letting a user manage tasks, emails, calendars, and files in plain English rather than navigating multiple separate applications.

## Setup

1. Clone this repository
2. Copy `.env.example` to `.env` and fill in your own Microsoft Entra ID app credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Register an app in Azure Entra ID and grant the required Microsoft Graph application permissions (see `docs/azure-app-setup.md`)
5. Configure Claude Desktop using the example config in `docs/claude_desktop_config.example.json` (replace every `REPLACE_WITH_*` placeholder and the absolute path with your own values)

## Security Features

- OAuth 2.0 client credentials authentication with automatic token refresh
- API key verification on server startup
- Audit logging with PII redaction
- Rate limiting with automatic retry
- Health check and secret expiry monitoring
- Error notification system

## Architecture

See `docs/ARCHITECTURE.md` for full technical documentation.

## Tech Stack

Python, Model Context Protocol (MCP) SDK, Microsoft Graph API, OAuth 2.0

## License

Proprietary commercial licence. See [LICENSE](./LICENSE) for the applicable terms.
