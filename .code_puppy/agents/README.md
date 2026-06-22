# Project JSON agents

This repo ships project-level JSON agents under `.code_puppy/agents/`.

Current agents:
- `split-my-pr` — reviews local git changes and suggests a tighter PR title, summary, risk notes, and split plan before you push a giant haunted diff.
- `workflow-state` — describes what is true right now from evidence only, and writes only the canonical `workflow_state` object.
- `execution-plan` — proposes next bounded steps without granting permission, and writes only the canonical `execution_plan` object.
- `lease-request` — derives the minimum lease/evidence ask needed for a governed effectful step without pretending a lease already exists, and defaults lease identity to the stable authority principal instead of ephemeral actor/run ids.
- `approval-decision` — frames the only authoritative permission object in the local governance chain, and writes only the canonical `approval_decision` object while keeping future lease identity bound to the stable authority principal.
- `workflow-commit` — freezes the current handshake, plan, and approval posture into a durable workflow commit receipt without pretending that commit equals permission.
- `lease-audit` — checks live authority-gateway lease/audit posture against the governed request and records mismatches plainly.
- `journal-audit` — reconciles what was approved, attempted, and actually observed, then appends a canonical journal entry.
- `governance-orchestrator` — explicitly runs `handshake -> workflow-state -> execution-plan -> lease-request -> approval-decision -> workflow-commit -> lease-audit -> journal-audit` against the DroidPuppy context packet.
