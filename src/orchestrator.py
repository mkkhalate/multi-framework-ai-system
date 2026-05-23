import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

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
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.policy = policy
        self.max_steps = max_steps

    def _system_prompt(self) -> str:
        return (
            "You are an autonomous system assistant. Return JSON only.\n"
            "Action schema:\n"
            "{\"type\":\"answer\",\"content\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"shell\",\"args\":{\"command\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"list_dir\",\"args\":{\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"read_file\",\"args\":{\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"write_file\",\"args\":{\"path\":\"...\",\"content\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"search_code\",\"args\":{\"pattern\":\"...\",\"path\":\"...\"},\"reason\":\"...\"}\n"
            "{\"type\":\"tool\",\"tool\":\"capabilities\",\"args\":{},\"reason\":\"...\"}\n"
            "Rules: use tools when needed, then finish with type=answer.\n"
            "If the user asks to inspect files/directories/code, DO NOT answer directly first.\n"
            "Run a relevant tool action before answering."
        )

    def _general_answer_prompt(self) -> str:
        return (
            "You are a helpful assistant for general questions. "
            "Answer clearly and directly. Keep it concise unless detail is requested."
        )

    def _is_general_question(self, goal: str) -> bool:
        g = goal.strip().lower()
        if not g:
            return True
        task_keywords = [
            "list", "dir", "directory", "file", "read", "write", "search", "grep",
            "run", "execute", "install", "create", "delete", "move", "copy",
            "project", "code", "repository", "repo", "test", "build", "deploy",
            "shell", "command", "terminal",
        ]
        return not any(k in g for k in task_keywords)

    def _heuristic_tool_for_goal(self, goal: str) -> Dict[str, Any] | None:
        """
        Deterministic fallback for common local-system intents so the agent
        stays useful even if the model responds too conversationally.
        """
        g = goal.strip().lower()

        # List directory intents.
        if any(k in g for k in ["list dir", "list directory", "show files", "read desktop dir", "ls "]):
            path = "."
            if "desktop" in g:
                path = "/home/mayur/Desktop"
            return {"tool": "list_dir", "args": {"path": path}}

        # Read file intents: "read file X", "open X", "show file X"
        m = re.search(r"(?:read file|open file|show file|read)\s+(.+)$", g)
        if m:
            raw = m.group(1).strip()
            # keep it simple; do not over-normalize user path
            return {"tool": "read_file", "args": {"path": raw}}

        # Code search intents
        m = re.search(r"(?:search code|find in code|grep)\s+(.+)$", g)
        if m:
            return {"tool": "search_code", "args": {"pattern": m.group(1).strip(), "path": "."}}

        return None

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
        if tool_name == "capabilities":
            return self.tools.capabilities()
        return {"success": False, "error": f"unknown tool: {tool_name}"}

    def run_goal(self, goal: str, confirm_callback: Callable[[str, str], bool]) -> AgentState:
        state = AgentState(goal=goal)

        # Direct conversational path for general questions/chitchat.
        if self._is_general_question(goal):
            try:
                out = self.llm.chat(
                    [
                        {"role": "system", "content": self._general_answer_prompt()},
                        {"role": "user", "content": goal},
                    ]
                )
                state.final_answer = str(out.get("content", "")).strip() or "I do not have an answer right now."
                state.finished = True
                state.steps.append(
                    {
                        "step": 1,
                        "type": "answer",
                        "mode": "general",
                        "content": state.final_answer,
                    }
                )
                return state
            except Exception as exc:
                state.steps.append({"step": 1, "type": "model_error", "error": str(exc)})
                state.final_answer = "I hit an error while answering that question."
                return state

        # First-pass deterministic handling for common local tasks.
        heuristic = self._heuristic_tool_for_goal(goal)
        if heuristic:
            result = self._run_tool(heuristic["tool"], heuristic["args"], confirm_callback)
            state.steps.append(
                {
                    "step": 1,
                    "type": "tool",
                    "tool": heuristic["tool"],
                    "args": heuristic["args"],
                    "result": result,
                }
            )
            if result.get("success"):
                out = result.get("output") or result.get("stdout", "")
                state.final_answer = str(out).strip() or "Done."
            else:
                state.final_answer = f"Tool failed: {result.get('error', 'unknown error')}"
            state.finished = True
            return state

        for step_idx in range(1, self.max_steps + 1):
            messages = [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": (
                        f"Goal: {goal}\n"
                        f"Previous steps JSON: {json.dumps(state.steps, ensure_ascii=True)}"
                    ),
                },
            ]

            try:
                model_out = self.llm.chat(messages)
                action = self._extract_json(model_out["content"])
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
            state.steps.append(
                {
                    "step": step_idx,
                    "type": "tool",
                    "tool": tool_name,
                    "args": args,
                    "result": result,
                }
            )

        if not state.finished:
            state.final_answer = (
                "I could not complete the task within the configured step budget. "
                "Try a more specific goal or increase AGENT_MAX_STEPS."
            )
        return state
