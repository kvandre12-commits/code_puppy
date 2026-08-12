# Android Capability Graph Spec

## Why this exists

DroidPuppy is converging on something broader than "Android automation."
It is becoming an **Android execution runtime for agents**.

The key shift is this:

> A workflow should ask for an outcome, not an implementation.

Example:

- "compose Gmail draft"
- "open Walmart"
- "search the web"
- "tap the second button"
- "summarize this screenshot"

The runtime should choose the best currently-available adapter based on live
capabilities, prerequisites, and reliability.

---

## Core architecture

The planning/execution pipeline should be treated as:

```text
Intent
  ↓
Capability Discovery (Doctor / Audit)
  ↓
Surface Selection
  ↓
Execution Adapter
  ↓
Result + Audit
```

This is more general than Android UI automation.
It is a runtime contract for agents operating against Android surfaces.

---

## Design principles

### 1. Workflows ask for outcomes

A workflow should express intent like:

- compose draft
- open app
- share file
- read browser page
- inspect UI
- capture screen

It should not hard-code:

- `am start`
- `adb shell uiautomator`
- CDP selector clicks
- share-sheet navigation

Those belong to adapters.

### 2. Adapters are replaceable

The same requested effect may be satisfiable by multiple adapters.

Example: `email.report.send_or_draft`

Possible adapters:
- Gmail intent draft
- generic Android SEND intent
- browser Gmail compose flow via CDP
- future native Android mail service

The planner should choose the best available one.

### 3. Capability is graded, not binary

"ADB required" is too coarse.
The planner needs a richer truth model describing:

- whether something is available
- how it was verified
- what prerequisites are missing
- how reliable it is

### 4. Doctors are first-class planning inputs

DroidPuppy's doctor pattern is one of its strongest ideas.
Doctors should not merely help humans debug after failure.
They should be consumed by the planner **before execution**.

### 5. Result + audit are part of execution

An action is not complete when a command exits.
It is complete when the runtime can report:

- requested intent
- selected adapter
- execution evidence
- success/failure
- fallback considered
- blockers observed

---

## Existing foundation already in repo

A lightweight version of this already exists in `droidpuppy_doctor`:

- `surface_inventory`
- `capability_routes`
- surface `availability`
- surface `verification`
- surface `blockers`
- connected ADB device count

And `authority_gateway_status()` already snapshots the execution topology from
that doctor output.

So the next layer should **promote and normalize** these structures, not replace
them with a separate fantasy taxonomy.

---

## Capability graph model

The graph should unify three kinds of nodes:

### 1. Capability nodes

These describe what an agent wants to accomplish.

Examples:
- `android.app.launch`
- `android.settings.open`
- `android.intent.send`
- `android.browser.open_url`
- `android.browser.dom.read`
- `android.browser.dom.act`
- `android.ui.inspect`
- `android.ui.act`
- `android.screen.capture`
- `android.share.text`
- `android.share.file`
- `android.worker.background.once`

Capability nodes are planner-facing.

### 2. Surface nodes

These are execution environments or channels.

Examples:
- `android_core`
- `browser_launch`
- `browser_dom`
- `ui_automation`
- `screen_capture`
- `device_diagnostics`
- `share_sheet`
- `termux_worker`
- `future_native_service`

Surface nodes explain where an action can happen.

### 3. Adapter nodes

These are the concrete implementations.

Examples:
- `adapter.intent.am_start`
- `adapter.intent.am_send`
- `adapter.browser.cdp.open_and_read`
- `adapter.ui.adb_uiautomator_tap`
- `adapter.share.termux_share`
- `adapter.termux.command`
- `adapter.worker.one_shot`
- `adapter.native.android_service` (future)

Adapters are execution-facing.

---

## Suggested record shapes

### Capability record

```json
{
  "capability_id": "android.app.launch",
  "label": "Launch Android app",
  "intent_kinds": ["open_app", "switch_surface"],
  "preferred_surfaces": ["android_core"],
  "fallback_surfaces": [],
  "success_contract": "target package launch intent dispatched successfully"
}
```

### Surface record

