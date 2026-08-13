# SharpEdge Wrapper Matrix

_Last verified: 2026-08-12_

This is the routing map for the active SharpEdge repositories surrounding the
Code Puppy checkout. It prevents integration glue from quietly becoming a
second analytics engine, broker, or Android product.

## Ownership and integration status

| Repository | Owns | Primary contract/artifact | Code Puppy integration | Current gap |
| --- | --- | --- | --- | --- |
| `SharpEdge-System` | Market analytics, cockpit signals, Trade Gate, operator artifacts | `sharpedge.signal.v1`, `outputs/signal.json`, operator packets | `sharpedge_market_state` validates and projects the live signal through in-process and read-only MCP tools; downstream bridge tools remain separate | Historical candle/path queries still require a dedicated stable producer contract |
| `SharpEdge-Robinhood-Bridge` | Broker-command classification and approval-gated handoff planning | `sharpedge.robinhood_execution_handoff.v1` | Strong: `chatgpt_robinhood_delegate` can plan, package, and audit connector handoffs | Connector boundary remains asynchronous and operator-confirmed by design |
| `SharpEdge-Android` | Kotlin/Compose rendering and imported contract cache | `sharpedge.signal.v1`, `sharpedge.operator_packet.v1` | Generic DroidPuppy Android launch, intent, diagnostics, and UI tools | No product-specific install/build/import health wrapper |
| `SharpEdge-Ace` | Minimal deterministic scoring core | `ace_snapshot.json` input and compact score/gate/bias output | None; Ace reads SharpEdge-System snapshots directly | No read-only Code Puppy adapter for scoring or comparing Ace with the full signal |
| `SharpEdge-WMT` | Focused WMT research pipeline | Planned SQLite, options, gap, and score artifacts | None | Repo is early-stage; do not wrap unfinished contracts |
| `SE-short-detector` | Standalone squeeze-risk ranking | Canonical candidate and detector result contracts | None | A future adapter should expose results as context, never silently alter execution rules |
| `TENSION-MODEL` | Unclassified scripts, SQL, and data | No verified stable contract | None | Define ownership and a versioned contract before integration |
| Code Puppy `sec_edgar` plugin | Official SEC identity, filing metadata, and bounded XBRL facts | `sharpedge.sec_edgar.*.v1` tool payloads | Complete: in-process tools plus read-only SharpEdge MCP server | Original filing context still requires operator verification |

## Hard boundaries

- Code Puppy owns agent runtime, plugins, tools, and governed integration glue.
- DroidPuppy owns Android actuation and observation capabilities, not product UI.
- SharpEdge-System owns market truth and signals, not broker execution.
- SharpEdge-Robinhood-Bridge owns broker command routing, not trading authority.
- SharpEdge-Android owns native rendering, not analytics or execution.
- Ace and the short detector provide bounded analytical context; neither may
  silently override unrelated trade gates.
- Broker writes, live trading, secrets, and production mutation always require
  their own explicit authority. Repository-write authority is not a substitute.

## Integration order

1. Keep SEC EDGAR read-only and source-attributed.
2. Keep the read-only SharpEdge market-state adapter freshness-aware and projection-only; do not duplicate cockpit analytics.
3. Add an Ace comparison adapter only after its input/output contract is frozen.
4. Add a SharpEdge-Android import-health wrapper before attempting build tooling.
5. Leave WMT unwrapped until its first durable artifact exists.
6. Classify TENSION-MODEL before writing any integration code.

## Workspace discovery

The repository catalog defaults intentionally list verified active repositories
rather than crawling every home-directory experiment. Explicit discovery avoids
promoting temporary clones, proof directories, virtual environments, and
archives into architectural dependencies.
