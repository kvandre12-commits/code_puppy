# Android Professional Onboarding Spec

## Goal

Deliver a first-run Android onboarding path that feels professional to a new
operator, not merely survivable to a technical Termux user.

The onboarding experience should make one promise and keep it:

> A motivated Android user can go from fresh Termux install to verified
> Code Puppy + DroidPuppy readiness through one guided flow with clear state,
> clear failures, and clear next actions.

This spec treats the **repo/runtime as mostly ready** and the **onboarding layer
as the weak point**.

---

## Current honest state

Today, a technical user can likely succeed by combining:

- `scripts/install_termux.sh`
- lean bootstrap planning
- DroidPuppy overlay install
- Android package setup (`android-tools`, etc.)
- Wireless Debugging pairing
- browser CDP probing / verification

That is good engineering surface area.
It is not yet a professional first-run ramp because those steps are still spread
across multiple mental models and multiple operator-owned transitions.

### Current fragmentation

The operator must still reason across separate concerns:

1. Code Puppy lean install
2. DroidPuppy overlay install
3. required Termux packages
4. Android `adb` / `android-tools` presence
5. Wireless Debugging pairing/connect flow
6. browser CDP/socket readiness
7. final verification of what works right now

A professional onboarding path should collapse those into **one guided system**.

---

## Product principles

### 1. One journey, many checkpoints

The user should not have to discover the sequence themselves.
The onboarding flow owns the order.

### 2. Detect before instructing

Never dump a giant README and hope for the best.
Each stage should inspect current state and choose the next best action.

### 3. Every failure must degrade into a next action

No dead-end “something failed lol” behavior.
Each failure should produce:

- what was attempted
- what was observed
- why it matters
- the exact next step

### 4. Separate required from optional capability

The user should leave knowing which of these are true:

- Code Puppy core is installed
- DroidPuppy overlay is installed
- Android launch/settings routing works
- ADB is installed but not paired
- ADB is paired but browser CDP is not ready
- browser CDP is ready

This prevents false binary thinking like “Android support works/doesn’t work.”

### 5. Preserve evidence and trust

The onboarding flow should feel trustworthy.
That means:

- explicit state transitions
- idempotent steps where possible
- concise summaries
- optional support bundle capture when things fail

---

## Target experience

### Entry point

Provide one primary onboarding command for Android users.

Candidate shapes:

```bash
code-puppy-android-onboard
```

or

```bash
code-puppy-bootstrap android-first-run
```

or a script entrypoint such as:

```bash
scripts/onboard_android.sh
```

The exact name matters less than the behavior:
**one obvious command** should own the first-run experience.

### Operator experience

The flow should feel like a staged installer/checkpoint wizard:

1. **Welcome / scope**
   - explain what will be set up
   - distinguish required vs optional capabilities
2. **Core install**
   - Termux baseline
   - `uv`
   - lean Code Puppy install
3. **Overlay install**
   - DroidPuppy plugin install / verify
4. **Android tooling**
   - detect/install `adb` / `android-tools`
5. **Wireless Debugging guidance**
   - open the right Android settings / explain what to copy
6. **ADB pair/connect**
   - generate or run the correct pair/connect commands
7. **Browser readiness**
   - detect Brave/Chrome
   - probe CDP sockets
8. **Final readiness report**
   - core ready / overlay ready / adb ready / browser ready
   - next recommended moves

---

## Capability ladder

The onboarding ramp should publish a ladder, not a blob.

### Level 0 — Platform recognized
- running on Android/Termux
- baseline commands available

### Level 1 — Core Code Puppy ready
- `code-puppy --help` passes
- lean profile installed

### Level 2 — DroidPuppy overlay ready
- plugin overlay installed
- Android-native helper tools visible

### Level 3 — Local Android utilities ready
- settings routing works
- app launch/open helpers work
- optional notification capability assessed

### Level 4 — ADB/Wireless Debugging ready
- `adb` installed
- pairing/connect path understood
- device connected

### Level 5 — Browser/CDP ready
- browser detected
- CDP socket reachable
- page target listing works

### Level 6 — Operationally verified
- a harmless real command succeeds end-to-end
- e.g. open browser, list targets, read example page

This ladder turns onboarding into a measurable product surface.

---

## Proposed architecture

## Phase A — unify existing primitives instead of rewriting them

Build a new orchestration layer that reuses existing pieces:

- `scripts/install_termux.sh`
- `code_puppy.bootstrap_profiles`
- `code_puppy.bootstrap_wizard`
- `android_setup_doctor`
- `android_setup_next_steps`
- `android_cdp_doctor`
- `android_adb_wireless_helper`
- `android_cdp_probe`
- browser doctor/probe utilities

