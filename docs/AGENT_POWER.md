# Agent Power Rule

Code Puppy is an agent OS layer: it routes intent into scoped capabilities,
local execution, observation, and audit/replay. Coding is a core workflow, but
not the boundary of the system.

> No direct power. Only granted power.

Every new tool that can observe, mutate, launch, click, trade, connect, or
exfiltrate must answer these questions before it becomes broadly available:

1. What scope gates this?
2. Which agent can receive it?
3. Can it be revoked?
4. Is the grant/revoke logged?
5. Can the effective state be replayed from the log?

Code Puppy routes optional bridge capabilities through `/bridge` grants instead
of handing every agent every tool by default.

```text
/bridge list
/bridge grant browser-agent browser.read
/bridge tools browser-agent
/bridge audit browser-agent
/bridge replay browser-agent
/bridge revoke browser-agent browser.read
```

The bridge grant plugin persists current state in:

```text
~/.code_puppy/bridge_grants.json
```

and appends grant/revoke audit events to:

```text
~/.code_puppy/bridge_grants.audit.jsonl
```

This is capability routing, not a hard in-process sandbox. A malicious plugin can
still cheat because it is Python running in the same process. The rule is for the
normal tool registration path: bridge/tool plugins should either expose tools via
`register_agent_tools(agent_name)` after a grant, or check `has_scope(agent_name,
"scope.name")` before advertising sensitive tools.

## Context economy

A kennel is not AI memory. It is a local context object/cache that prevents the
agent OS from repeatedly paying to reconstruct the same context through massive
API calls.

```text
Token history -> Kennel
Kennels -> Working context
Working context -> Model
```

As agent systems mature, context reconstruction becomes more expensive than raw
computation. The OS should treat context as an asset: cache it locally, pack it
intentionally, route it into working context only when useful, and avoid paying
the model to rediscover what the system already knows.
