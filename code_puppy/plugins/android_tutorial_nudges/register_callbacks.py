"""Tutorial nudges that surface the next helpful step after first use."""

from __future__ import annotations

from code_puppy.callbacks import register_callback
from code_puppy.messaging import emit_info

_SEEN_TOOLS: set[str] = set()

_NUDGES = {
    "android_open": "Nice. Next try android_workflow_list or android_setup_next_steps(goal='basics').",
    "android_browser_read_page": "Good — you read a live page. Next try android_browser_list_links or android_browser_get_html.",
    "android_cdp_probe": "CDP probing is a big step. Next try android_cdp_list_targets or android_browser_read_page on a live page.",
    "android_notification_send": "If notifications are missing, run android_notification_setup_guide for the easiest next step.",
    "android_reconnect_doctor": "Great. Next try android_reconnect_plan or android_reconnect_quick with the current Wi-Fi debugging address.",
    "android_ui_dump_hierarchy": "Now that you can see the screen, try android_ui_dump_find or android_ui_tap_match with dry_run=True.",
}


def _post_tool_call(tool_name, tool_args, result, duration_ms, context=None):
    del tool_args, result, duration_ms, context
    if tool_name in _SEEN_TOOLS:
        return None
    _SEEN_TOOLS.add(tool_name)
    message = _NUDGES.get(tool_name)
    if message:
        try:
            emit_info(f"DroidPuppy hint: {message}")
        except Exception:
            print(f"DroidPuppy hint: {message}")
    return None


register_callback("post_tool_call", _post_tool_call)
