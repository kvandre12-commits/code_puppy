# Repo Inventory

_Last updated: 2026-06-17_

## What this checkout is

This repository is primarily a **Code Puppy fork/working checkout** with a substantial **DroidPuppy Android overlay** embedded inside it.

At a high level:

- `code_puppy/` = the main Code Puppy application
- `code_puppy/plugins/` = installed/bundled plugin ecosystem
- `DroidPuppy/` = Android-native overlay, docs, contracts, and orchestra prototype
- `tests/` = broad regression coverage for core + plugins

## Current git identity

- Active branch: `droidpuppy`
- Working tree: clean at time of inventory
- Fork remote: `https://github.com/kvandre12-commits/code_puppy.git`
- Upstream remote: `https://github.com/mpfaffenberger/code_puppy.git`

## Built systems in this repo

### 1. Code Puppy core

Main app runtime lives in `code_puppy/`.

Important areas:
- `code_puppy/agents/` — agent runtime, agent manager, JSON agents, streaming, steering
- `code_puppy/callbacks.py` — plugin hook backbone
- `code_puppy/cli_runner.py` — CLI execution layer
- `code_puppy/config.py` — configuration and settings
- `code_puppy/mcp_/` — MCP support
- `code_puppy/messaging/` — internal messaging/event pieces

### 2. Plugin-first extension architecture

The repo strongly prefers adding features as plugins under `code_puppy/plugins/`.

Current scale snapshot:
- `code_puppy/plugins/`: 76 plugin directories
- many non-Android provider, safety, auth, UI, and utility plugins

### 3. DroidPuppy Android operating layer

`DroidPuppy/` is the Android-native layer and also mirrors plugin folders under:
- `DroidPuppy/code_puppy/plugins/`

Current DroidPuppy overlay scale:
- 35 Android-focused plugin directories

Major DroidPuppy families include:
- app launching / settings / friendly router
- browser launch and browser actions
- wireless ADB + CDP bridge/client
- UI dump / UI actions / input
- screenshots / notifications / handoff/share
- logcat / dumpsys / bugreport / support bundles
- app inventory / stack reports / workflow feasibility
- orchestration blueprint and workflow macro helpers
- master health checks (`droidpuppy_doctor`)

### 4. Orchestra prototype

`DroidPuppy/orchestra/` is a runnable vertical slice of the orchestration architecture.

Important files:
- `kernel.py` — durable SQLite state substrate
- `adapters.py` — watchlist/device/mock-broker adapters
- `planners.py` — planner registration and decomposition
- `orchestra_agent.py` — coordinator logic
- `run_demo.py` / `run_device_demo.py` / `run_approval_demo.py` / `run_pipeline_demo.py`

The architecture split documented here is:
- **SharpEdge decides WHAT**
- **DroidPuppy decides HOW**
- **Capabilities provide WITH WHAT**

### 5. Contracts layer

`DroidPuppy/contracts/v1/` contains versioned schemas for orchestration:
- intent
- task
- handoff
- observation
- result

These are the load-bearing boundary docs for the multi-layer architecture.

### 6. Workflow examples

There is at least one concrete workflow example in:
- `code_puppy/workflows/reddit_demo/workflow.json`

That demo proves a simple Android macro flow:
- launch Reddit
- dump UI
- capture screenshot
- send notification

### 7. Robinhood-related work present here

This checkout contains **Robinhood/OAuth research and delegation support**, not a full local broker implementation.

Relevant pieces here:
- `docs/robinhood_mcp_config_only_proof.md`
- `docs/robinhood_mcp_validation_tasks.md`
- `docs/mcp_oauth_http_report.md`
- `code_puppy/plugins/chatgpt_robinhood_delegate/`
- tests covering MCP OAuth and delegation behavior

## What appears to be outside this checkout

Based on current repo contents, the heavier **SharpEdge trading/cockpit/analytics/operator** implementation is mostly **not stored in this checkout**.

This repo references that architecture in:
- skills
- contracts/docs
- orchestra demos
- Robinhood planning docs

But the actual larger trading stack seems to live elsewhere or across separate repos/artifacts.

## Scale snapshot

At inventory time:
- ~150 directories
- ~1027 files
- ~14 MB tracked workspace content
- 397 test files
- 138 Python files within `code_puppy/` at depth <= 2

## Best source-of-truth docs

If you are tired and need the shortest path back into the system, start here:

1. `README.md` — Code Puppy core overview
2. `docs/AGENT_STACK_GOVERNANCE.md` — current stack layers, authority rules, repo boundaries
3. `DroidPuppy/README.md` — what the Android layer is
4. `DroidPuppy/docs/PLUGIN_REFERENCE.md` — full Android plugin/tool index
5. `DroidPuppy/docs/PLUGIN_OVERVIEW.md` — plugin families at a glance
6. `DroidPuppy/docs/ORCHESTRA_AGENT.md` — the architecture constitution
7. `DroidPuppy/contracts/README.md` — contract model and boundaries
8. `docs/robinhood_mcp_config_only_proof.md` — current Robinhood path in this repo

## Plain-English identity

If we need one sentence so we do not lose the plot:

> This repo is a Code Puppy fork with a serious Android-native extension layer (DroidPuppy), plus an early contract-driven orchestration system that points toward SharpEdge-style coordinated execution.
