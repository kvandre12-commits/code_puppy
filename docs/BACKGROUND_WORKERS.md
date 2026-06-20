# Background Workers and Guarded Context Windows

## Why this matters

A foreground chat model is the wrong place to run every recurring or triggered
job forever.

If a user wants things like:

- morning briefs
- bill-change alerts
- syllabus summaries
- inbox triage
- reminder digests

then the right architecture is **delegation**, not "keep the whole model awake
in RAM and pray Android is feeling generous today."

## Core split

### Foreground model

Owns:

- understanding user intent
- turning vague requests into strict job definitions
- explaining policy and tradeoffs
- handling escalations
- synthesizing results across jobs

### Background worker

Owns:

- one narrow trigger or schedule
- one bounded source scope
- one bounded extraction/summarization task
- one structured result payload

If a background worker starts acting like a general assistant, the design is
rotting.

## Guarded context windows

The key safety rule is:

> background workers should ingest the minimum sufficient text slice, not the
> user's whole upstream corpus.

A proper worker contract should name:

- the trigger
- the source scope
- the input filter
- the extraction goal
- the output schema
- the side-effect class
- the escalation rule
- the retention policy

That is why this branch includes generic planning tools for background-worker
contracts rather than pretending the runtime is already universal.

## Android reality check

Android background execution has real limits:

- processes are killed
- battery policies are strict
- arbitrary apps do not run forever just because they want to

So a serious Android path usually relies on platform-native execution surfaces,
for example:

- scheduled work / job scheduling
- foreground services for explicit ongoing tasks
- notification listeners or share/intake paths
- companion-app components where Termux alone is insufficient

This is exactly why the engine/runtime split matters.

## What lands in core vs overlay

### Upstream Code Puppy

Should own the generic seams:

- typed worker contracts
- guarded context-window planning
- tool surfaces for defining and reviewing those contracts
- graceful handoff boundaries between foreground reasoning and later execution

### Product/overlay layers

Should own the runtime details:

- Android-specific scheduling
- notification bridges
- inbox/file observers
- dashboard surfaces
- approval UX
- device-specific background execution tactics

## Included tools

This branch adds a small builtin plugin that exposes:

- `background_worker_blueprint`
- `background_worker_examples`

These tools do **not** claim to execute background jobs. They define the
contract that a runtime can later honor.

That is the honest, reviewable slice to upstream first.
