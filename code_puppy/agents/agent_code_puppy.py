"""Code-Puppy - The default code generation agent."""

from code_puppy.config import get_owner_name, get_puppy_name

from .base_agent import BaseAgent


class CodePuppyAgent(BaseAgent):
    """Code-Puppy - The default loyal digital puppy code agent."""

    @property
    def name(self) -> str:
        return "code-puppy"

    @property
    def display_name(self) -> str:
        return "Code-Puppy 🐶"

    @property
    def description(self) -> str:
        return "The most loyal digital puppy, helping with all coding tasks"

    def get_available_tools(self) -> list[str]:
        """Get the list of tools available to Code-Puppy."""
        return [
            "list_agents",
            "invoke_agent",
            "list_files",
            "read_file",
            "grep",
            "create_file",
            "replace_in_file",
            "delete_snippet",
            "delete_file",
            "agent_run_shell_command",
            "ask_user_question",
            "activate_skill",
            "list_or_search_skills",
            "load_image_for_analysis",
            "android_app_inventory_doctor",
            "android_app_inventory_list",
            "android_app_profile",
            "android_app_stack_report_doctor",
            "android_app_stack_report_generate",
            "android_app_stack_report_examples",
            "android_app_workflow_doctor",
            "android_app_workflow_list",
            "android_app_workflow_run",
            "android_brave_status",
            "android_browser_open_url",
            "android_browser_click_link_by_text",
            "android_browser_click_selector",
            "android_browser_fill_input",
            "android_browser_take_screenshot",
            "android_browser_read_page",
            "android_browser_get_html",
            "android_browser_list_links",
            "android_browser_get_text_by_selector",
            "android_bugreport_doctor",
            "android_bugreport_collect",
            "android_business_workflow_capture_doctor",
            "android_business_workflow_capture_template",
            "android_business_workflow_capture_create",
            "android_business_workflow_capture_examples",
            "android_cdp_doctor",
            "android_adb_wireless_helper",
            "android_cdp_probe",
            "android_cdp_list_targets",
            "android_cdp_get_page_info",
            "android_cdp_navigate",
            "android_cdp_eval_js",
            "android_dumpsys_doctor",
            "android_dumpsys_service",
            "android_dumpsys_snapshot",
            "android_edge_test_element",
            "android_edge_assert_text",
            "android_open",
            "android_list_shortcuts",
            "android_handoff_doctor",
            "android_handoff_text",
            "android_handoff_url",
            "android_handoff_file",
            "android_handoff_examples",
            "android_input_doctor",
            "android_input_tap",
            "android_input_tap_bounds",
            "android_input_swipe",
            "android_input_text",
            "android_input_keyevent",
            "android_intent_audit_doctor",
            "android_intent_audit_app",
            "android_intent_audit_stack",
            "android_intent_audit_examples",
            "android_intent_doctor",
            "android_intent_build",
            "android_intent_send",
            "android_intent_examples",
            "android_logcat_doctor",
            "android_logcat_recent",
            "android_logcat_clear",
            "android_notification_doctor",
            "android_open_notification_settings",
            "android_notification_setup_guide",
            "android_notification_send",
            "android_orchestration_blueprint_doctor",
            "android_orchestration_blueprint_plan",
            "android_orchestration_blueprint_examples",
            "android_process_doctor",
            "android_process_list",
            "android_top_snapshot",
            "android_reconnect_doctor",
            "android_reconnect_plan",
            "android_reconnect_quick",
            "android_reconnect_full",
            "android_screen_capture_doctor",
            "android_capture_screenshot",
            "android_record_screen",
            "android_setup_doctor",
            "android_setup_next_steps",
            "android_first_run_tour",
            "android_support_bundle_doctor",
            "android_support_bundle_plan",
            "android_support_bundle_collect",
            "android_support_bundle_list",
            "android_support_bundle_summarize",
            "android_support_issue_draft",
            "android_support_share_wizard",
            "android_ui_action_doctor",
            "android_ui_tap_match",
            "android_ui_text_into_match",
            "android_ui_capability_audit_doctor",
            "android_ui_capability_audit_app",
            "android_ui_capability_audit_stack",
            "android_ui_capability_audit_examples",
            "android_ui_dump_doctor",
            "android_ui_dump_hierarchy",
            "android_ui_dump_find",
            "android_utility_doctor",
            "android_open_settings",
            "android_launch_app",
            "android_share_text",
            "android_find_apps",
            "android_workflow_feasibility_doctor",
            "android_workflow_feasibility_assess",
            "android_workflow_feasibility_examples",
            "android_workflow_doctor",
            "android_workflow_list",
            "android_workflow_run",
            "droidpuppy_doctor",
        ]

    def _get_reasoning_prompt_sections(self) -> dict[str, str]:
        """Return prompt sections describing the expected think-act loop."""
        return {
            "pre_tool_rule": (
                "- Before major tool use, think through your approach "
                "and planned next steps"
            ),
            "loop_rule": (
                "- You're encouraged to loop between reasoning, file "
                "tools, and run_shell_command to test output in order "
                "to write programs"
            ),
        }

    def get_system_prompt(self) -> str:
        """Get Code-Puppy's full system prompt."""
        puppy_name = get_puppy_name()
        owner_name = get_owner_name()
        r = self._get_reasoning_prompt_sections()

        result = f"""
You are {puppy_name}, the most loyal digital puppy, helping your owner {owner_name} get coding stuff done!
You are a code-agent assistant with the ability to use tools to help users complete coding tasks.
You MUST use the provided tools to write, modify, and execute code rather than just describing what to do.

Be super informal - we're here to have fun. Don't be scared of being a little bit sarcastic too.
Be very pedantic about code principles like DRY, YAGNI, and SOLID.
Be fun and playful. Don't be too serious.

Keep files under 600 lines. If a file grows beyond that, consider splitting into smaller subcomponents—but don't split purely to hit a line count if it hurts cohesion.
Always obey the Zen of Python, even if you are not writing Python code.

If asked about your origins: 'I am {puppy_name}, authored on a rainy weekend in May 2025.
If asked 'what is code puppy': 'I am {puppy_name}! 🐶 A sassy, open-source AI code agent—no bloated IDEs, or closed-source vendor traps needed.'

When given a coding task:
1. Analyze the requirements carefully
2. Execute the plan by using appropriate tools
3. Continue autonomously whenever possible

Important rules:
- You MUST use tools — DO NOT just output code or descriptions
{r["pre_tool_rule"]}
- Explore directories before reading/modifying files
- Read existing files before modifying them
- Prefer replace_in_file over create_file. Keep diffs small (100-300 lines).
{r["loop_rule"]}
- Continue autonomously unless user input is definitively required
"""
        # NOTE: runtime ``load_prompt`` fragments (plugin-injected notes such
        # as environment context, file-permission rules, memory recall, ...)
        # are intentionally NOT appended here — they're injected fresh at
        # runtime by ``BaseAgent.get_full_system_prompt`` so they never get
        # baked into a cloned/persisted agent definition.
        return result
