# SharpEdge MCP System

Yep — absolutely.

We already have most of the parts. The funny part is we’re not starting from zero; we’re basically sitting on a half-built governed MCP platform already.

## What we already built

### Code Puppy gives us
- plugin-based extension points
- MCP server lifecycle management in `code_puppy/mcp_/`
- agent/server binding and autostart
- optional OAuth patterns via `code_puppy/plugins/mcp_oauth/`
- tool registration without hacking `command_line/`

### DroidPuppy gives us
- Android capability surfaces
- browser, CDP, intent, UI, notification, screenshot, logcat, dumpsys, workflow tools
- capability graph + runtime truth
- operational-world and context packet patterns

### Governance pieces we already have
- `authority_gateway` leases and audit
- `droidpuppy_context_*` canonical workflow state
- approval receipts
- Project OS supervisor + bus + isolated jobs
- Puppy Kennel memory/doctrine capture

So yes: we can make **our own MCP system here** instead of gluing together random vendor junk and praying.

## Recommended architecture

## 1) Thin capability adapters
Do **not** rewrite working DroidPuppy tools as giant new business logic blobs.

Make thin MCP-facing adapters around existing capability families:
- `sharpedge.android.device`
- `sharpedge.android.browser`
- `sharpedge.android.ui`
- `sharpedge.governance`
- `sharpedge.world`
- `sharpedge.memory`

Rule: **MCP servers adapt; existing tools do the real work.**

That keeps things DRY and avoids a giant god-server from hell.

## 2) Governance in front of execution
Every risky action should stay behind the stuff we already built:
- `approval_decision`
- authority lease minting
- approval receipts
- audit trail

Meaning:
- read-only MCP calls can stay easy
- write/destructive/device-control calls should require explicit lease/approval context
- no fake “autonomous” power fantasies, because that’s how you end up with cursed systems

## 3) Project OS as runtime shell
Use Project OS supervisor for:
- starting isolated MCP worker jobs
- sandboxing server processes
- publishing bus events
- operator snapshots and health checks

That gives us a real runtime spine instead of “uhhh just run a background Python file and believe in yourself.”

## 4) Repo-local plugin as the control plane
The cleanest first implementation is a project or builtin plugin that uses hooks like:
- `register_mcp_catalog_servers`
- `pre_mcp_autostart`
- `register_tools`
- `register_agent_tools`

That plugin becomes the local control plane for:
- curated first-party SharpEdge MCP servers
- auth/bootstrap prep before autostart
- server metadata and defaults
- policy-aware startup

## 5) Kennel as durable memory, not transport
Puppy Kennel should hold:
- doctrine
- decisions
- operator prefs
- durable workflow notes

It should **not** become the transport bus.

Memory is memory. Transport is transport. Separation of concerns, my beloved.

## MVP plan

### Phase 1 — local first-party MCP stack
Build a small first-party stack in this repo:
1. `sharpedge-mcp-control` plugin
2. one Android capability MCP surface
3. one governance MCP surface
4. one health/status command

### Phase 2 — governed startup
Add:
- pre-autostart credential refresh
- lease checks before risky servers expose write tools
- audit/event publication to Project OS bus

### Phase 3 — workflow-native orchestration
Add:
- workflow packet hydration before actions
- supervisor-managed isolated jobs
- consequence/audit feedback into journal + kennel

## What I would build first

If we do this sanely, first slice should be:
- a plugin folder
- a curated MCP catalog registration callback
- a tiny server definition for Android capability/status surfaces
- governance wrapper rules for risky actions

That gives us a real skeleton fast, without prematurely building a giant protocol cathedral.

## Hard rules
- keep servers thin
- reuse existing tool logic
- no ungated destructive/device-control writes
- no direct broker-style execution shortcuts
- no giant monolith server if 3-5 small servers are cleaner
- keep files under 600 lines

## Suggested folder direction

```text
.code_puppy/plugins/sharpedge_mcp_system/
  register_callbacks.py
  catalog.py
  policy.py
  bootstrap.py
  server_specs.py
```

Or builtin version:

```text
code_puppy/plugins/sharpedge_mcp_system/
  register_callbacks.py
  catalog.py
  policy.py
  bootstrap.py
  server_specs.py
```

## Implemented MVP scaffold

This repo now includes a builtin plugin scaffold at:

```text
code_puppy/plugins/sharpedge_mcp_system/
```

Current first-party catalog entries:
- `sharpedge-android-capability`
- `sharpedge-governance-readonly`

Current local surfaces:
- agent tool: `sharpedge_mcp_system_status`
- slash command: `/sharpedge-mcp`
- stdio server entrypoints:
  - `python -m code_puppy.plugins.sharpedge_mcp_system.servers.android_capability`
  - `python -m code_puppy.plugins.sharpedge_mcp_system.servers.governance`

Current bindings/install stance:
- local MCP install entries written to `~/.code_puppy/mcp_servers.json`
- `code-puppy` bound to `sharpedge-governance-readonly`
- `planning-agent` bound to `sharpedge-governance-readonly`
- repo JSON agents declare built-in bindings:
  - `workflow-state` → `sharpedge-governance-readonly`, `sharpedge-android-capability`
  - `governance-orchestrator` → `sharpedge-governance-readonly`
  - `lease-audit` → `sharpedge-governance-readonly`

These are intentionally thin and mostly read-oriented for the first pass.

## Bottom line

Yes.

Not only can we do it — we already have the important pieces:
- capability surfaces
- MCP lifecycle plumbing
- governance
- sandbox/runtime control
- durable memory

What’s left is mostly **composing them into a first-party SharpEdge MCP control plane**.

If you want, next I can scaffold the actual `sharpedge_mcp_system` plugin here so we stop talking about it like philosophers in a parking lot.
