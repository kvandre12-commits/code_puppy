"""DroidPuppy 'edge' — one-shot element testing over Android CDP.

The goal: ask one question — "is this element on the page, and what does it
look like?" — and get a clean structured answer (existence, match count, text,
attributes, geometry, visibility) without juggling raw CDP calls.

It is a thin, DRY layer on top of ``android_cdp_client``:
- ``android_cdp_navigate`` to (optionally) drive a tab to a URL
- ``android_cdp_eval_js`` to run the inspection snippet in the page

Nothing here raises into the agent loop; failures return ``success=False``
with an ``error`` string.
"""

from __future__ import annotations

import json
from typing import Any

from code_puppy.plugins.android_cdp_client.tooling import (
    android_cdp_eval_js,
    android_cdp_navigate,
)

DEFAULT_PORT = 9222
MAX_ELEMENTS = 10

# JS template: describe up to N elements matching a selector. The selector is
# injected as a JSON string literal so quotes/backslashes are always safe.
_INSPECT_JS = """
(function() {
  var sel = %s;
  var max = %d;
  var els;
  try { els = Array.prototype.slice.call(document.querySelectorAll(sel)); }
  catch (e) { return JSON.stringify({selectorError: String(e)}); }
  function describe(el) {
    var r = el.getBoundingClientRect();
    var st = window.getComputedStyle(el);
    var visible = !!(r.width || r.height)
      && st.visibility !== 'hidden'
      && st.display !== 'none'
      && st.opacity !== '0';
    var attrs = {};
    for (var i = 0; i < el.attributes.length; i++) {
      attrs[el.attributes[i].name] = el.attributes[i].value;
    }
    return {
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      classes: el.className || null,
      text: (el.innerText || el.textContent || '').trim().slice(0, 300),
      href: el.getAttribute('href'),
      value: ('value' in el) ? el.value : null,
      attributes: attrs,
      rect: {x: Math.round(r.x), y: Math.round(r.y),
             w: Math.round(r.width), h: Math.round(r.height)},
      visible: visible,
      enabled: !el.disabled,
      inViewport: r.top >= 0 && r.left >= 0
        && r.bottom <= (window.innerHeight || document.documentElement.clientHeight)
        && r.right <= (window.innerWidth || document.documentElement.clientWidth)
    };
  }
  return JSON.stringify({
    selector: sel,
    found: els.length > 0,
    count: els.length,
    pageUrl: location.href,
    pageTitle: document.title,
    elements: els.slice(0, max).map(describe)
  });
})()
""".strip()


def _build_expression(selector: str) -> str:
    return _INSPECT_JS % (json.dumps(selector), MAX_ELEMENTS)


def android_edge_test_element(
    selector: str,
    url: str = "",
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    """Test whether a CSS selector matches elements on a live page.

    Picks a CDP page target (by id / url_contains / title_contains, else the
    first page), optionally navigates it to ``url`` first, then reports match
    count, text, attributes, geometry, and visibility for the matches.
    """
    if not selector.strip():
        return {"success": False, "error": "selector is required"}

    navigated = None
    if url:
        nav = android_cdp_navigate(
            url=url,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )
        navigated = nav.get("target")
        # Lock onto the tab we just navigated so eval hits the same page.
        target_id = str((nav.get("target") or {}).get("id") or target_id)

    result = android_cdp_eval_js(
        expression=_build_expression(selector),
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )

    if not result.get("success"):
        return {
            "success": False,
            "error": "eval failed",
            "exceptionDetails": result.get("exceptionDetails"),
            "target": result.get("target"),
        }

    raw = ((result.get("result") or {}).get("value")) or "{}"
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return {"success": False, "error": "could not parse inspection result", "raw": raw}

    if parsed.get("selectorError"):
        return {"success": False, "error": f"invalid selector: {parsed['selectorError']}"}

    return {
        "success": True,
        "selector": selector,
        "found": parsed.get("found", False),
        "count": parsed.get("count", 0),
        "page": {"title": parsed.get("pageTitle"), "url": parsed.get("pageUrl")},
        "elements": parsed.get("elements", []),
        "navigated_to": navigated,
        "target": result.get("target"),
    }


def android_edge_assert_text(
    selector: str,
    expected_text: str,
    url: str = "",
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    """Assert that the first element matching ``selector`` contains expected text.

    Great for quick smoke checks: 'does the H1 say what I think it says?'.
    Returns ``passed`` plus the actual text found.
    """
    probe = android_edge_test_element(
        selector=selector,
        url=url,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    if not probe.get("success"):
        return probe

    elements = probe.get("elements", [])
    actual = elements[0].get("text", "") if elements else ""
    passed = bool(elements) and expected_text.lower() in actual.lower()
    return {
        "success": True,
        "passed": passed,
        "selector": selector,
        "expected_text": expected_text,
        "actual_text": actual,
        "found": probe.get("found", False),
        "count": probe.get("count", 0),
        "page": probe.get("page"),
    }
