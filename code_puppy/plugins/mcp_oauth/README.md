# MCP OAuth Plugin

Adds generic OAuth support for remote MCP servers without stuffing auth logic into core.

## What it does

- stores per-server OAuth tokens under `~/.code_puppy` / XDG data
- can perform auth code + PKCE flows using the installed `mcp` client auth stack
- refreshes/injects bearer tokens before bound MCP servers auto-start
- adds slash commands:
  - `/mcp-oauth-auth <server>`
  - `/mcp-oauth-status [server]`
  - `/mcp-oauth-logout <server>`

## Example `mcp_servers.json`

```json
{
  "mcp_servers": {
    "robinhood": {
      "type": "http",
      "url": "https://agent.robinhood.com/mcp/trading",
      "oauth": {
        "enabled": true,
        "scope": "openid profile",
        "auto_authorize_on_autostart": true,
        "callback_port_range": [8765, 8795]
      }
    }
  }
}
```

## Optional OAuth fields

- `scope` or `scopes`
- `client_name`
- `client_metadata_url`
- `client_id`
- `client_secret`
- `token_endpoint_auth_method`
- `redirect_host`
- `callback_path`
- `callback_port_range`
- `callback_timeout`
- `manual_callback_only`
- `auto_authorize_on_autostart`
- `protocol_version`
- `expiry_buffer_seconds`

## Notes

- The currently validated v1 path is a remote `type: "http"` MCP server using bearer-token auth.
- Runtime bearer injection is in-memory only; it does **not** write your access token into `mcp_servers.json`.
- If a provider needs a one-time login, run `/mcp-oauth-auth <server>` first.
- If the MCP server is already running when you reauth or logout, restart it before expecting new OAuth headers to take effect.
- Token refresh is automatic when the provider issues a refresh token and the stored session can be renewed.
