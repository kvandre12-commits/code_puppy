# Evidence Distillation Backlog

The next bottleneck is **distillation**, not ontology growth.

The workspace already contains multiple under-distilled evidence streams.
This backlog exists to answer one question:

> What lessons have we already paid for, but not yet preserved as durable doctrine?

## Current posture

- Decision objects exist
- Active doctrine exists
- Doctrine consultation exists
- Doctrine adaptation proof exists
- Doctrine receipt logging exists

So the next move is not new truth-object families.
The next move is turning repeated evidence into durable decisions.

---

## 1. Android Survival

**Status:** audit
**Priority:** highest

### Candidate decisions
- Desktop-only dependencies must degrade gracefully.
- Bootstrap paths must assume lean installs.
- Browser tooling must survive missing Playwright/CDP.
- Android/Termux support is a first-class execution environment, not a weird afterthought.

### Evidence
- branches:
  - `android-graceful-deps`
  - `android-optional-playwright`
  - `playwright-goblin-fix`
  - `termux-bootstrap`
  - `optional-deps-sweep`
- commits/lines of work:
  - optional browser deps
  - optional provider deps
  - lean bootstrap planner
  - native Android bootstrap flow
- artifacts/logs:
  - `cp-depsurgery-*`
  - `cp-clean-audit-*`
  - `cp496-proof-*`
  - PR 483 / 494 / 496 evidence in `outputs/`

### Distillation questions
- Which Android breakages repeated most often?
- Which dependencies failed often enough to become doctrine?
- Which “fixes” were really just desktop assumptions wearing a fake mustache?

---

## 2. Authority / Governance

**Status:** audit
**Priority:** high

### Candidate decisions
- Authority validation must happen before lease issuance.
- Runtime anomalies trigger containment, not polite disappointment.
- Execution surfaces require narrow, inspectable constraints.
- Audit contract validity is operational, not cosmetic.

### Evidence
- `code_puppy/plugins/authority_gateway/`
- `docs/AGENT_STACK_GOVERNANCE.md`
- `.code_puppy/agents/governance-orchestrator.json`
- runtime tests + audit-path tests
- Project OS / authority / lease history in git
- cross-repo ledger entries in `docs/CROSS_REPO_WORK_LEDGER.md`

### Distillation questions
- Which authority rules are truly foundational vs implementation detail?
- Which failures forced containment doctrine into existence?
- Which constraints actually mattered in live work?

---

## 3. SharpEdge Doctrine

**Status:** audit
**Priority:** high

### Candidate decisions
- Trade gate must be checked before entry.
- Reconciliation must happen before confidence claims.
- Data integrity comes before signal trust.
- Model outputs are advisory until validated against real outcomes.

### Evidence
- repo: `/data/data/com.termux/files/home/SharpEdge-System`
- Golden Loop proofs
- deterministic trade gate scoring
- cockpit/dashboard chain
- OOS validation work
- reconciliation / scoreboard work
- regime / gamma / feature validation history

### Distillation questions
- Which trade filters survived repeated validation?
- Which dashboards are explanation layers vs actual decision layers?
- What truths were expensive enough to deserve agent-visible doctrine?

---

## 4. Failure Doctrine

**Status:** audit
**Priority:** high

### Candidate decisions
- Repeated failures deserve doctrine faster than repeated successes.
- Environment breakage is evidence.
- Installability is a first-class requirement.
- “Works on desktop” is not evidence of portability.

### Evidence
- `cp-clean-audit-*`
- `cp-depsurgery-*`
- `cp-fulltest.log`
- `code_puppy_pr483*`
- `code_puppy_pr494_fix/`
- `code_puppy_upstream_pr496_*`
- browser / CDP / Android breakage logs across scratch clones

### Distillation questions
- Which failures repeated across branches, clones, and fresh envs?
- Which errors were expensive enough to justify permanent warnings?
- Which failures already have receipts but no decisions?

---

## 5. Workspace / Catalog Evidence

**Status:** audit
**Priority:** medium

### Candidate decisions
- Workspace artifacts should be treated as evidence streams until promoted into source.
- Repo catalogs are navigation and audit infrastructure, not just convenience output.
- Distillation should happen across repos, not only inside the current checkout.

### Evidence
- `code_puppy/plugins/repository_catalog/`
- `outputs/repository_catalog.json`
- `outputs/workspace_catalog.json`
- sibling repos under `/data/data/com.termux/files/home/`
- docs:
  - `docs/CROSS_REPO_WORK_LEDGER.md`
  - `docs/REPO_INVENTORY.md`

### Distillation questions
- Which repos share the same doctrine family?
- Which outputs are recurring evidence and which are disposable noise?
- What cross-repo truths should future agents know before touching code?

---

## Recommended next distillation pass

Start with **Android Survival**.

Why:
- richest scar tissue
- freshest evidence
- repeated across branches, PRs, logs, and fresh-environment proofs
- most likely to yield 3-5 durable decisions quickly

## Suggested next step

Distill **3-5 durable decisions** from Android Survival only.

Do **not** add new ontology layers first.
Use the existing pipeline instead:

**Evidence -> Decision -> Doctrine -> Challenge -> Receipt**

## Stop signs

Pause ontology growth unless receipts show a real bottleneck.
Avoid building:
- fact engines
- claim engines
- scoring engines
- constraint taxonomies

until this backlog produces more real doctrine receipts.
