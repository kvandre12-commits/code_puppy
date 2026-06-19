# Android Agent OS Layer

Android already behaves like a layered operating system full of service agents,
capability grants, local indexes, background caches, and predictive services.
Code Puppy does not replace Android. It adds the missing project-reasoning layer
above Android.

```text
Human
  -> Agent OS
  -> Android system services
  -> Linux kernel
```

A sharper responsibility split:

```text
Linux -> manages hardware/resources
Android -> manages device state and user experiences
Code Puppy -> manages project/work state
Kennel -> preserves durable project memory
```

Do not fight lower layers. Use them.

## Layer 1: Linux kernel

A Samsung phone is running Linux underneath Android.

Kernel responsibilities:

```text
memory
processes
filesystems
network
security
scheduling
drivers
```

Hardware surfaces:

```text
CPU
RAM
storage
Bluetooth
WiFi
USB
camera
sensors
```

This is the actual kernel. Code Puppy should not pretend to be this layer.

## Layer 2: Android system services

Android runs always-on system services. They are not AI agents, but they are
service agents in the operating-system sense.

Examples:

```text
ActivityManager
PackageManager
WindowManager
NotificationManager
LocationManager
MediaManager
SensorManager
PowerManager
```

Anthropomorphized:

```text
System UI = receptionist
Activity Manager = traffic controller
Package Manager = HR department
Permission Manager = legal department
Power Manager = finance department
Notification Manager = communications department
Google Play Services = operations department
```

This is why Android already feels like a company. It has departments, policies,
queues, managers, and background work.

## Layer 3: Android permission system

Android already has capability grants:

```text
camera
location
microphone
notifications
contacts
SMS
storage
```

Each app is roughly in one of these states:

```text
granted
denied
ask every time
```

That maps directly onto the Code Puppy power model:

```text
Agent
  -> Capability
  -> Approval
```

Code Puppy should mirror this pattern for agents. Android permissions protect
device resources. Code Puppy grants protect agent capabilities.

## Do not rebuild Android

Android should own device capabilities:

```text
camera
notifications
contacts
calendar
location
Bluetooth
network
runtime permissions
```

Code Puppy should use these through controlled bridges. It should not rebuild
them.

Code Puppy should own project/work capabilities:

```text
projects
agents
decisions
artifacts
workflows
provider grants
audit history
repo state
```

Android has no native concept of:

```text
SharpEdge
DroidPuppy
Robinhood Bridge
Agent Org Chart
Trade Gate research
```

Those are project objects. That is Code Puppy territory.

## Layer 4: Android local intelligence

Modern Android keeps local knowledge stores so the phone does not re-scan the
world from scratch every time.

Examples:

```text
UsageStats
AppSearch
Launcher index
Media index
Notification history
Predictive services
```

Android learns:

```text
which apps you use
when you use them
who you call
which notifications matter
which Bluetooth devices matter
```

This is already a local context economy.

## Layer 5: Android's existing kennels

Android and Google services maintain local context caches:

```text
recent apps
notification history
search index
photos metadata
assistant context
on-device ML state
```

The pattern is:

```text
world
  -> index
  -> cache
  -> prediction
```

That is kennel-shaped. The phone does not re-scan everything every time. It
builds local context caches and consults them.

## Layer 6: on-device AI

New Android devices are adding on-device AI features:

```text
Gemini Nano
Samsung Galaxy AI
Live Translate
Circle to Search
Call Assist
note summarization
```

The pattern is becoming:

```text
phone call
  -> transcript
  -> summary
  -> stored context
```

instead of:

```text
store entire transcript forever
```

This validates the kennel direction: summarize or select durable context, avoid
hoarding raw transcript sludge.

## What Android does not have

Android has:

```text
memory
permissions
services
apps
background tasks
indexes
local caches
```

Android does not naturally have:

```text
durable reasoning
durable decisions
durable project memory
workflow commitments
agent department handoffs
operator approval policies
```

Android may know:

```text
you opened GitHub yesterday
```

But it does not know:

