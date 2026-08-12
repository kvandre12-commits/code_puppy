# Mike Test Run 001

**Status:** planned
**Purpose:** first intentional **no-Kurtis** Android install attempt

This is not a theory document.
This is the next evidence artifact.

See also:
- `docs/ANDROID_MIKE_TEST_PROVENANCE.md`

For Mike Test Run 001, **failure is a valid deliverable**.
A failed run that exposes one hidden dependency is progress.

---

## Mike Test Rules

- Fresh Android device
- Fresh Termux
- Fresh target checkout
- Only documented instructions
- No Kurtis intervention
- No personal setup shortcuts
- No hidden oral history

If Kurtis intervenes during the run:

- mark the run **contaminated**
- stop claiming it was a real Mike test
- record what intervention was needed
- restart later under clean conditions

If the test fails:

- **Do not fix immediately**
- First capture the failure
- Then identify the hidden dependency it exposed
- Treat the first meaningful failure as the primary deliverable of the run

---

## Core question

Can a fresh Android device starting from the declared Code Puppy target reach a working installation
without Kurtis-specific setup knowledge?

---

## Expected relationship to the scorecard

This run primarily advances:

- `docs/ANDROID_ACCEPTANCE_SCORECARD.md`
  - **Mike Installer Test**

It may also generate evidence for:

- Fresh-Install Viability
- Kennel Operator Substitution Test
- Android candidate explanations in `docs/ANDROID_CANDIDATE_DECISIONS.md`

---

## Pre-run checklist

- [ ] Fresh phone or meaningfully fresh Android environment
- [ ] Fresh Termux install
- [ ] No project-specific dotfiles or cached setup shortcuts
- [ ] One explicit target selected: upstream main / upstream PR ref / current fork PR branch
- [ ] Install surface matches target: published-package flow for upstream acceptance, source-checkout path for PR/ref validation
- [ ] Current Android docs available
- [ ] Kennel available only if the operator is using the official repo tooling path

---

## Exact clean-run environment steps

Use these steps for the **clean Mike acceptance run** against upstream main.
This is the default acceptance path unless you are explicitly running a PR/ref
validation instead.

### Device setup

1. Start with a fresh Android device or a meaningfully clean reset state.
2. Install **Termux from F-Droid or GitHub**.
3. Do **not** install project dotfiles, helper scripts, or personal bootstrap shortcuts.
4. Do **not** ask Kurtis for help during the run.

### Clean-state capture before install

Run these first and paste the output into the run log:

```bash
uname -a
getprop ro.build.version.release
termux-info || true
command -v code-puppy || true
command -v uv || true
command -v python || true
env | grep '^VIRTUAL_ENV=' || true
pkg list-installed | grep -E '^(git|python|uv|ripgrep|proot)/' || true
```

If any hidden setup appears here that should not exist on a fresh run, stop and
mark the run contaminated before continuing.

### Exact command sequence for upstream-main clean Mike test

Run these commands in order and paste them into the run log exactly as used:

```bash
pkg update && pkg upgrade
pkg install python git
pkg install uv
uvx --from code-puppy code-puppy-bootstrap detect --json
uvx --from code-puppy code-puppy-bootstrap plan --profile auto
pkg install ripgrep proot
uv tool install --refresh code-puppy
code-puppy -i
```

### If `pkg install uv` fails

Use only the documented fallback:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then resume at:

```bash
uvx --from code-puppy code-puppy-bootstrap detect --json
```

### Contamination guardrails during the run

Mark the run **contaminated** if any of these happen:

- Kurtis gives instructions beyond the written docs
- a helper script or personal alias is used
- an existing `code-puppy` install is discovered and reused
- an active virtualenv leaks into the run
- the target under test changes mid-run without being recorded

---

## Run log

### Environment

- Device:
- Android version:
- Termux version:
- Network conditions:
- Date/time:
- Operator:

### Target under test

- Target class: upstream main / upstream PR ref / current fork PR branch
- Repo URL:
- Remote name:
- Branch/ref:
- Commit SHA:
- Install surface: published-package flow / source-checkout flow
- Evidence source: clean run / proxy run / imported proof / other
- Contamination state: clean / contaminated / unknown at start
- Why this target matters:

### Documented install path used

Record which install surface this run uses:

- published-package Android flow
- source-checkout PR/ref validation flow

Paste the exact steps followed from docs. If this run targets our PR/branch,
record the exact checkout step that moved the environment onto that target and
make sure the install path actually exercises the checked-out branch code rather
than silently installing the published package.

```text
```

### Actual commands run

```text
```

---

## Outcome

- [ ] Pass: working agent reached
- [ ] Fail: installation/bootstrap/runtime blocked
- [ ] Partial: some milestone reached, but operational agent not achieved cleanly
- [ ] Contaminated: Kurtis intervention or hidden shortcut entered the loop

### If pass

Record:
- What worked unexpectedly well?
- What documentation was sufficient?
- What hidden dependency appears to have been removed?

### If fail

Record the **first meaningful failure**, not five layers of downstream wreckage.
This is a success condition for the evidence run if the hidden dependency becomes visible.

- Failure step:
- Exact command:
- Error excerpt:
- Full log path:

```text
```

---

## Hidden dependency exposed

Choose the best current fit:

- [ ] Missing documentation
- [ ] Hidden package assumption
- [ ] Environment assumption
- [ ] Bootstrap assumption
- [ ] Dependency-resolution/build-pressure issue
- [ ] Error-message quality issue
- [ ] Kennel retrieval gap
- [ ] Other:

### Explanation

What Kurtis knew that the system did not yet carry on its own:

```text
```

---

## Triage using current Android knowledge

Before proposing fixes, answer:

### Known dead ends checked?

- [ ] `validation-requires-system-python` is rejected
- [ ] `remove-playwright-and-android-is-fixed` is rejected
- [ ] `browser-automation-never-works-on-android` is rejected

### Current leading explanation considered?

- [ ] `avoid-unnecessary-native-build-pressure`

### Current challenger considered?

- [ ] `validation-prefers-lean-runtime-paths`

### Current next discriminator considered?

- [ ] `large environment + prebuilt wheels only`

---

## Next vertical slice candidate

After the first failure is captured, answer:

What is the **single highest-value next slice** revealed by this failure?

```text
```

Good answers look like:
- improve one missing doc step
- isolate one hidden package assumption
- improve one bootstrap message
- run one discriminating mutant

Bad answers look like:
- invent three more governance layers
- rename the ontology again
- write another cathedral README before testing the exposed failure

---

## Final summary

```text
Mike Test Run 001 result:
Hidden dependency exposed:
Relevant Android posture:
Recommended next slice:
Contaminated?:
Install surface used:
Evidence source:
```

---

## Deliverable rule

For this first run, the most valuable next artifact is expected to be one of:

- `PASSED_MIKE_TEST_001.md`
- `FAILED_MIKE_TEST_001.md`

A failure artifact is a **win** if it clearly exposes:

- the first hidden dependency
- the relevant Android posture
- the next vertical slice

The only truly bad outcome is a quietly rescued run that teaches the repo nothing.
