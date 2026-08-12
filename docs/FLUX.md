# 𝕱 Flux — The Developer Superpower You Didn't Know You Needed

> *Stop babysitting your AI. Let Flux do the heavy lifting.*

Welcome to **Flux** — the structured, AI-assisted development pipeline that turns chaotic "vibe-coding" sessions into a smooth, repeatable, crash-proof workflow.

If you've ever lost hours of context to a terminal crash, wrestled with a bloated AI context window, or stared at a half-finished feature wondering "where was I?" — Flux was built for you.

---

## 🪄 Why Flux? (The Honest Pitch)

Here's the thing about working with AI coding assistants: **longer conversations aren't always better.**

There's a common trap developers fall into — assuming that a bigger context window will magically fix the AI's attention. It won't.

When you throw 30 files and 10,000 lines of context at an AI in one go, attention gets diluted, important details get lost, and quality tanks.

**Flux fixes this.** Instead of one giant "do everything" prompt, Flux breaks your work into focused, per-file passes — each step laser-focused on one thing.

The AI stays sharp because it's not trying to hold your entire codebase in its head at once.

And the best part? **Context anxiety is officially dead.**

After each Flux step, you can run `/clear` to wipe your context clean before the next step — because *everything Flux needs is already persisted to files in `~/.flux/`*.

No more babysitting the context window. No more starting over.

Oh, and crashes? **Flux laughs at crashes.**

If your terminal dies, your laptop restarts, or the universe decides to be rude mid-execution — just come back and pick up exactly where you left off.

If a crash happened while a Flux step was running, no problem: just rerun that step.

Your task files are safe, your progress is intact, and your sanity remains... mostly intact.

---

## 🖼️ The Big Picture

Flux organizes all your work around **task files** — small, focused markdown specs living in `~/.flux/<your-project>/todo/`.

Each task file is a living document that evolves as it moves through the pipeline, tracking its own stage and status in YAML frontmatter.

The pipeline looks like this:
```
new → ask → split → aug → exec → qa → tests → commit → create-pr
```

Nine steps. Each one does exactly one thing. Each one suggests the next. You stay in control.

---

## 🗂️ Project Setup (optional)

Run this **once per project or github worktree** from your project directory:
```
/flux/config TEST_CMD=<your-test-command-for-this-project>
# example:
/flux/config TEST_CMD="uv run ruff check . && uv run pytest -q --no-cov"
```

This creates `~/.flux/<your-project>/config.env` file.

NOTE: config.env is only used by the '/flux/tests' commands. If you don't plan to use that command, you can skip /flux/config and start directly with /flux/new.

---

## 🏗️ The ~/.flux Directory: Your Persistent Brain

Everything Flux needs lives here:
```
~/.flux/<flattened-project-dir>/
├── config.env           # Your project settings
├── stack.env            # Auto-detected tech stack
├── todo/                # Active task files — the action is here
│   ├── ADD_DARK_MODE.md
│   ├── FIX_AUTH_BUG.md
│   └── ...
├── done/                # Completed tasks (moved here when QA gives 10/10)
│   └── ...
└── review/              # Code review files & zips
```

The flattened project name is derived from your current working directory — all non-alphanumeric characters become hyphens.

So `/Users/you/projects/my-app` becomes `-Users-you-projects-my-app`. Flux automatically handles this — you never need to think about it.

---

## 🔢 The 9-Step Pipeline, Explained

### Step 1 — `/flux/new` · *Birth of a Task* 🐣
```
/flux/new "Add dark mode support with a toggle in settings"
or
/flux/new PROJ-892   # Pull directly from a Jira ticket!
```

Creates a task file in ~/.flux/<project>/todo/ with a clear spec, acceptance criteria, and metadata.

If you pass a Jira ticket ID, it fetches the ticket details automatically and builds the spec for you.
(you need to have a Jira MCP server installed for this to work)

---

### Step 2 — `/flux/ask` · *The Smart Questions Step* ❓
```
/flux/ask DARK_MODE
```

The agent reads the task, researches your codebase, and asks clarifying questions to fill in any gaps.

It also augments the spec with relevant codebase context it discovered. Think of this as the "no surprises later" step.

---

### Step 3 — `/flux/split` · *Divide and Conquer* 🥞
```
//flux/split DARK_MODE
```

If a task is too big to tackle in one pass (and many are), `split` decomposes it into several focused subtask files — each small enough to get 100% of the AI's attention.

The original task file is moved to `done`; the subtasks take its place. Smaller tasks = better results.

For example: DARK_MODE.md becomes DARK_1, DARK_2, DARK_3, DARK_4

---

### Step 4 — `/flux/aug` · *The Research Pass* 🔍
```
/flux/aug DARK_1
```

The deep research step. The agent explores your source code, finds the exact files and functions that need changing,
and annotates the task file with precise implementation notes and file citations.

When exec runs, it knows exactly where to go. No guessing, no hallucinating paths.

**Pro tip:** Run `/flux/aug 2` or `/flux/exec 3` to process multiple tasks simultaneously using parallel sub-agents. Run `/flux/aug all` to process all task files sequentially

