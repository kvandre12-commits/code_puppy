# Project JSON agents

This repo ships project-level JSON agents under `.code_puppy/agents/`.

Current agents:
- `split-my-pr` — reviews local git changes and suggests a tighter PR title, summary, risk notes, and split plan before you push a giant haunted diff.
- `workflow-state` — describes what is true right now from evidence only.
- `execution-plan` — proposes next bounded steps without granting permission.
- `approval-decision` — frames the only authoritative permission object in the local governance chain.
- `journal-audit` — reconciles what was approved, attempted, and actually observed.
- `governance-orchestrator` — explicitly runs `workflow-state -> execution-plan -> approval-decision -> journal-audit`.
