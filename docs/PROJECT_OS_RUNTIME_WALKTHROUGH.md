# Project OS Runtime Walkthrough

This is the smallest implemented Project OS runtime theorem:

```text
Valid AuthorityGrant + valid active one-shot LeaseRecord
  -> exactly one bounded effect
  -> auditable EventRecord
```

The bounded effect is intentionally boring: `noop_executed`. The point is not to
launch a browser, touch Android, mutate GitHub, or submit a trade. The point is
to prove that the control plane can govern one runtime effect.

## Control plane vs effect plane

```text
Control plane:
  identity
  authority grant
  authority validation
  lease issuance
  audit events

Effect plane:
  one scoped action under one active lease
```

Future Android, browser, GitHub, or broker-adjacent effects should preserve this
shape. Only the effect implementation should change.

## Implemented lifecycle

```text
Project Run
  -> AuthorityGrant draft
  -> Authority registry validation
  -> AuthorityGrant create plan
  -> confirmed AuthorityGrant creation
  -> authority check passes
  -> confirmed lease issuance
  -> execute no-op
  -> audit event
  -> refuse lease reuse
```

## Safe sandbox demo

This demo uses a temporary state file, so it does not mutate your normal Code
Puppy Project OS state.

Run it from the repo root:

```bash
python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from code_puppy.plugins.project_runtime import commands, store

GRANT_ID = "grant:run-demo:project_run.execute_bounded_step"
LEASE_ID = "lease:run-demo:project_run.execute_bounded_step"

with TemporaryDirectory() as tmp:
    store.STATE_FILE = str(Path(tmp) / "project_runs.json")

    print(commands.dispatch([
        "run", "create", "run-demo",
        "--project", "Code Puppy",
        "--objective", "Prove governed runtime",
        "--status", "ready",
    ]))
    print("---")
    print(commands.dispatch(["authority", "grant-draft"]))
    print("---")
    print(commands.dispatch(["authority", "validate"]))
    print("---")
    print(commands.dispatch(["authority", "grant-create-plan"]))
    print("---")
    print(commands.dispatch(["authority", "grant-create", "--confirm", GRANT_ID]))
    print("---")
    print(commands.dispatch(["run", "authority-check"]))
    print("---")
    print(commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID]))
    print("---")
    print(commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID]))
    print("--- reuse is refused ---")
    print(commands.dispatch(["run", "execute-noop", "--confirm", LEASE_ID]))
    print("--- audit trail ---")
    print(commands.dispatch(["run", "events", "run-demo"]))
PY
```

You should see these important state transitions:

```text
grant-create       -> created: yes
run authority-check -> lease_issuable: yes
lease-issue        -> issued: yes
execute-noop       -> executed: yes
execute-noop again -> executed: no
```

And the audit trail should include:

```text
run_created
authority_grant_created
lease_issued
noop_executed
```

## Refusal theorem

The tests intentionally spend most of their effort proving that dangerous paths
do not mutate state:

```text
missing authority  -> no lease mutation
wrong confirmation -> no mutation
expired lease      -> no effect
reused lease       -> no second effect
revoked authority  -> no effect
```

The regression suite for this theorem is:

```bash
python -m pytest -q -o addopts='' tests/test_project_runtime_lease_noop.py
```

For the full Project OS runtime slice:

```bash
python -m pytest -q -o addopts='' \
  tests/test_project_runtime.py \
  tests/test_project_runtime_events.py \
  tests/test_project_runtime_validator.py \
  tests/test_project_os_scenarios.py \
  tests/test_project_runtime_candidates.py \
  tests/test_project_runtime_selection.py \
  tests/test_project_runtime_dispatch_plan.py \
  tests/test_project_runtime_lease_draft.py \
  tests/test_project_runtime_authority_check.py \
  tests/test_project_runtime_authority_grants.py \
  tests/test_project_runtime_authority_grant_draft.py \
  tests/test_project_runtime_authority_validate.py \
  tests/test_project_runtime_authority_grant_create_plan.py \
  tests/test_project_runtime_authority_grant_create.py \
  tests/test_project_runtime_lease_noop.py
```

## What this is not

This is not an external automation feature yet.

It does not:

```text
open Android apps
launch browsers
call GitHub APIs
place broker orders
execute arbitrary shell commands
```

That is the point. The first effect is harmless so the authority, lease, and
audit mechanics can be judged on their own.

## Extension rule

Any future real effect should keep this contract:

```text
valid authority + valid active unconsumed lease
  -> exactly one bounded effect
  -> consume lease
  -> write audit event

missing/expired/reused/revoked authority
  -> no effect
  -> no hidden mutation
```