```text
we decided broker orders require approval
SharpEdge owns the Android viewer
Code Puppy is the agent OS layer
Droid bridge tools require scoped grants
kennel transcript sludge should be pruned
```

That is the missing layer.

## Code Puppy's missing-layer responsibility

Code Puppy provides what Android does not:

```text
projects
goals
decisions
workflows
agent hierarchy
grant policies
operator approvals
context economy
```

Linux remembers resources. Android remembers device state. Code Puppy remembers
project state. The kennel preserves durable project memory.

```text
Linux -> CPU, memory, storage, network
Android -> apps, notifications, locations, Bluetooth, permissions
Code Puppy -> projects, agents, artifacts, workflows, repo state
Kennel -> principles, facts, decisions, artifacts, relationships, history
```

Examples of durable project context:

```text
SharpEdge
Code Puppy
Robinhood Bridge
DroidPuppy
Agent Org Chart
Grant Policies
Kennel Hygiene
Android Distribution Plan
```

This is closer to a knowledge operating system than a mobile operating system.
The kennel is the Institutional Knowledge Layer between projects and agents.

## Target stack

```text
Human operator
  -> Code Puppy Agent OS
      -> projects
      -> institutional knowledge
      -> agents
      -> bridge grants
      -> workflow monitor
      -> audit/replay
  -> Android system services
      -> activities
      -> packages
      -> windows
      -> notifications
      -> sensors
      -> power
  -> Linux kernel
      -> processes
      -> memory
      -> filesystems
      -> network
      -> drivers
```

## Design consequences

### 1. Mirror Android permissions

Agent power should look like Android runtime permissions:

```text
scope requested
operator grants
agent receives tools
use is logged
scope can be revoked
state can be replayed
```

### 2. Treat kennel as typed durable project memory

The kennel is not AI memory, chat history, embeddings, or app state. Its role is
the durable project memory layer: distilled project knowledge that survives after
the conversation ends. Decisions are the highest-value drawer type, but they are
not the only type. The distillation contract lives in `docs/KENNEL_DISTILLATION.md`.

```text
Kennel
  -> Principles
  -> Facts
  -> Decisions
  -> Artifacts
  -> Relationships
  -> History
```

Examples:

```text
Principle: No direct power. Only granted power.
Fact: Android owns runtime permissions.
Decision: No god-agent.
Artifact: docs/ANDROID_AGENT_OS_LAYER.md
Relationship: DroidPuppy depends on Android.
History: Commit e27359c clarified the memory layer model.
```

The important question is not whether 195k tokens were saved. The important
question is whether those tokens produced durable project knowledge:

```text
principles
discoveries
designs
commits
tests
policies
relationships
```

That is worth carrying forward. Raw transcript bulk usually is not.

```text
conversation
  -> quarantine
  -> typed durable memory
  -> future work
```

Raw transcript can enter the kennel only as temporary quarantine:

```text
quarantine transcript
  -> distill typed drawers
  -> promote durable drawers
  -> prune transcript crumbs
```

It should store durable project knowledge, not every transcript crumb.

### 3. Separate Android observation from agent reasoning

Android can expose:

```text
current app
installed packages
notifications
screen state
logs
browser state
```

Code Puppy should decide:

```text
what matters
what changed
what policy applies
which agent owns next action
whether approval is required
```

### 4. Make departments explicit

Android has service departments. Code Puppy needs agent departments.

```text
Permission Manager -> Safety Governor
UsageStats/AppSearch -> Context Governor
ActivityManager -> Workflow Orchestrator
NotificationManager -> Observability Agent
PackageManager -> Runtime/Plugin Registry
```

The org chart is not decoration. It is how the agent OS scales beyond one
assistant.

## North star

Code Puppy becomes the missing project-context and agent-governance layer on top
of Android:

```text
Android = device operating system
Code Puppy = project and agent operating system
```

That is why DroidPuppy, Phone Companion, bridge grants, workflow monitor, and the
kennel keep converging. They are not separate ideas. They are pieces of the same
layer.
