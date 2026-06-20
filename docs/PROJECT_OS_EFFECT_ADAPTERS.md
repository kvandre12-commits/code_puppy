# Project OS Effect Adapters

Effect adapters are not separate runtimes. They are replaceable effect-plane
modules plugged into the same Project OS control plane. The v0.1 milestone is
summarized in `PROJECT_OS_V0_1_RUNTIME_THEOREM.md`.

The system promise is:

```text
Authority -> Lease -> One bounded Effect -> Audit
```

The adapter promise is:

```text
noop_execution.py
browser_execution.py
android_execution.py
github_execution.py
robinhood_execution.py

all obey the same control plane.
```

## Baseline theorem

The no-op runtime proves the baseline theorem:

```text
valid AuthorityGrant
+ valid active unconsumed one-shot LeaseRecord
= exactly one bounded effect
+ consumed lease
+ audit EventRecord
```

For noop, the effect event is:

```text
noop_executed
```

Future adapters change the effect, not the theorem. Effect adapters use the
normalized audit event shape:

```text
<adapter>_effect_executed
```

For example, the browser adapter writes `browser_effect_executed` without adding
a browser-specific audit catalog rule.

## Browser adapter acceptance test

The first real browser adapter should not be judged by whether a browser opened.

It should be judged by whether the browser opened only because a valid lease
allowed exactly that one effect.

The target lifecycle is:

```text
AuthorityGrant
  -> authority-check
  -> LeaseRecord
  -> execute-browser
  -> lease consumed
  -> browser_effect_executed EventRecord
```

The positive case is:

```text
valid authority
+ valid one-shot lease for the exact browser action and URL scope
= one bounded browser effect
+ audit
```

The refusal table is sacred:

```text
missing authority  -> no lease
wrong confirm      -> no mutation
expired lease      -> no browser effect
reused lease       -> no second browser effect
revoked authority  -> no browser effect
wrong URL/scope    -> no browser effect
```

A browser adapter is therefore not special. It is the first external effect that
proves the control plane survives contact with the outside world.

## Boundary test ladder

Treat adapters as increasingly difficult boundary tests:

```text
Browser   -> external effect boundary
Android   -> device boundary
me@sams   -> application + identity + agent + workflow boundary
GitHub    -> persistent mutation boundary
Robinhood -> financial-risk boundary
```

The first effect for a new boundary should be boring: launch an approved screen,
read an approved view, retrieve an approved status, then consume the lease and
audit. Do not begin with complex workflows.

For me@sams specifically, the first experiment should cross the identity-bearing
application boundary without mutation:

```text
Authority -> Lease -> Approved me@sams View -> Audit
```

Do not begin with task submission, workflow mutation, agent orchestration,
background recovery, or message sending. If me@sams needs special authority or a
special trust path, treat that as possible contract evidence before patching.

If the approved-view test reveals a need to translate Project OS authority into
an external application permission/session model, record that as possible
capability-translation evidence. Do not hide it inside me@sams-only code.

Pre-register outcomes before implementing: direct pass means the theorem gains
credibility; capability translation means the theorem may need a new explicit
concept; me@sams-only special permissions, validators, leases, or trust paths
mean the experiment has been compromised.

Protect the experiment, not the theorem. Learn something true and do not hide
it. If a boundary requires special Authority, Lease, Validator, or Audit
behavior, classify that as possible contract evidence before adding exceptions.
Theorem changed is not the same as theorem failed.

Classify action type before implementing:

```text
approved view/read/status      -> read boundary
commit/comment/post/edit/send  -> persistent mutation boundary
financial/regulated action     -> high-risk boundary
```

For Reddit or LinkedIn style adapters, treat read-only approved views as the
first identity/reputation experiment. Posting, commenting, messaging,
endorsements, or profile edits are persistent public mutations and need their
own later mutation-boundary experiment.

If a boundary presents biometric/MFA/operator approval, do not treat that as an
adapter bug by default and do not bypass it. Pause at an explicit human approval
checkpoint, let the operator satisfy the external challenge, then continue only
inside the lease/scope and audit the bounded effect. If this pattern repeats
across adapters, record it as possible contract evidence instead of hiding it in
one adapter.

Keep effect execution separate from effect observation. If an effect launches but
ADB/UI/CDP inspection fails afterward, classify the observer failure separately.
Do not mark the effect failed unless execution itself failed; do not mark the
experiment proven unless runtime audit evidence exists.

