---
name: igi-cli
description: Use when working with IGI Fund Manager private operational data via the local `npx igi-cli` command instead of the MCP server, including searching pots, clients, introducers, retrieving user pots, assigning introducers, transferring introducer balances, updating pot names, and handling IGI CLI OAuth.
---

# IGI CLI

Use `npx igi-cli` from the repository root for IGI private operational tasks. Prefer JSON output, which is the default. The CLI talks to the remote IGI API and does not need a local database connection.

If the launcher reports missing dependencies, run the repository install first so the workspace bin and TypeScript runner are available.

## Authentication

Before database-backed commands, check auth:

```bash
npx igi-cli auth status
```

If unauthenticated, run:

```bash
npx igi-cli auth login
```

OAuth uses PKCE, opens a browser, receives the callback on localhost, and stores tokens in macOS Keychain with a file fallback. If OAuth dynamic client registration is unavailable, the environment must provide `IGI_CLI_CLIENT_ID` and `IGI_CLI_CLIENT_SECRET`.

API base URL is stored in the CLI and defaults to `https://api.igi.co.uk`.

Defaults stored in the CLI:

- API base URL: `https://api.igi.co.uk`
- OAuth issuer: `https://clerk.introducers.igifundmanager.com`

Required environment:

- `IGI_CLI_CLIENT_ID` and `IGI_CLI_CLIENT_SECRET` only if OAuth dynamic client registration is unavailable
- Optional: `IGI_CLI_API_BASE_URL`, `IGI_CLI_ISSUER`, `IGI_CLI_OAUTH_SCOPES`, `IGI_CLI_REDIRECT_PORT`

For local development only, `--skip-auth` or `IGI_CLI_SKIP_AUTH=1` bypasses the OAuth check.

## Commands

List available mirrored MCP tools:

```bash
npx igi-cli tools
```

Run the exact MCP-style tool name:

```bash
npx igi-cli tool igi_search_pot_reference --input '{"potReferences":"ABCD1234"}'
```

Friendly commands:

```bash
npx igi-cli search-pot-reference --pot-reference ABCD1234
npx igi-cli search-client-by-name --name "Jane Smith"
npx igi-cli search-introducer-by-name --name "Smith"
npx igi-cli get-user-pots --user-id user_123
npx igi-cli assign-introducer --client-id <uuid> --introducer-id <uuid>
npx igi-cli update-pot-name --pot-reference ABCD1234 --new-name "Emergency Fund"
npx igi-cli transfer-introducer-balance --introducer-id <uuid>
```

Batch inputs may be repeated flags, comma-separated values, or JSON arrays:

```bash
npx igi-cli search-client-by-name --name "Jane" --name "John"
npx igi-cli search-pot-reference --pot-references '["ABCD1234","EFGH5678"]'
```

## Safety

Before mutating commands, summarize the intended change unless the user explicitly asked to perform it. Mutating commands are:

- `assign-introducer`
- `update-pot-name`
- `transfer-introducer-balance`

Use `--text` only when the user wants human-readable output instead of JSON.
