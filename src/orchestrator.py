import json
import logging
import os
import platform
import sys
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from policy import SafetyPolicy
from provider_adapter import OllamaCloudAdapter
from tool_router import ToolRouter


@dataclass
class AgentState:
    goal: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    finished: bool = False
    final_answer: str = ""


class UnifiedOrchestrator:
    def __init__(
        self,
        llm: OllamaCloudAdapter,
        tools: ToolRouter,
        policy: SafetyPolicy,
        max_steps: int = 8,
        logger: logging.Logger | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.policy = policy
        self.max_steps = max_steps
        self.logger = logger

    def _clip(self, value: Any, limit: int = 400) -> str:
        text = str(value)
        if len(text) <= limit:
            return text
        return text[:limit] + "...<truncated>"

    def _system_prompt(self, current_time_iso: str) -> str:
        os_name = platform.system()
        kernel = platform.release()
        machine = platform.machine()
        python_version = sys.version.split()[0]
        shell = os.environ.get("SHELL", "unknown")
        distro = "unknown"
        try:
            if os_name.lower() == "linux" and os.path.exists("/etc/os-release"):
                with open("/etc/os-release", "r", encoding="utf-8") as f:
                    content = f.read()
                for line in content.splitlines():
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            distro = "unknown"

        return (
            "You are an autonomous system assistant. Return JSON only.\n"
            f"Current local time (ISO): {current_time_iso}\n"
            f"System details: os={os_name}, distro={distro}, kernel={kernel}, arch={machine}, python={python_version}, shell={shell}\n"
            "Action schema:\n"
            "{\"type\":\"answer\",\"content\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"shell\",\"args\":{\"command\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"list_dir\",\"args\":{\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"read_file\",\"args\":{\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"write_file\",\"args\":{\"path\":\"...\",\"content\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"search_code\",\"args\":{\"pattern\":\"...\",\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"web_search\",\"args\":{\"query\":\"...\",\"max_results\":5},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"fetch_url\",\"args\":{\"url\":\"...\",\"max_chars\":8000},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"reply\",\"args\":{\"text\":\"...\",\"await_user\":false},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"capabilities\",\"args\":{},\"reason\":\"...\"}\n"
            "Rules: use tools when needed, then finish with type=answer.\n"
            "If the user asks to inspect files/directories/code, DO NOT answer directly first.\n"
            "Run a relevant tool action before answering.\n"
            "For time-sensitive or 'current/latest/today/now' questions, use the current local time provided above and web_search when needed.\n"
            "When web_search returns URLs, use fetch_url on relevant URLs before writing final conclusions.\n"
            "Do not respond with capability disclaimers like 'I can't do this' without attempting at least one actionable tool or shell step first.\n"
            "Use system-appropriate commands and package managers based on system details (e.g., avoid apt on Arch Linux)."
            "Use reply tool when you want to explicitly ask the user a confirmation/question or return a direct interactive message."
        )

    def _looks_like_capability_refusal(self, text: str) -> bool:
        t = text.lower()
        markers = [
            "i can't",
            "i cannot",
            "i do not have",
            "as an ai",
            "i'm unable to",
        ]
        return any(m in t for m in markers)

    def _extract_json(self, text: str) -> Dict[str, Any]:
        content = text.strip()
        if content.startswith("```"):
            parts = content.split("```")
            if len(parts) >= 2:
                block = parts[1]
                if block.startswith("json"):
                    block = block[4:]
                content = block.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Best-effort extraction when model wraps JSON with extra prose.
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(content[start : end + 1])
            raise

    def _run_tool(
        self,
        tool_name: str,
        args: Dict[str, Any],
        confirm_callback: Callable[[str, str], bool],
    ) -> Dict[str, Any]:
        if tool_name == "shell":
            command = str(args.get("command", ""))
            decision = self.policy.evaluate_shell(command)
            if not decision.allow:
                return {"success": False, "error": decision.reason}
            if decision.needs_confirmation and not confirm_callback(command, decision.reason):
                return {"success": False, "error": "denied by user"}
            return self.tools.run_shell(command)

        if tool_name == "list_dir":
            return self.tools.list_dir(str(args.get("path", ".")))
        if tool_name == "read_file":
            return self.tools.read_file(str(args.get("path", "")))
        if tool_name == "write_file":
            return self.tools.write_file(str(args.get("path", "")), str(args.get("content", "")))
        if tool_name == "search_code":
            return self.tools.search_code(str(args.get("pattern", "")), str(args.get("path", ".")))
        if tool_name == "web_search":
            return self.tools.web_search(
                str(args.get("query", "")),
                int(args.get("max_results", 5)),
            )
        if tool_name == "fetch_url":
            return self.tools.fetch_url(
                str(args.get("url", "")),
                int(args.get("max_chars", 8000)),
            )
        if tool_name == "reply":
            return self.tools.reply(str(args.get("text", "")))
        if tool_name == "capabilities":
            return self.tools.capabilities()
        return {"success": False, "error": f"unknown tool: {tool_name}"}

    def run_goal(
        self,
        goal: str,
        confirm_callback: Callable[[str, str], bool],
        ask_user_callback: Optional[Callable[[str], str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AgentState:
        state = AgentState(goal=goal)
        if self.logger:
            self.logger.info("goal_received | goal=%s", goal)
        if self.logger:
            self.logger.info("mode_selected | mode=plan")

        for step_idx in range(1, self.max_steps + 1):
            current_time_iso = datetime.now().astimezone().isoformat()
            if self.logger:
                self.logger.info("plan_step_start | step=%s", step_idx)
            messages = [
                {"role": "system", "content": self._system_prompt(current_time_iso)},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\n"
                        f"Context: {json.dumps(context or {}, ensure_ascii=True)}\n"
                        f"Previous steps JSON: {json.dumps(state.steps, ensure_ascii=True)}"
                    ),
                },
            ]

            try:
                model_out = self.llm.chat(messages)
                if self.logger:
                    self.logger.info("model_raw_content | step=%s | content=%s", step_idx, self._clip(model_out.get("content", ""), 1400))
                action = self._extract_json(model_out["content"])
                if self.logger:
                    self.logger.info(
                        "plan_step_action | step=%s | action_type=%s | action=%s",
                        step_idx,
                        action.get("type"),
                        self._clip(json.dumps(action, ensure_ascii=True), 1400),
                    )
            except Exception as exc:
                err = str(exc)
                state.steps.append(
                    {
                        "step": step_idx,
                        "type": "model_error",
                        "error": err,
                    }
                )
                # Fatal provider/config errors should not consume all remaining steps.
                if "provider_http_error status=401" in err or "provider_http_error status=403" in err:
                    break
                if "provider_error no candidate endpoint succeeded" in err:
                    break
                if "model" in err and "not found" in err:
                    break
                continue

            action_type = action.get("type")
            if action_type == "answer":
                state.finished = True
                state.final_answer = str(action.get("content", ""))
                state.steps.append({"step": step_idx, "type": "answer", "content": state.final_answer})
                break

            if action_type != "tool":
                state.steps.append({"step": step_idx, "type": "invalid_action", "raw": action})
                continue

            tool_name = str(action.get("tool", ""))
            args = action.get("args", {})
            if not isinstance(args, dict):
                args = {}

            result = self._run_tool(tool_name, args, confirm_callback)
            if self.logger:
                self.logger.info(
                    "tool_executed | step=%s | tool=%s | args=%s | success=%s | result=%s",
                    step_idx,
                    tool_name,
                    self._clip(json.dumps(args, ensure_ascii=True), 1200),
                    result.get("success"),
                    self._clip(json.dumps(result, ensure_ascii=True), 1400),
                )
            state.steps.append(
                {
                    "step": step_idx,
                    "type": "tool",
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                }
            )

            if tool_name == "reply" and result.get("success"):
                reply_text = str(result.get("output", "")).strip()
                await_user = bool(args.get("await_user", False))
                if await_user and ask_user_callback is not None:
                    user_feedback = ask_user_callback(reply_text)
                    state.steps.append(
                        {
                            "step": step_idx,
                            "type": "user_input",
                            "prompt": reply_text,
                            "response": user_feedback,
                        }
                    )
                    if self.logger:
                        self.logger.info(
                            "reply_interaction | prompt=%s | user_response=%s",
                            self._clip(reply_text, 600),
                            self._clip(user_feedback, 600),
                        )
                    # Continue planning with this new user input embedded in steps context.
                    continue

                state.final_answer = reply_text
                state.finished = True
                if self.logger:
                    self.logger.info("goal_completed | mode=reply_tool | final_answer=%s", self._clip(state.final_answer, 1200))
                break

        if not state.finished:
            state.final_answer = (
                "I could not complete the task within the configured step budget. "
                "Try a more specific goal or increase AGENT_MAX_STEPS."
            )
            if self.logger:
                self.logger.warning("goal_incomplete | goal=%s", goal)
        elif self.logger:
            self.logger.info("goal_completed | mode=plan | final_answer=%s", self._clip(state.final_answer, 1200))
        return state