Do not promote one-off pressure into a theorem concept. Capability Translation,
Human Approval Checkpoint, Effect Observation Boundary, Location / Proximity
Precondition, and Work-State / Duty-State Precondition are watch-list items until
multiple unrelated boundaries demand them.

Do not collapse every gate into authentication. Identity gates prove who is
acting; duty-state gates prove the context/state under which they are acting.
Adapters must not perform a state-changing action, such as employment clock-in,
merely to unlock broader downstream capabilities.

## Capability OS milestone ladder

Project OS has moved beyond a generic agent framework. It is becoming a governed
capability operating system for agents.

The next technical milestone should prove a staged capability ladder:

```text
AuthorityGrant
  -> Authority Registry Validation
      -> Lease Issue
          -> Execute No-op
              -> Execute Memory Recall
                  -> Execute Android Intent
                      -> Execute Browser Action
                          -> Execute Tool Call
```

Each stage should prove the same thing with a stronger effect:

```text
governance controls the effect
without skipping Authority
without skipping validation
without skipping Lease issue
without skipping Lease consumption
without skipping Audit
```

This is the Project OS equivalent of process permissions and capability security,
but for AI agents instead of human users. The lease is the revocable execution
permission. Lease consumption is the one-shot capability boundary. The audit
trail is the operating-system record of what happened.

The test is not whether an agent can do the thing. The test is whether the agent
can do the thing only through the governed path.

No effect may occur unless:

```text
1. Authority is registered.
2. Authority validates.
3. Lease is issued.
4. Lease is unexpired.
5. Lease is unconsumed.
6. Execution succeeds.
7. Audit event is recorded.
```

Different adapters may touch different systems, but they do not get different
governments. Memory recall, Android intents, browser actions, and tool calls are
effect adapters behind the same authority substrate.

## Memory as an effect domain

Memory is not privileged runtime magic. It is an effect domain.

Traditional agents often treat memory as a special subsystem:

```text
Memory
  -> Reasoning
      -> Action
```

Project OS treats memory access as a governed capability:

```text
Authority
  -> Lease
      -> Effect Adapter
          -> memory.recall / memory.promote / memory.distill
              -> Audit
```

Read and mutation memory effects must not be collapsed:

```text
memory.recall
  reads existing knowledge

memory.promote
  elevates information to durable status

memory.distill
  creates durable knowledge derived from existing records
```

`memory.recall` is a read effect. `memory.promote`, `memory.distill`, and future
`memory.archive` are durable mutations and should require stronger controls.
SQLite, FTS5, BM25 ranking, vector indexes, or hybrid retrieval are storage and
retrieval implementation details. The Project OS law is unchanged:

```text
Who requested?
What authority existed?
What lease authorized it?
What effect occurred?
What audit evidence remains?
```

Milestone split:

```text
Milestone 1A: Governed Memory Recall
  AuthorityGrant -> Lease -> memory.recall -> Audit

Milestone 1B: Governed Memory Mutation
  AuthorityGrant -> Lease -> memory.promote/distill/archive -> Audit
```

## Governed memory mutation contract

Memory mutation is a different security class from recall. Recall reads existing
institutional knowledge. Promote, distill, archive, revise, or delete changes
what future agents may treat as durable truth.

A memory mutation adapter must not merely prove that a lease existed. It must
produce enough evidence to reconstruct what changed and why.

Required mutation audit fields:

```text
requesting_identity
requesting_agent
lease_id
authority_grant_id or authority evidence reference
mutation_type
source_evidence
mutation_reason
before_object
proposed_after_object
resulting_memory_id
resulting_memory_type
project_id or project wing
objective_id or objective label
work_item_id or work item label, when applicable
precedent_id, when applicable
remedy_id, when applicable
```

For `memory.promote`, source evidence should point to the quarantine drawer,
conversation excerpt, event, artifact, or operator statement being promoted. For
`memory.distill`, source evidence should list the input drawers or artifacts that
were compressed into the durable record. For `memory.archive`, `before_object`
must identify what was archived and `mutation_reason` must explain why it should
stop guiding default recall.

The minimum mutation invariant is:

```text
No durable memory object may be created, revised, archived, or deleted unless:
1. Authority is registered for the exact mutation class.
2. Authority validates.
3. A mutation lease is issued.
4. The lease is unexpired.
5. The lease is unconsumed.
6. Source evidence is recorded.
7. Mutation reason is recorded.
8. Before/after or input/output object evidence is recorded.
9. The memory backend reports the resulting memory id or refusal reason.
10. The lease is consumed once.
11. A mutation audit event is recorded.
```

The mutation must be atomic:

