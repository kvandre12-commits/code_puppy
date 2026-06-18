# Android Agent OS Distribution Plan

Code Puppy Droid is not just a mobile code editor or a chatbot wrapper. It is the
Android-facing distribution path for Code Puppy as a local **agent OS layer**:
agent intent, scoped power, local execution, observation, audit, replay, and
coding as a first-class workflow. The Android layer model is defined in
`docs/ANDROID_AGENT_OS_LAYER.md`; the operating department model is defined in
`docs/AGENT_ORG_CHART.md`.

```text
Linux -> manages hardware/resources
Android -> manages device state and user experiences
Code Puppy -> manages project/work state
Kennel -> preserves durable project memory
```

```text
Intent -> Contract -> Code Puppy -> Droid action -> Observation -> Audit/replay
```

## Current truth

Code Puppy can run on Android today through Termux:

```text
pkg install python git
pip install code-puppy
code-puppy -i
```

The current repo already ships a Python package with console entrypoints:

```text
code-puppy
pup
```

The Droid bridge stack is healthy on the reference device: Android/Termux,
ADB, Brave/Chrome, and DroidPuppy plugins are available. This is the early
shape of a phone-native agent OS layer, not a one-off Android helper script. The
bridge grant model also exists:

```text
No direct power. Only granted power.
```

## What does not exist yet

There is not currently a traditional Android APK/AAB in this repo. A normal user
cannot yet install "Code Puppy Droid" from an APK and get the full experience
without Termux or another Python runtime layer.

## Recommended ship path

### Phase 1: Termux-backed public beta

Goal: let Android power users do what the maintainer does today.

Current beta pieces:

1. Bootstrap script: `scripts/install-code-puppy-droid.sh`
2. Droid viewer plugin: `/droid status`, `/droid open`, `/droid stop`
3. Local dashboard: `http://127.0.0.1:8765/`
4. Machine-readable status: `http://127.0.0.1:8765/status.json`
5. Live event stream: `http://127.0.0.1:8765/events.json`
6. Local bridge mutation endpoints:
   - `POST /bridge/grant`
   - `POST /bridge/revoke`
7. First-run bridge checklist:
   - browser handoff
   - optional Wireless Debugging / ADB pairing
   - `/bridge list`
   - `/bridge grant <agent> <scope>`

Install from a checkout:

```text
scripts/install-code-puppy-droid.sh
code-puppy -i
/droid open
```

This is the fastest path and keeps the core tiny.

### Phase 2: Native Android shell app

Goal: normal Android install with a friendly puppy UI.

Architecture:

```text
Android APK shell
  ├─ native landing screen / mascot / setup wizard
  ├─ WebView or Custom Tab viewer
  ├─ localhost bridge to Code Puppy backend
  └─ Android permission / intent helper screens

Code Puppy runtime
  ├─ still Python-first initially
  ├─ runs in Termux or a bundled runtime
  └─ exposes local HTTP/WebSocket control surface
```

The APK should start as a shell/launcher, not a full Python rewrite. Rewriting
Code Puppy in Kotlin would be yak shaving with a chainsaw. Bad puppy.

### Phase 3: Bundled runtime experiment

Options to investigate:

1. Termux companion install: easiest, least polished.
2. Chaquopy: Android app embeds Python, but dependency/native-wheel pain is real.
3. BeeWare/Briefcase: worth testing, but Droid bridge and subprocess support need
   proof.
4. PWA + Termux backend: surprisingly practical, but less "app store native."

## Native browser/viewer

Yes, the product should ship with its own viewer experience.

Recommended first viewer:

```text
Local web UI served by Code Puppy
opened in Brave/Chrome/Android WebView
```

Why not pure terminal? Because normal people do not wake up thinking, "I need
more prompt-toolkit in my life." Weird, but apparently true.

The first viewer is workflow-first. It exposes:

- workflow monitor as the main screen
- current golden-loop stage
- stage counts
- live workflow trail
- local `/workflow.json`
- local `/events.json`
- Droid command status
- audit event count/path

Bridge permissions are intentionally tucked under an "Advanced bridge
permissions" drawer. They matter, but they are plumbing, not the show.

The later viewer should add:

- chat/session stream
- audit/replay controls
- agent picker
- tool activity timeline with tool-call events
- background agent run controls
- workflow cards grouped by agent/task

## Mascot direction

Code Puppy should be visually distinct from enterprise helper mascots.

Direction:

```text
Code Puppy in a MegaMan-style helmet with a tiny blaster
```

Keep it playful, but avoid copying any protected character design directly. The
safe version is "retro cyber puppy / blue robot helmet / tool blaster," not a
literal MegaMan clone. Lawyers are not fun party guests.

## Product rule

Every Android/Droid/native feature must answer:

```text
What scope gates this?
Which agent can receive it?
Can it be revoked?
Is it logged?
Can it be replayed?
```

That is how Code Puppy becomes the Android agent OS layer that includes coding,
instead of a pile of very excited scripts wearing a trench coat.
