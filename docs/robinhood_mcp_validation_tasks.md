# Robinhood MCP validation tasks

## Scope
These tasks are for a **configuration-only** validation pass.
Do **not** patch plugin/core code during this phase.

## Tasks
1. Create or update `~/.code_puppy/mcp_servers.json` with the Robinhood HTTP MCP entry.
2. Ensure the config uses:
   - `type: "http"`
   - `url: "https://agent.robinhood.com/mcp/trading"`
   - `oauth.enabled: true`
   - `oauth.scope: "internal"`
3. Start Code Puppy and confirm the `robinhood` server is recognized as OAuth-enabled.
4. Run `/mcp-oauth-auth robinhood`.
5. Complete Robinhood login in browser.
6. If localhost callback does not return cleanly, paste the callback URL/code manually.
7. Run `/mcp-oauth-status robinhood`.
8. Confirm an `access_token` was stored.
9. Confirm whether a `refresh_token` was also stored.
10. Start or restart the Robinhood MCP server after auth so fresh bearer headers apply.
11. Validate authenticated MCP initialize/tool discovery.
12. Limit validation to safe read-only capability checks.
13. Record exact failure point if validation does not pass:
    - metadata discovery
    - dynamic registration
    - callback handling
    - token exchange
    - runtime header injection
    - post-auth MCP session/tool discovery
14. Do not patch anything until the exact failure mode is identified.

## Success criteria
- `robinhood` is recognized as an OAuth-enabled MCP server
- OAuth flow completes
- `access_token` exists
- bearer auth is applied to HTTP MCP runtime
- MCP initialize/tool discovery works for read-only validation
