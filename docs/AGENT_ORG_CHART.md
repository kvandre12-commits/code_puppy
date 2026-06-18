# Agent OS Org Chart

Code Puppy is an agent OS layer. If it is going to replicate the work of large
teams, it needs a hierarchy: departments, duties, authorities, handoffs, and
inspection points. The goal is not one giant genius agent. The goal is a managed
agent organization that turns intent into safe local execution.

```text
Operator intent
  -> Executive control
  -> Product / architecture / planning
  -> Department agents
  -> Specialist workers
  -> Verification
  -> Audit / replay / kennel context
```

## Prime directive

No direct power. Only granted power.

Every department owns decisions and artifacts, not unrestricted tools. Powerful
capabilities are routed through bridge grants, logged, and replayable.

## Control hierarchy

### 0. Operator

Human owner. Final authority for destructive operations, live broker actions,
security-sensitive changes, releases, and scope changes.

Responsibilities:

- sets mission and constraints;
- approves high-risk actions;
- decides product direction;
- can override or shut down any workflow.

### 1. Executive agents

Executive agents translate operator intent into controlled workstreams.

#### Chief Agent Officer

Owns the agent organization itself.

Responsibilities:

- decomposes missions into department work;
- assigns responsible agents;
- prevents duplicate work;
- enforces handoff artifacts;
- resolves department conflicts.

Artifacts:

- mission brief;
- department assignment plan;
- final operator summary.

#### Safety Governor

Owns authority, approvals, and blast-radius control.

Responsibilities:

- applies the Agent Power Rule;
- classifies risk tiers;
- blocks unsafe autonomy;
- verifies grant/revoke/audit coverage.

Artifacts:

- approval decision;
- risk register;
- grant manifest.

#### Context Governor

Owns kennel hygiene and context economy.

Responsibilities:

- decides what enters working context;
- promotes durable facts to notes;
- prunes transcript sludge after approval;
- prevents token-burn regressions.

Artifacts:

- context pack report;
- kennel audit;
- prune plan.

## Product and design department

### Product Manager Agent

Turns vague goals into user-facing product requirements.

Responsibilities:

- defines target user and problem;
- writes acceptance criteria;
- prevents feature sprawl;
- keeps Android agent OS positioning coherent.

Artifacts:

- product brief;
- user stories;
- acceptance checklist.

### UX / Droid Cockpit Agent

Owns the phone-facing workflow experience.

Responsibilities:

- designs local viewer screens;
- keeps bridge plumbing hidden unless needed;
- makes workflow state understandable;
- designs first-run setup and recovery paths.

Artifacts:

- screen map;
- workflow UI spec;
- first-run checklist.

### Documentation Agent

Owns operator and contributor docs.

Responsibilities:

- converts architecture into readable docs;
- keeps README, Android plan, and agent rules aligned;
- writes runbooks;
- removes stale claims.

Artifacts:

- docs diff;
- runbook;
- release notes.

## Architecture department

### Systems Architect Agent

Owns the OS spine.

Responsibilities:

- defines layer boundaries;
- keeps plugins over core where possible;
- designs event, workflow, and bridge contracts;
- prevents god-object agent design.

Artifacts:

- architecture decision record;
- interface contract;
- dependency map.

### Android Platform Architect Agent

Owns Droid-native constraints.

Responsibilities:

- designs Termux, browser, ADB, and future APK paths;
- keeps phone install small;
- separates Android viewer from backend runtime;
- ranks on-device observation seams.

Artifacts:

- Android capability matrix;
- bridge setup plan;
- distribution plan.

### Security Architect Agent

Owns credentials, OAuth, broker boundaries, and secret handling.

Responsibilities:

- forbids credential capture in kennel;
- designs token storage boundaries;
- verifies redaction and audit logs;
- separates read, draft, and write authority.

Artifacts:

- security review;
- credential boundary map;
- approval policy.

## Engineering department

### Core Runtime Agent

Owns Code Puppy runtime behavior.

Responsibilities:

- agent construction;
- tool registration;
- model/provider loading;
- plugin lifecycle;
- graceful optional dependency handling.

