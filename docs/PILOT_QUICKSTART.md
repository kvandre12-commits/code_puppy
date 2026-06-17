# Pilot Quickstart

_Last updated: 2026-06-17_

## The first thing to memorize

You are **the pilot / operator / conductor**.

You are **not**:
- the broker
- the adapter
- the orchestra engine
- the Android tool layer

Your job is to:
1. decide the goal you want
2. confirm the system understood it
3. inspect state and outcomes
4. approve irreversible actions when required
5. deny or abort unsafe work

## The stack in plain English

### 1. SharpEdge decides **WHAT**
This is the intent layer.
Example:
- "add this option to the watchlist"
- "open the cockpit"
- "prepare this workflow"

### 2. Orchestra decides **HOW TO COORDINATE**
This is the coordinator.
It decomposes work, routes tasks, tracks state, and reports results.

### 3. DroidPuppy / adapters decide **HOW TO EXECUTE**
This is the bridge to the real world.
Examples:
- launch Brave
- talk to Android
- talk to a broker adapter
- update a watchlist

### 4. Capabilities provide **WITH WHAT**
These are the tools and services.
They should be dumb, swappable, and observable.

## The authority rule

If something can move money or cause an irreversible side effect, the machine is
not the boss. **You are.**

Important rule from the operator layer:

> `approval_decision` is the only authoritative permission object.

That means:
- a plan is not permission
- a note is not permission
- a workflow state is not permission
- a recommendation is not permission

Only explicit approval grants authority.

## Your operating loop as pilot

### Before execution
Ask:
- What am I trying to make true?
- Is this a read, an idempotent action, or an irreversible action?
- What layer should own this?
- What would success look like?

### During execution
Watch for:
- accepted intent
- task decomposition
- adapter selection
- progress observations
- approval gates
- final result

### After execution
Confirm:
- what changed
- whether result status is honest
- whether anything is pending approval
- whether artifacts or logs were produced

## The side-effect ladder

This matters a lot.

- `read` — safe to retry
- `idempotent` — safe-ish to repeat, same result
- `nonidempotent` — can change outcome if repeated
- `irreversible` — do not auto-retry, human authority matters

Pilot rule:
- be relaxed with reads
- be careful with writes
- be strict with irreversible actions

## The safest training progression

### Stage 1 — observe only
Learn the observation spine without touching the device.

Run:

```bash
cd DroidPuppy/orchestra
python3 run_demo.py
```

What you learn:
- intent
- decomposition
- task execution
- result reporting
- resume safety

### Stage 2 — real device, low risk
Trigger a visible phone action.

```bash
cd DroidPuppy/orchestra
python3 run_device_demo.py
```

What you learn:
- adapter-based execution
- real-world side effects
- observation flow on a device action

### Stage 3 — approval gate
See the system suspend instead of doing something irreversible.

```bash
cd DroidPuppy/orchestra
python3 run_approval_demo.py
```

What you learn:
- awaiting approval is a feature, not a failure
- approval and denial are first-class control actions
- irreversible work must not sneak around you

### Stage 4 — multi-step pipeline
Run the DAG demo.

```bash
cd DroidPuppy/orchestra
python3 run_pipeline_demo.py
```

What you learn:
- multiple adapters
- handoffs
- sequencing
- approval at the end of a pipeline

## How to think when something feels weird

Use this triage order:

1. **Did the intent say the right WHAT?**
2. **Did the orchestra decompose it correctly?**
3. **Did the right adapter get selected?**
4. **Did a contract or handoff fail?**
5. **Did the system correctly stop for approval?**

Do not jump straight to "the tool is broken."
A lot of bugs are actually layer confusion.

## The main pilot mistakes to avoid

### Mistake 1: treating a plan like permission
Nope. Cute idea. Wrong.

### Mistake 2: mixing WHAT with HOW
"Open Brave, click X, then maybe do Y" is execution detail.
Start with the goal, then inspect how the orchestra routes it.

### Mistake 3: skipping observability
If you cannot see observations, you are flying blind.
That is not piloting. That is vibes-based aviation.

### Mistake 4: retrying irreversible work casually
Absolutely not.

### Mistake 5: becoming the adapter
You should direct the system, not manually impersonate every layer unless you are debugging.

## If you only remember one mental model

Think of yourself like this:

- **You choose destination**
- **The orchestra chooses the route**
- **Adapters drive the roads**
- **Tools are the engine parts**
- **Approval is the ignition key for dangerous moves**

## Best files to study next

- `DroidPuppy/docs/ORCHESTRA_AGENT.md`
- `DroidPuppy/docs/ARCHITECTURE_REVIEW.md`
- `DroidPuppy/contracts/README.md`
- `DroidPuppy/orchestra/README.md`
- `docs/REPO_INVENTORY.md`

## Best first habit

When you feel overwhelmed, ask and answer this one question:

> Is this a WHAT, a HOW, a WITH WHAT, or an approval decision?

That single question prevents a shocking amount of architectural nonsense.
