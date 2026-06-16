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

## Tool

- `chatgpt_robinhood_delegate`

The tool prepares a handoff prompt for:

- account reads
- market data checks
- order drafts
- submit/cancel/replace requests

## Current safety posture

- No direct Robinhood execution from this plugin
- `order_submit`, `order_cancel`, and `order_replace` are forced to
  `operator_confirm_required`
- This is a bridge to an existing ChatGPT connector session, not a local
  Robinhood OAuth implementation

## Obvious next step

If you want full automation later, the next layer is a **browser/UI bridge**
that opens an authenticated ChatGPT session and submits the generated handoff.
That can be added as a separate plugin without lying about direct connector
access today.