Artifacts:

- runtime patch;
- compatibility notes;
- regression tests.

### Plugin Engineer Agent

Owns plugin-first feature delivery.

Responsibilities:

- implements callbacks;
- avoids command-line core edits when hooks exist;
- keeps files under 600 lines;
- splits cohesive submodules before soup happens.

Artifacts:

- plugin module;
- hook registration summary;
- tests.

### Droid Bridge Engineer Agent

Owns Android/browser/ADB bridges.

Responsibilities:

- maps bridge scopes to tools;
- tests live Droid commands;
- keeps dangerous tools grant-gated;
- records observe/act/verify events.

Artifacts:

- bridge catalog;
- scope-tool map;
- live capability report.

### Cockpit Engineer Agent

Owns the local Droid viewer.

Responsibilities:

- implements workflow monitor;
- exposes status/workflow/events JSON;
- adds controls without leaking dangerous power;
- keeps stdlib-only until pain justifies more.

Artifacts:

- viewer patch;
- smoke report;
- UI test coverage.

### Context Engineer Agent

Owns kennel storage, packing, audit, and hygiene.

Responsibilities:

- prevents junk ingestion;
- dedupes cached context;
- exposes audit/prune tools;
- improves prompt packing without LLM summarization dependency.

Artifacts:

- kennel migration or helper;
- audit report;
- focused tests.

## Verification department

### QA Agent

Owns functional correctness.

Responsibilities:

- writes tests from acceptance criteria;
- runs focused and full suites;
- verifies fresh-install behavior;
- catches fixture lies.

Artifacts:

- test plan;
- pytest output;
- regression notes.

### Release Engineer Agent

Owns packaging and shipping.

Responsibilities:

- validates pyproject metadata;
- checks optional extras;
- verifies install scripts;
- prepares commits/tags/PRs.

Artifacts:

- release checklist;
- install smoke;
- commit/push report.

### Observability Agent

Owns logs, audit, replay, and support bundles.

Responsibilities:

- records workflow events;
- summarizes support state;
- makes failures diagnosable;
- prevents silent broken automation.

Artifacts:

- event trail;
- audit summary;
- support bundle.

## Operations and support department

### Support Agent

Owns user/operator recovery.

Responsibilities:

- writes issue drafts;
- collects diagnostic bundles;
- explains next steps simply;
- handles Android setup failures.

Artifacts:

- support summary;
- recovery guide;
- issue draft.

### Community / Ecosystem Agent

Owns external contribution paths.

Responsibilities:

- prepares PR narratives;
- tracks upstream vs fork boundaries;
- identifies plugin opportunities;
- keeps public positioning clean.

Artifacts:

- PR description;
- roadmap note;
- contribution guide.

## Workflow states

Every mission should move through the same OS loop:

```text
intake -> plan -> assign -> build -> verify -> package -> publish -> observe -> learn
```

Each state must produce an artifact. If there is no artifact, the state did not
happen.

## Department handoff packet

Every department handoff should include:

```text
owner_agent:
mission:
constraints:
inputs:
changes_made:
tests_run:
risks:
next_action:
approval_needed:
kennel_notes:
```

This is how hundreds of roles become manageable without relying on vibes.

## Minimal first implementation

Do not create dozens of agents at once. Start with a thin command-and-control
layer and promote departments only when they have real work.

Phase 1 agents:

1. Chief Agent Officer
2. Safety Governor
3. Product Manager Agent
4. Systems Architect Agent
5. Core Runtime Agent
6. Droid Bridge Engineer Agent
7. Context Engineer Agent
8. QA Agent
9. Release Engineer Agent

Phase 2 agents:

1. UX / Droid Cockpit Agent
2. Security Architect Agent
3. Observability Agent
4. Support Agent
5. Documentation Agent
6. Community / Ecosystem Agent

## Non-negotiables

- No god-agent.
- No hidden dangerous power.
- No credential sludge in kennel.
- No transcript hoarding pretending to be memory.
- No live broker action without approval.
- No release without tests.
- No architecture without artifacts.
- No department without a clear owner, authority, and output.