```text
mutation succeeds completely
  or
mutation does not occur
```

There must be no half-written institutional memory. If the kennel mutation
succeeds but Project OS cannot consume the lease and write audit evidence, the
mutation is not acceptable. If Project OS can consume the lease but the kennel
cannot report the resulting memory object, the mutation is not acceptable.
Design implementation so Project OS state and kennel state either advance
together or both remain unchanged.

This is a two-domain transaction:

```text
Governance State
  Authority
  Lease
  Audit
  Precedent
  Remedy

Knowledge State
  Memory Objects
  FTS Records
  Distillations
  Promotions
  Archives
```

The implementation proof is not:

```text
Can memory be mutated?
```

The implementation proof is:

```text
Can a durable knowledge mutation be governed, audited, and atomic?
```

Target transaction shape:

```text
Authority
  -> Lease
      -> Mutation Request
          -> BEGIN
              -> Write Memory
              -> Write Audit
              -> Consume Lease
          -> COMMIT
```

Failure shape:

```text
Authority
  -> Lease
      -> Mutation Request
          -> BEGIN
              -> Write Memory
              -> Audit Failure
          -> ROLLBACK
```

After rollback:

```text
memory unchanged
lease unconsumed
audit absent
```

Required proof matrix before claiming Governed Memory Mutation Proven:

```text
valid authority + valid lease + valid evidence -> mutation succeeds
missing authority                             -> refused, no mutation
missing evidence                              -> refused, no mutation
expired lease                                 -> refused, no mutation
consumed lease                                -> refused, no mutation
audit failure                                 -> rollback, no mutation
memory write failure                          -> rollback, no lease consumption
```

Memory effect classes should reflect risk:

```text
Class 1: Recall
  memory.recall
  read-only
  low consequence

Class 2: Knowledge creation or modification
  memory.promote
  memory.distill
  medium consequence
  requires source evidence and mutation reason

Class 3: Knowledge removal or correction
  memory.archive
  memory.delete
  memory.remedy
  high consequence
  requires additional authority or precedent/remedy evidence
```

A mutation adapter must not quietly rewrite institutional knowledge while
technically following the generic effect rules. If the adapter cannot produce
source evidence, mutation reason, and before/after or input/output object
evidence, it must refuse the mutation and leave both Project OS state and kennel
state unchanged.

## Runtime proof versus deployment proof

Project OS is not the Android app.

Current distinction:

```text
Project OS
  status: proven Termux-loadable governed runtime
  owns: governance, authority grants, leases, audit, effect adapter doctrine

SharpEdge-Android
  status: native Android source scaffold
  owns: APK/presentation shell and future native operator UI

SharpEdge APK
  status: not built yet
  owns: deployment proof once a repeatable build exists
```

The stack evolves inward-to-outward:

```text
Governance Layer
  -> Capability Security Layer
      -> Runtime Layer
          -> Effect Adapter Layer
              -> Android Packaging Layer
```

From the Project OS perspective, the important proof already achieved is:

```text
authority-check PASS
  -> lease issued
      -> lease consumed
          -> reuse denied
              -> audit written
```

That is a security model proof. An APK build is a deployment proof. Do not
confuse them.

Milestone map:

```text
Milestone 0: Governed Runtime Proven
  status: COMPLETE

Milestone 1: Effect Adapter Proven
  examples: No-op, Android Intent, Browser Action, Tool Call
  status: IN PROGRESS

Milestone 2: Android Packaging Proven
  examples: GitHub Actions, Gradle build, debug APK artifact
  status: NOT STARTED

Milestone 3: Native Operator Shell
  examples: APK installs, connects to Project OS, displays audit trail,
            displays leases, displays runs
  status: NOT STARTED
```

The clean APK path is to let GitHub Actions build the native shell while Project
OS remains the governed runtime substrate:

```text
SharpEdge-Android
  -> GitHub Actions
      -> debug.apk artifact
          -> install on phone
              -> presentation layer over Project OS runtime
```

Do not embed all governance/runtime logic directly into the Android app just to
make an APK exist. The APK is the shell, not the theorem.

## Adapter implementation rule

An adapter may:

```text
validate its effect-specific scope
perform one bounded external effect
consume the lease once
write one effect-specific audit event
```

An adapter must not:

```text
create authority
issue leases
repair missing grants
expand URL/action/capability scope
reuse consumed leases
hide external effects without EventRecords
```

If an adapter needs broader authority, it stops and requests authority. It does
not reinterpret the lease. Runtime obedience beats runtime creativity here.