```json
{
  "surface_id": "browser_dom",
  "label": "Browser DOM automation through CDP",
  "availability": "ready",
  "verification": "deep_verified",
  "reliability": "conditional",
  "score": 0.68,
  "blockers": [],
  "prerequisites": [
    "adb_installed",
    "adb_connected",
    "supported_browser_present",
    "cdp_socket_reachable"
  ],
  "recommended_tools": [
    "android_browser_read_page",
    "android_browser_click_selector",
    "android_browser_fill_input"
  ]
}
```

### Adapter record

```json
{
  "adapter_id": "adapter.intent.am_start",
  "surface_id": "android_core",
  "capability_ids": ["android.app.launch"],
  "tool_name": "android_launch_app",
  "reliability": "reliable",
  "score": 0.95,
  "prerequisites": ["android_core_commands"],
  "evidence_kind": "command_exit_and_intent_dispatch"
}
```

### Workflow record

```json
{
  "workflow_id": "email.report.draft",
  "goal": "Draft an email with report content",
  "required_capabilities": ["android.intent.send"],
  "preferred_app_packages": ["com.google.android.gm"],
  "fallback_order": [
    "adapter.intent.gmail_draft",
    "adapter.intent.generic_send",
    "adapter.browser.gmail_compose"
  ]
}
```

---

## Capability score model

The planner should compute or ingest a score instead of using only binary
labels like "ready" / "blocked".

### Suggested qualitative statuses

- `reliable`
- `conditional`
- `degraded`
- `blocked`

### Suggested numeric score

Range: `0.0` to `1.0`

Example interpretation:
- `0.90 - 1.00` → highly reliable
- `0.70 - 0.89` → usable with minor caveats
- `0.40 - 0.69` → conditional / likely to need operator help
- `0.00 - 0.39` → effectively blocked

### Suggested score inputs

- platform present
- command/tool installed
- doctor verification depth (`inferred`, `observed`, `deep_verified`)
- active blockers count
- known package/app presence
- ADB connected device count
- historical success rate (future)
- operator-confirm requirement (future weighting)

### Example human-facing matrix

| Capability | Status | Notes |
|---|---|---|
| Launch app |  Reliable | Android core ready |
| Open settings |  Reliable | Android core ready |
| Send Android intent |  Reliable | `am` / intent routing works |
| Share text/file |  Reliable | Termux/API + Android share path available |
| Browser handoff |  Reliable | Brave/Chrome present |
| Browser DOM (CDP) |  Conditional | Needs Wireless Debugging / ADB / CDP |
| Native app UI automation |  Conditional | Needs ADB + UI dump path |
| Screen capture |  Conditional | Needs ADB connection |
| Background scheduled worker |  Reliable | Termux scheduler + one-shot workers |

This is the language agents should plan against.

---

## Planner behavior

Given a requested workflow intent:

1. identify required capabilities
2. query capability graph
3. rank candidate adapters by:
   - capability score
   - preferred surface order
   - app/package preference
   - prerequisite satisfaction
   - governance cost / required lease scope
4. select best adapter
5. execute
6. emit result + audit envelope
7. if execution fails, attempt the next allowed fallback adapter

### Example

Request:

```text
Email this report
```

Planner reasoning:

1. workflow requires `android.intent.send`
2. Gmail installed
3. Android core surface is ready and reliable
4. choose Gmail draft intent adapter
5. if Gmail package unavailable, fall back to generic SEND intent
6. if app intent path is blocked, optional future fallback could be browser Gmail compose

---

## Example adapter selection table

| User intent | Preferred adapter | Fallbacks |
|---|---|---|
| Email this report | Gmail intent draft | generic SEND intent, browser Gmail compose |
| Open Walmart | app launch | browser handoff |
| Search the web | browser handoff | Google app launch + search intent |
| Tap second button | UI automation | none unless app has an intent route |
| Summarize this screenshot | one-shot worker over eyes inbox | operator review gate |

The workflow should not care which route wins.
It should care whether the runtime can honestly fulfill the requested effect.

---

## Doctor integration contract

Every doctor should be able to contribute structured facts into the graph.