The new onboarding layer should mostly orchestrate and summarize.
It should not duplicate low-level logic unless necessary.

## Phase B — expose one operator-facing onboarding surface

This layer should:

- inspect state
- choose the next stage
- execute or preview actions
- record outcomes
- print a final capability report

## Phase C — add support-grade artifacts

When onboarding fails, offer to produce:

- support bundle
- screenshot if useful
- concise issue draft / summary

Professional onboarding includes professional failure handling.

---

## UX requirements

### Required

- dry-run mode
- noninteractive / auto-yes mode
- explicit stage headers
- success/failure summary at the end
- idempotent reruns
- exact commands shown before execution
- clear distinction between:
  - installed
  - skipped
  - unavailable
  - blocked by operator step

### Nice to have

- progress bar / stage indicator
- copy-paste snippets for Android settings steps
- support bundle handoff on failure
- “resume from here” checkpointing

---

## Recommended flow design

### Stage 1 — Core install

Responsibility:
- own the current `install_termux.sh` behavior
- verify Code Puppy core install

Output:
- `core_ready: yes/no`
- installed version
- Python / uv / package snapshot

### Stage 2 — Overlay attach

Responsibility:
- install or verify DroidPuppy overlay
- ensure Android plugins are visible

Output:
- `overlay_ready: yes/no`
- plugin location and visibility summary

### Stage 3 — Local Android capability baseline

Responsibility:
- run `android_setup_doctor`
- assess what works without ADB

Output:
- launch/settings/browser-open capability summary

### Stage 4 — ADB readiness

Responsibility:
- detect whether `adb` exists
- install or instruct for `android-tools`
- guide Wireless Debugging pairing

Output:
- `adb_installed`
- `adb_connected`
- pairing/connect instructions or confirmation

### Stage 5 — Browser CDP readiness

Responsibility:
- detect supported browser presence
- probe DevTools/CDP socket
- verify target discovery

Output:
- `browser_detected`
- `cdp_ready`
- target count / browser identity

### Stage 6 — Final verification journey

Responsibility:
- run one or two harmless proof actions

Candidate proof actions:
- open a test URL
- read page text
- list browser targets

Output:
- operator-facing “you are ready for X, blocked for Y” report

---

## Reporting contract

At the end, print a structured summary like:

```text
Android Onboarding Summary
-------------------------
Core Code Puppy: READY
DroidPuppy overlay: READY
Android local utilities: READY
ADB / Wireless Debugging: BLOCKED (pairing info not yet supplied)
Browser CDP: BLOCKED (ADB not connected)

Next best action:
1. Open Wireless Debugging settings
2. Enter pairing IP/port/code
3. Re-run onboarding from Stage 4
```

This is much more professional than “stuff happened, good luck.”

---

## Implementation plan

### Milestone 1 — professional shell path

Extend the existing script path into a broader Android onboarding script that:

- installs core Code Puppy lean
- optionally installs DroidPuppy overlay
- detects `adb`
- points to the next ADB/CDP step
- prints a structured readiness summary

This is the fastest route to a meaningful upgrade.

### Milestone 2 — integrated Python wizard

Create a Python onboarding orchestrator that reuses the script/doctor logic and
supports:

- interactive progression
- dry-run
- rerun/resume
- richer summaries

### Milestone 3 — issue/support polish

Add support-grade failure capture:

- support bundle offer
- issue draft generation
- operator-friendly remediation text

---

## Success criteria

The onboarding ramp is professional when all of these are true:

1. A new operator can identify **one obvious starting command**.
2. The command can move them from zero to at least **core-ready** without doc
   spelunking.
3. Optional Android/browser/ADB setup is presented as an ordered journey, not a
   bag of side quests.
4. Failures produce exact next steps instead of vague advice.
5. The end state is summarized as explicit capability readiness.

---

## Non-goals

This onboarding spec does **not** require:

- hiding all Android complexity
- making Wireless Debugging magically automatic
- collapsing every capability into one binary success flag

Some operator-driven Android steps will remain real.
The goal is not to erase reality.
The goal is to make reality feel organized, trustworthy, and supportable.

---

## Recommended next build step

Implement **Milestone 1** first:

> evolve the current Termux installer into a broader Android onboarding command
> that owns core install, optional overlay attach, `adb` detection, and a final
> staged readiness summary.

That gives the biggest professionalism jump with the least architectural thrash.