---

### Step 5 — `/flux/exec` · *The Magic Happens* 🪄
```
/flux/exec DARK_1
```

Implementation time. The agent reads the task file (which is now packed with research from aug) and implements
exactly what the spec says — no more, no less. No scope creep. No "I also noticed..." detours.

**Pro tip:** Run `/flux/exec 2` or `/flux/exec 3` to process multiple tasks simultaneously using parallel sub-agents. Run `/flux/exec all` to process all task files sequentially

---

### Step 6 — `/flux/qa` · *The 10/10 Gate* ✅
```
/flux/exec DARK_1
```

The agent reviews the implementation against the acceptance criteria and gives it a score from 1–10.

- **10/10?** ✅ Task moves to `done/`. You're done with this one.
- **Less than 10/10?** 🔁 The task file gets updated with feedback, marked `needs-rework`. Run `/flux/exec` again, then `/flux/qa` again. Repeat until 10/10.

The QA loop is your quality guarantee. Nothing ships until it's genuinely complete.

**Pro tip:** Run `/flux/qa 2` or `/flux/qa 3` to process multiple tasks simultaneously using parallel sub-agents. Run `/flux/qa all` to process all task files sequentially

---

### Step 7 — `/flux/tests` · *Regression-Proof Your Work* 🧪
```
/flux/tests
```

Runs your configured `TEST_CMD` from the `config.env` file. Fixes any regressions introduced by your changes.

Critically: **pre-existing test failures are left untouched** — Flux only fixes what it broke. No surprise test suite cleanups you didn't ask for.
Of course, if you want pre-existing failures to be fixed, just ask.

---

### Step 8 — `/flux/commit` · *The Perfect Commit Message* 💾
```
/flux/commit
```

Reads the diff, reads your completed tasks, and crafts a detailed, meaningful commit message.

Asks for your confirmation before committing. No more `"fix stuff"` commits.

---

### Step 9 — `/flux/create-pr` · *Ship It* 🚢
```
/flux/create-pr
```

Creates a GitHub PR with a comprehensive description derived from your task files.

Idempotent — if a PR already exists for your branch, it shows you the link instead of creating a duplicate.

