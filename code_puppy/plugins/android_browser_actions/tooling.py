from __future__ import annotations

import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from code_puppy.plugins.android_browser_easy.tooling import _resolve_target
from code_puppy.plugins.android_cdp_client.tooling import CDPError, _cdp_call

DEFAULT_PORT = 9222
OUTPUT_DIR = Path("outputs")


def _eval_json_on_target(ws_url: str, expression: str) -> Any:
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
            return json.loads(value)
        except Exception:
            return value
    return value


def android_browser_click_link_by_text(
    text: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    exact: bool = False,
    wait_seconds: float = 1.0,
) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required")
    target, ws_url = _resolve_target(
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    needle = json.dumps(text)
    expression = f"""
JSON.stringify((() => {{
  const needle = {needle};
  const exact = {str(bool(exact)).lower()};
  const anchors = Array.from(document.querySelectorAll('a[href], button, [role="button"]'));
  const normalize = s => (s || '').replace(/\\s+/g, ' ').trim();
  const match = anchors.find(el => {{
    const txt = normalize(el.innerText || el.textContent || '');
    if (!txt) return false;
    return exact ? txt === needle : txt.toLowerCase().includes(needle.toLowerCase());
  }});
  if (!match) return {{clicked:false, reason:'No matching link/button found'}};
  const info = {{
    text: normalize(match.innerText || match.textContent || ''),
    href: match.href || null,
    tagName: match.tagName,
  }};
  match.click();
  return {{clicked:true, element:info}};
}})())
""".strip()
    payload = _eval_json_on_target(ws_url, expression)
    time.sleep(wait_seconds)
    page = _eval_json_on_target(
        ws_url,
        "JSON.stringify({title: document.title, url: location.href, readyState: document.readyState})",
    )
    return {
        "success": bool(payload and payload.get("clicked")),
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "click": payload,
        "page_after": page,
    }


def android_browser_click_selector(
    selector: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    wait_seconds: float = 1.0,
) -> dict[str, Any]:
    if not selector.strip():
        raise ValueError("selector is required")
    target, ws_url = _resolve_target(
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    selector_js = json.dumps(selector)
    expression = f"""
JSON.stringify((() => {{
  const selector = {selector_js};
  const el = document.querySelector(selector);
  if (!el) return {{clicked:false, reason:'Selector not found', selector}};
  const info = {{
    selector,
    tagName: el.tagName,
    text: (el.innerText || el.textContent || '').trim().slice(0, 500)
  }};
  el.click();
  return {{clicked:true, element:info}};
}})())
""".strip()
    payload = _eval_json_on_target(ws_url, expression)
    time.sleep(wait_seconds)
    page = _eval_json_on_target(
        ws_url,
        "JSON.stringify({title: document.title, url: location.href, readyState: document.readyState})",
    )
    return {
        "success": bool(payload and payload.get("clicked")),
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "click": payload,
        "page_after": page,
    }


def android_browser_fill_input(
    selector: str,
    value: str,
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    submit: bool = False,
) -> dict[str, Any]:
    if not selector.strip():
        raise ValueError("selector is required")
    target, ws_url = _resolve_target(
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    selector_js = json.dumps(selector)
    value_js = json.dumps(value)
    expression = f"""
JSON.stringify((() => {{
  const selector = {selector_js};
  const value = {value_js};
  const submit = {str(bool(submit)).lower()};
  const el = document.querySelector(selector);
  if (!el) return {{filled:false, reason:'Selector not found', selector}};
  el.focus();
  el.value = value;
  el.dispatchEvent(new Event('input', {{bubbles:true}}));
  el.dispatchEvent(new Event('change', {{bubbles:true}}));
  if (submit) {{
    const form = el.form;
    if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
  }}
  return {{
    filled:true,
    selector,
    tagName: el.tagName,
    type: el.type || null,
    valueLength: (el.value || '').length,
    submitted: submit
  }};
}})())
""".strip()
    payload = _eval_json_on_target(ws_url, expression)
    return {
        "success": bool(payload and payload.get("filled")),
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "fill": payload,
    }


def android_browser_take_screenshot(
    target_id: str = "",
    url_contains: str = "",
    title_contains: str = "",
    local_port: int = DEFAULT_PORT,
    format: str = "png",
    quality: int = 90,
    artifact_name: str = "android_browser_screenshot",
) -> dict[str, Any]:
    image_format = format.strip().lower()
    if image_format not in {"png", "jpeg"}:
        raise ValueError("format must be png or jpeg")
    target, ws_url = _resolve_target(
        target_id=target_id,
        url_contains=url_contains,
        title_contains=title_contains,
        local_port=local_port,
    )
    _cdp_call(ws_url, "Page.enable")
    params: dict[str, Any] = {"format": image_format, "fromSurface": True}
    if image_format == "jpeg":
        params["quality"] = max(1, min(int(quality), 100))
    result = _cdp_call(ws_url, "Page.captureScreenshot", params)
    data = result.get("data")
    if not data:
        raise CDPError("Page.captureScreenshot returned no image data")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "jpg" if image_format == "jpeg" else image_format
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    file_path = OUTPUT_DIR / f"{artifact_name}_{timestamp}.{suffix}"
    file_path.write_bytes(base64.b64decode(data))
    return {
        "success": True,
        "target": {
            "id": target.get("id"),
            "title": target.get("title"),
            "url": target.get("url"),
        },
        "format": image_format,
        "file_path": str(file_path),
        "bytes_written": file_path.stat().st_size,
    }
