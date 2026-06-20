from __future__ import annotations

import json
from typing import Any

from code_puppy.plugins.android_cdp_client.tooling import (
    CDPError,
    _cdp_call,
    _list_targets_raw,
    _pick_target,
)

DEFAULT_PORT = 9222


def _resolve_target(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> tuple[dict[str, Any], str]:
    targets = _list_targets_raw(local_port=local_port)
    target = _pick_target(
        targets,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
    )
    ws_url = str(target.get("webSocketDebuggerUrl") or "")
    if not ws_url:
        raise CDPError("Target does not expose webSocketDebuggerUrl")
    return target, ws_url


def _eval_json(
    expression: str,
    *,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> tuple[dict[str, Any], Any]:
    target, ws_url = _resolve_target(
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    _cdp_call(ws_url, "Runtime.enable")
    result = _cdp_call(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
    )
    remote = result.get("result", {})
    value = remote.get("value")
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            pass
    return target, value


def android_browser_read_page(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    max_text_chars: int = 4000,
    max_headings: int = 20,
) -> dict[str, Any]:
    expression = f"""
JSON.stringify((() => {{
  const headings = Array.from(document.querySelectorAll('h1,h2,h3'))
    .slice(0, {max_headings})
    .map(el => el.innerText || el.textContent || '');
  const links = Array.from(document.querySelectorAll('a[href]'));
  const text = (document.body && (document.body.innerText || document.body.textContent) || '').trim();
  return {{
    title: document.title,
    url: location.href,
    readyState: document.readyState,
    visibleText: text.slice(0, {max_text_chars}),
    visibleTextTruncated: text.length > {max_text_chars},
    visibleTextLength: text.length,
    headings,
    linkCount: links.length
  }};
}})())
""".strip()
    target, payload = _eval_json(
        expression,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "page": payload,
    }


def android_browser_get_html(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    selector: str = "document.documentElement",
    local_port: int = DEFAULT_PORT,
    max_chars: int = 20000,
) -> dict[str, Any]:
    selector_js = json.dumps(selector)
    expression = f"""
JSON.stringify((() => {{
  const expr = {selector_js};
  let el;
  if (expr === 'document.documentElement') {{
    el = document.documentElement;
  }} else if (expr === 'document.body') {{
    el = document.body;
  }} else {{
    el = document.querySelector(expr);
  }}
  if (!el) return {{ found: false, selector: expr, outerHTML: '', truncated: false, totalLength: 0 }};
  const html = el.outerHTML || '';
  return {{
    found: true,
    selector: expr,
    outerHTML: html.slice(0, {max_chars}),
    truncated: html.length > {max_chars},
    totalLength: html.length
  }};
}})())
""".strip()
    target, payload = _eval_json(
        expression,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "html": payload,
    }


def android_browser_list_links(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    text_contains: str = "",
    max_links: int = 50,
) -> dict[str, Any]:
    needle_js = json.dumps(text_contains.lower())
    expression = f"""
JSON.stringify((() => {{
  const needle = {needle_js};
  let links = Array.from(document.querySelectorAll('a[href]')).map(a => {{
    const text = (a.innerText || a.textContent || '').trim();
    return {{ text, href: a.href }};
  }}).filter(x => x.href);
  if (needle) {{
    links = links.filter(x => (x.text || '').toLowerCase().includes(needle) || (x.href || '').toLowerCase().includes(needle));
  }}
  const total = links.length;
  links = links.slice(0, {max_links});
  return {{ total, returned: links.length, links }};
}})())
""".strip()
    target, payload = _eval_json(
        expression,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "links": payload,
    }


def android_browser_get_text_by_selector(
    selector: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    if not selector.strip():
        raise ValueError("selector is required")
    selector_js = json.dumps(selector)
    expression = f"""
JSON.stringify((() => {{
  const selector = {selector_js};
  const nodes = Array.from(document.querySelectorAll(selector));
  return {{
    selector,
    count: nodes.length,
    text: nodes.map(n => (n.innerText || n.textContent || '').trim())
  }};
}})())
""".strip()
    target, payload = _eval_json(
        expression,
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "selector_result": payload,
    }
