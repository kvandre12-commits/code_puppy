# Robinhood MCP configuration-only proof

## Claim
A first-pass native Robinhood MCP OAuth validation in Code Puppy can be attempted with **configuration only**.

This proof is limited to:
- existing `code_puppy/plugins/mcp_oauth/*`
- existing HTTP MCP startup in `code_puppy/mcp_/*`
- Robinhood's published OAuth metadata
- Termux-safe callback handling already present in the plugin

This proof does **not** claim live trading works.
It only claims the repo already has enough moving parts to attempt OAuth-backed Robinhood MCP validation without patching code first.

## Required config schema
Minimum `mcp_servers.json` entry:

```json
{
  "mcp_servers": {
    "robinhood": {
      "type": "http",
      "url": "https://agent.robinhood.com/mcp/trading",
      "oauth": {
        "enabled": true,
        "scope": "internal",
        "auto_authorize_on_autostart": false
      }
    }
  }
}
```

## Why this is enough for a first validation attempt
The current plugin already supports:
- OAuth Authorization Code + PKCE
- localhost callback server
- manual callback paste fallback
- token storage
- refresh token reuse
- pre-autostart access-token preparation
- runtime `Authorization: Bearer <token>` injection for HTTP MCP servers

The current HTTP MCP startup path already supports:
- `type: "http"`
- remote MCP URL
- runtime custom headers
- async lifecycle startup for `MCPServerStreamableHTTP`

Robinhood's published metadata already confirms:
- resource: `https://agent.robinhood.com/mcp/trading`
- bearer method: `header`
- scope: `internal`
- auth endpoint: `https://robinhood.com/oauth`
- token endpoint: `https://api.robinhood.com/oauth2/token/`
- registration endpoint: `https://agent.robinhood.com/oauth/trading/register`
- PKCE method: `S256`
- token endpoint auth method: `none`

That means the current plugin shape matches the provider shape closely enough to justify a config-only validation attempt.

## Required files
User-managed config file:
- `~/.code_puppy/mcp_servers.json`
- or `$XDG_CONFIG_HOME/code_puppy/mcp_servers.json` if `XDG_CONFIG_HOME` is explicitly set

Expected runtime token file after successful auth:
- `~/.code_puppy/mcp_oauth/robinhood.json`
- or the XDG data equivalent if `XDG_DATA_HOME` is explicitly set

## Exact startup sequence
1. Code Puppy loads `mcp_servers.json`
2. `MCPManager.sync_from_config()` registers the `robinhood` HTTP server
3. `ManagedMCPServer._create_server()` builds `MCPServerStreamableHTTP`
4. agent startup triggers the `pre_mcp_autostart` hook
5. `mcp_oauth` calls `ensure_access_token(...)`
6. stored token is reused, refreshed, or interactive OAuth begins
7. plugin performs its MCP `initialize` probe during auth setup
8. plugin injects `Authorization: Bearer <access_token>` into runtime HTTP headers
9. HTTP MCP server lifecycle starts
10. bound agent receives the authenticated HTTP MCP server instance

## Termux support status
Supported:
- localhost callback listener on `127.0.0.1`
- manual callback URL/code paste fallback

Caveat:
- browser auto-open from Termux may be flaky

This is not a blocker because the plugin already supports manual callback paste.

## Validation commands
First auth attempt:

```text
/mcp-oauth-auth robinhood
```

Status check:

```text
/mcp-oauth-status robinhood
```

## Pass criteria
Configuration-only proof is validated if all of these happen without code changes:
1. Code Puppy recognizes `robinhood` as an OAuth-enabled MCP server
2. OAuth flow starts successfully
3. an `access_token` is stored for `robinhood`
4. runtime bearer injection can be prepared for the HTTP MCP server
5. authenticated MCP initialize/tool discovery succeeds for safe read-only use

## Likely failure cases
Hard blockers:
- Robinhood refuses to issue usable `internal` scope
- dynamic registration fails and a static `client_id` is required
- token is minted but real MCP runtime needs extra session continuity not currently preserved

Recoverable annoyances:
- browser auto-open fails in Termux
- localhost callback times out and manual paste is needed
- server restart is required after auth so fresh headers apply

## Bottom line
The smallest sane next step is **not** a code patch.
It is a **config-only Robinhood validation attempt** using the existing `mcp_oauth` plugin and HTTP MCP startup path.