### Existing candidates

- `droidpuppy_doctor`
- `android_setup_doctor`
- `android_cdp_doctor`
- `android_ui_dump_doctor`
- `android_screen_capture_doctor`
- `android_notification_doctor`
- `android_app_inventory_doctor`
- `android_workflow_feasibility_assess`

### Normalization goal

Doctor outputs should eventually reconcile into a single packet like:

```json
{
  "capabilities": [...],
  "surfaces": [...],
  "adapters": [...],
  "apps": [...],
  "workflows": [...],
  "updated_at": "..."
}
```

That becomes the planner's source of truth.

### Runtime truth should be evidence-backed

The runtime should not treat truth as only a disposable snapshot.
It should preserve the evidence that produced the current truth model.

That means the observation layer should be able to record facts like:

- probe name
- timestamp
- target surface or package
- success / failure
- reason or blocker
- raw evidence reference where appropriate

Example:

```text
09:41:02 android_cdp_probe FAILED reason=pairing_required
09:42:17 intent_bridge PASSED
09:42:18 clipboard PASSED
```

The capability graph can still publish a current-state packet, but it should be
possible to explain why the packet changed over time.

This improves:

- auditability
- deterministic debugging
- confidence transitions when device state changes
- future learning from repeated probe outcomes

A useful rule is:

> snapshots are for planning; evidence trails are for trust.

---

## App, tool, and workflow advertisements

The graph should also support advertised facts from three domains.

### App advertisement

Each app can advertise:
- package name
- launch support
- share target support
- browser handoff relevance
- known deep-link / intent actions
- whether native UI automation is likely needed

### Tool advertisement

Each tool or adapter can advertise:
- supported capability ids
- prerequisites
- evidence type
- reliability band
- lease/governance footprint

### Workflow advertisement

Each workflow can advertise:
- desired outcome
- required capabilities
- preferred apps
- acceptable fallbacks
- review requirements

---

## Why one-shot workers still fit

This architecture is compatible with Android reality because execution does not
require a forever-daemon pretending the OS won't eventually body-check it.

The existing one-shot worker pattern is still correct:

- bounded scan
- bounded claims
- typed artifacts
- optional review gate
- clean exit

That fits Android much better than a permanent loop.

So the capability graph should plan **what to run**, while one-shot workers
remain a good answer for **where deferred work executes**.

---

## Recommended implementation path

### Phase 1 — normalize current doctor topology

Extend the existing `surface_inventory` / `capability_routes` concept into a
first-class exported capability graph packet.

Deliverable:
- `android.capability_graph.v1` artifact/tool output

Suggested code shape at this stage:
- `runtime_truth.py` collects observed facts
- `tooling.py` assembles and returns the public packet
- adapter compilation may remain a small local function until it earns
  extraction

### Phase 2 — extract adapter compilation when it grows

Do not split code only because a future architecture diagram said so.
Extract compilation logic when there are enough adapter families or enough
selection logic that the separation becomes clearer than the inline version.

At that point:
- `runtime_truth.py` should observe reality only
- `compiler.py` should reason over facts into adapters and synthesized
  capabilities
- `tooling.py` should expose the public API only

Deliverable:
- planner can choose between multiple adapters for the same capability
- compiler logic is testable with synthetic runtime-truth inputs

### Phase 3 — add workflow planner

Planner takes a requested effect and returns:
- selected adapter
- prerequisites
- confidence / score
- fallback order
- review requirements

Deliverable:
- `android_workflow_plan(...)`

### Phase 4 — app-specific advertisements

Let app/workflow plugins advertise richer package-level facts.

Deliverable:
- app capability inventory and package-aware planning

---

## Non-goals

This graph should not:
- pretend all apps are deeply automatable
- hide operator approvals that actually matter
- collapse reliability and availability into one boolean
- require every capability to use ADB

The whole point is honest planning.

---

## Short version

DroidPuppy should evolve toward:

> **intent-driven planning over a live Android capability graph, with adapter
> selection based on availability, prerequisites, and reliability.**

That is the bridge from "bag of Android tools" to **Android execution runtime
for agents**.
