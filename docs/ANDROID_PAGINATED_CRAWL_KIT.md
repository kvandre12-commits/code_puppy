# Android Paginated Crawl Kit

This helper was added after live Freecash crawling exposed a repeatable Android seam:

- pagination controls live near the bottom
- footer content can steal the viewport
- page taps are coordinate-sensitive in split screen
- useful capture usually means: recover viewport -> tap page -> scroll content -> capture again

## Plugin surface

The plugin lives at:

- `code_puppy/plugins/android_paginated_crawl_kit/`

It provides:

- `android_paginated_crawl_doctor`
- `android_paginated_crawl_examples`
- `android_paginated_crawl_run(plan_json, dry_run=True)`

It can now also probe one or more visible item/detail modals during the crawl.

## Plan shape

```json
{
  "artifact_prefix": "freecash-sample",
  "current_page_label": "3",
  "capture_current_page": true,
  "pagination_recovery_swipe": {
    "x1": 550,
    "y1": 1460,
    "x2": 550,
    "y2": 1750,
    "duration_ms": 250
  },
  "page_turns": [
    {"label": "4", "x": 994, "y": 1908}
  ],
  "item_taps": [
    {
      "page_label": "3",
      "label": "screw-guru",
      "x": 472,
      "y": 1492,
      "capture_stage": "detail-screw-guru",
      "close_tap": {"x": 1008, "y": 1185}
    }
  ],
  "scroll_passes_per_page": 2,
  "capture_swipe": {
    "x1": 550,
    "y1": 1830,
    "x2": 550,
    "y2": 1410,
    "duration_ms": 350
  },
  "capture_after_recovery": false,
  "settle_ms": 250
}
```

## Notes from the Freecash crawl

- visible offers strongly suggested a **game milestone ladder** pattern:
  - installs / open / login steps
  - tiny progression payouts
  - occasional larger reach/level payouts
- page-turn coordinates may need per-layout calibration in split screen
- if page buttons are visible but unreliable, the right workflow is still:
  - capture current state
  - adjust one coordinate
  - retry
  - write the calibration back into the plan
- if an offer row is visible and interesting, use `item_taps` to:
  - open the row/modal
  - capture the detail state
  - optionally close it
  - continue the crawl

## Governance note

The repo code now supports package-scoped Android constraints for future narrow leases, but a long-running tool host may need reload/restart before new constraint keys are accepted at runtime.
