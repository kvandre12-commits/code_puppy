# ChatGPT Robinhood Delegate

This plugin gives Code Puppy agents a **truthful** Robinhood delegation path:
prepare a handoff for a ChatGPT session that already has the Robinhood
connector enabled.

## Why this exists

Code Puppy's current `chatgpt_oauth` integration uses the ChatGPT Codex backend
as a **model provider**. It does **not** expose ChatGPT connector tools directly
inside Code Puppy.

So instead of pretending we can call the connector natively, this plugin:

- builds a structured delegation packet
- writes `outputs/<artifact>.json`
- writes `outputs/<artifact>.txt`
- keeps live-order style requests approval-gated

## Tools

- `chatgpt_robinhood_delegate`
- `chatgpt_robinhood_delegate_from_handoff`
- `chatgpt_robinhood_delegate_from_signal`
- `chatgpt_robinhood_audit_ingest`
- `chatgpt_robinhood_loop`

The plugin can either prepare a handoff from raw task fields, consume the
stable `sharpedge.robinhood_execution_handoff.v1` artifact emitted by
`SharpEdge-Robinhood-Bridge`, run the bridge `signal-handoff` step first and
then package the result in one shot, ingest the downstream connector result
back into SharpEdge as structured audit + journal artifacts, or run the whole
thing as a two-phase loop with a persisted manifest.

The tools prepare a handoff prompt for:

- account reads
- market data checks
- order drafts
- submit/cancel/replace requests

## Two-phase loop

`chatgpt_robinhood_loop` supports:

- `action='start'` → run bridge prep + write delegation artifacts + persist `outputs/<artifact>_loop.json`
- `action='finish'` → ingest the later connector response back into audit artifacts tied to that loop
- `action='status'` → inspect the saved loop manifest without mutating it

That gives agents an honest async workflow instead of pretending the downstream
ChatGPT connector response will materialize in the same tool call.

## Audit loop

`chatgpt_robinhood_audit_ingest` accepts:

- raw connector response text
- structured connector response JSON
- or a saved connector response file

It writes:

- `outputs/<artifact>.json` as `sharpedge.robinhood_connector_audit.v1`
- `outputs/<artifact>_journal_stub.json` as `sharpedge.trade_journal_stub.v1`
- `outputs/<artifact>_journal_stub.md` for human review
- `outputs/robinhood_connector_audit_log.jsonl` as an append-only breadcrumb log
- `outputs/robinhood_live_positions.json` when the connector response includes normalizable live positions

If you provide the originating bridge handoff path too, the audit artifact is
enriched with the requested action, approval posture, and setup context. That
lets SharpEdge compare **intent** versus **observed connector outcome** without
pretending it has direct connector telemetry.

## Current safety posture

- No direct Robinhood execution from this plugin
- `order_submit`, `order_cancel`, and `order_replace` are forced to
  `operator_confirm_required`
- `chatgpt_robinhood_delegate_from_handoff` refuses stand-down or non-approval-ready
  bridge packets instead of pretending there is a live broker action to take
- `chatgpt_robinhood_delegate_from_signal` invokes the real bridge CLI instead
  of duplicating bridge planning logic inside Code Puppy
- This is a bridge to an existing ChatGPT connector session, not a local
  Robinhood OAuth implementation
- The audit layer records what the connector said happened, but it still does
  not claim broker execution authority or fabricate connector-side truth

## Obvious next step

If you want full automation later, the next layer is a **browser/UI bridge**
that opens an authenticated ChatGPT session and submits the generated handoff.
That can be added as a separate plugin without lying about direct connector
access today.