(we highly recommend installing the github cli, 'gh' (https://cli.github.com/))

---

## ⚡ Supercharge: Parallel Agents

Three pipeline steps support parallel multi-agent execution:

| Command | What it does |
|---|---|
| `/flux/aug 3` | Augments all todo tasks with 3 concurrent agents |
| `/flux/exec 2` | Implements all todo tasks with 2 concurrent agents |
| `/flux/qa 2` | Reviews all todo tasks with 2 concurrent agents |


`aug`, `exec` and `qa` also accept "all" as argument. When passed it will process all task files.
Example:
```
/flux/split IMPLEMENT_DARK_MODE # breaks the file down into e.g. DARK_1, DARK_2, DARK_3, DARK_4
# then, you can just continue like this:
/flux/aug all
/flux/exec all
/flux/qa all
```

### 🧠 Smart Scheduling: How Parallel Exec Actually Works

- When you run `/flux/exec 2` (or any number > 1) with multiple specs sitting in your `todo/` directory, Flux doesn't just blindly fire off N agents at once. It's smarter than that.

  Say you've got 8 specs that have all been through ask, split, and aug. When you invoke `/flux/exec 2`, Flux analyzes the dependency graph across those tasks and groups them into pairs that are safe to run in parallel — then orders those pairs intelligently. So instead of a naive top-to-bottom execution, you might see it run tasks 1 and 3 first, then 5 and 6, then 2 and 4 — whatever ordering minimizes conflicts and maximizes throughput.

- If two tasks have strict dependencies (task B must complete before task C can start), Flux won't try to run them together. Instead, it silently falls back to sequential execution for that pair and tells you exactly why — so you're never left guessing why something didn't run in parallel.

The result: your 8-task batch finishes as fast as your dependency graph allows, with zero manual orchestration on your part.

---

## 📋 The Flux Status Panel

**This is your mission control.** A sleek real-time overlay that shows exactly where all your tasks stand in the pipeline.

### Opening It

- **Command:** `/flux/status`

### What You'll See

```
𝕱 FLUX STATUS                              (Ctrl+F to close)
══════════════════════════════════════════════════════════════════
TODO-FILE                  STAGE    STATUS
──────────────────────────────────────────────────────────────────
DARK_MODE.md               exec     ✅ done
FIX_AUTH_BUG.md            qa       🔁 needs-rework
ADD_NOTIFICATIONS.md       aug      🔄 in-progress
══════════════════════════════════════════════════════════════════
  COMPLETED TASKS ▼     REVIEW TASKS ▼   cheatsheet ▼
```

**Status icons explained:**

- 🔄 `in-progress` — actively being worked on
- 🔁 `needs-rework` — QA scored it < 10/10, needs another exec pass
- ✅ `done` — QA approved (10/10), moved to `done/`

If you want a focused status, you can do this:
`/flux/status todo` — to see only tasks files in the `~/.flux/<flattened-dir>/todo` dir.
`/flux/status done` — to see only completed tasks in the `~/.flux/<flattened-dir>/done` dir.
`/flux/status review` — to see only review tasks in the `~/.flux/<flattened-dir>/review` dir.

`/flux/cheatsheet`— to see the four pipeline variants (A/B/C/D). Your quick reference.

---

## 🎯 Pre-Built Pipelines

Don't want to think about which steps to run? Use a pre-built pipeline.

### Pipeline A — New Feature or Bug Fix
```
/flux/new → /flux/ask → /flux/split → /flux/aug → /flux/exec → /flux/qa → /flux/tests → /flux/commit → (test app manually) → /flux/create-pr
```

### Pipeline B — Self-Review Before Merging
```
/flux/review → /flux/address-feedback → /flux/ask → /flux/exec → /flux/qa → /flux/tests → /flux/commit
```

### Pipeline C — Address Feedback You Received
```
/flux/address-feedback <path-to-zip-file> → /flux/ask → /flux/exec → /flux/qa → /flux/tests → /flux/commit
```

### Pipeline D — Review Someone Else's PR
```
/flux/review <PR#> → (post the zip file on the PR)
```

### Auto-Pilot Mode — The Full Enchilada
```
/flux/auto-pilot "Add dark mode support to settings panel"
```
Orchestrates the entire Pipeline A end-to-end. Pauses only for `ask` (clarifying questions that genuinely need you) and hands you the PR link at the end.

---

## 🛠️ Utility Commands

| Command | What it does |
|---|---|
| `/flux/about` | Shows you a quick TL;DR|
| `/flux/review [PR#]` | Full code review vs parent branch, produces `review.zip` |
| `/flux/address-feedback [zipfile]` | Converts review comments into todo task files |
| `/flux/status` | Open the pipeline status panel |
| `/flux/cheatsheet` | Open the pipeline status panel |
| `/flux/config` | One-time per project setup (optional)|

---

## 💡 Tips & Tricks

- Use `about` to get a quick TL;DR of Flux
```
/flux/about
```
- **❕For best results, use GitHub worktrees.**
    - For a new feature or bug fix, create a new local branch and a GH worktree from that branch.

        Example:
        ```
        git worktree add -b luc/PROJ-426-collect-cust-satisfaction ../wt-luc-PROJ-426-collect-cust-satisfaction

        /flux/new PROJ-426

        # OR, if no Jira ticket
        git worktree add -b luc/chore-remove-dead-code ../wt-luc-chore-remove-dead-code

        /flux/new scan the code base, identify dead code and safely remove; all functionality and UI/UX should remain intact
        ```
    - For a review on someone else's PR, create a GH worktree from that branch.

        Example:
        ```
        git worktree add -b wes/fix-loader ../wt-wes-fix-loader

        /flux/review
        ```

- **Clear context between steps — it's fine, actually encouraged:**
  The `/clear` wipes the agent's in-memory context, but your task file (packed with research from `aug`) is sitting safely on disk. Context anxiety: cured.

      Example:
      ```
      /flux/aug DARK_MODE
      /clear
      /flux/exec DARK_MODE
      ```

- **Crashed mid-step? Just rerun it:** If anything goes wrong while a Flux step is executing — terminal crash, laptop restart, network blip — just run the same step again. Flux steps are designed to be re-runnable. Your task files preserve state.

- **Path shortcuts:** You don't have to type the full path to a task file. `DARK_MODE` auto-expands to `~/.flux/<your-project>/todo/DARK_MODE.md`. Flux knows where to look.

- **Jira-first workflow:** Got a Jira ticket with a good, detailed description? Skip writing a spec entirely:
  Flux fetches the ticket, builds the spec, and you're off.
  ```
  /flux/new PROJ-1234
  ```
  (you need to have a Jira MCP pre-installed)

---

## 🔑 Quick Reference
```
/flux/config          # One-time setup (do this first!)
/flux/new             # Create a task
/flux/ask             # Research & clarify
/flux/split           # Break big tasks into small ones
/flux/aug [N]         # Deep research pass (N = parallel agents)
/flux/exec [N]        # Implement (N = parallel agents)
/flux/qa [N]          # Quality review (N = parallel agents)
/flux/tests           # Fix regressions
/flux/commit          # Commit with a great message
/flux/create-pr       # Ship the PR

/flux/status          # Pipeline status panel (or Ctrl+F)
/flux/review [PR#]    # Code review
/flux/address-feedback # Convert review → tasks
/flux/auto-pilot      # Let Flux drive (Pipeline A, end-to-end)

```


---

## 🏃‍♂️ You're Ready

Flux isn't just a workflow — it's a mindset shift.
Stop thinking of AI coding as "one big conversation" and
start thinking of it as a **pipeline of focused, reliable steps**.

Each step does one thing.
Each step persists its output.
Each step picks up where the last one left off.
Your context is clean.
Your progress is safe.
Your quality is guaranteed.

**Go build something great. 𝕱 Flux has your back. ⚡**

---

*Inspired by the original `gandalf` workflow by David Maple.*

---
