import json
from pathlib import Path

from dotenv import load_dotenv

from config import load_settings
from memory_store import MemoryStore
from mcp_registry import MCPRegistry
from orchestrator import UnifiedOrchestrator
from policy import SafetyPolicy
from provider_adapter import OllamaCloudAdapter
from runtime_logger import setup_runtime_logger
from tool_router import ToolRouter


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)


def _confirm_command(command: str, reason: str) -> bool:
    print(f"\n[approval required] {reason}")
    print(f"command: {command}")
    answer = input("approve? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}


def _print_status(settings, mcp: MCPRegistry, tools: ToolRouter) -> None:
    print("\n=== System Status ===")
    print(f"Provider: {settings.provider}")
    print(f"Model: {settings.default_model}")
    print(f"Endpoint: {settings.ollama_base_url}{settings.ollama_chat_path}")
    print(f"Approval mode: {settings.approval_mode}")
    print(f"Max steps: {settings.max_steps}")
    print(f"MCP enabled: {settings.mcp_enabled}")
    print(mcp.summary())
    print(f"Capabilities: {json.dumps(tools.capabilities().get('output', {}), indent=2)}")


def _derive_project_dir_from_steps(steps):
    written = []
    for s in steps:
        if s.get("type") == "tool" and s.get("tool") == "write_file":
            path = str((s.get("args") or {}).get("path", "")).strip()
            if path:
                written.append(path)
    if not written:
        return "", []
    parents = [str(Path(p).parent) for p in written]
    # Pick shortest parent as likely project root for modular generated projects.
    project_dir = min(parents, key=len) if parents else ""
    return project_dir, written


def run() -> None:
    _load_env()
    settings = load_settings()
    runtime_logger = setup_runtime_logger(
        log_dir=Path(settings.workspace_root) / "logs",
        level="INFO",
    )

    if not settings.ollama_api_key:
        raise RuntimeError("Set OLLAMA_API_KEY in system_builder/.env")

    workspace_root = Path(settings.workspace_root)
    llm = OllamaCloudAdapter()
    tools = ToolRouter(
        workspace_root=workspace_root,
        file_scope_mode=settings.file_scope_mode,
        operation_root=Path(settings.operation_root),
    )
    policy = SafetyPolicy(approval_mode=settings.approval_mode)
    orchestrator = UnifiedOrchestrator(
        llm=llm,
        tools=tools,
        policy=policy,
        max_steps=settings.max_steps,
        logger=runtime_logger,
    )

    mcp = MCPRegistry(settings.mcp_config_path)
    if settings.mcp_enabled:
        mcp.load()

    memory = MemoryStore(workspace_root / ".assistant_memory.json")
    memory.load()

    print("Unified Live Assistant ready.")
    print("Commands: :status, :history, :capabilities, :exit")
    print(f"Live logs: {Path(settings.workspace_root) / 'logs' / 'runtime.log'}")

    history = memory.get_recent_history(limit=200)
    while True:
        user_input = input("\nGoal> ").strip()
        if not user_input:
            continue
        runtime_logger.info("input_received | input=%s", user_input)
        if user_input in {":exit", "exit", "quit"}:
            runtime_logger.info("session_stopped")
            print("Stopping.")
            break
        if user_input == ":status":
            _print_status(settings, mcp, tools)
            continue
        if user_input == ":history":
            print(json.dumps(history[-5:], indent=2))
            continue
        if user_input == ":capabilities":
            print(json.dumps(tools.capabilities(), indent=2))
            continue

        runtime_context = {
            "last_project_dir": memory.data.get("last_project_dir", ""),
            "last_written_files": memory.data.get("last_written_files", []),
            "last_shell_command": memory.data.get("last_shell_command", ""),
        }
        runtime_logger.info(
            "context_snapshot | last_project_dir=%s | last_shell_command=%s | last_written_files_count=%s",
            runtime_context["last_project_dir"],
            runtime_context["last_shell_command"],
            len(runtime_context["last_written_files"]),
        )
        state = orchestrator.run_goal(user_input, _confirm_command, context=runtime_context)
        history_item = {"goal": user_input, "final_answer": state.final_answer, "steps": state.steps}
        history.append(history_item)
        memory.append_history(history_item)
        runtime_logger.info("goal_finished | goal=%s | finished=%s", user_input, state.finished)

        project_dir, written_files = _derive_project_dir_from_steps(state.steps)
        if project_dir:
            memory.data["last_project_dir"] = project_dir
        if written_files:
            memory.data["last_written_files"] = written_files
        for s in reversed(state.steps):
            if s.get("type") == "tool" and s.get("tool") == "shell":
                cmd = str((s.get("args") or {}).get("command", "")).strip()
                if cmd:
                    memory.data["last_shell_command"] = cmd
                    break
        memory.save()
        runtime_logger.info("final_answer | content=%s", state.final_answer[:1200])
        runtime_logger.info(
            "memory_updated | last_project_dir=%s | last_shell_command=%s | last_written_files_count=%s",
            memory.data.get("last_project_dir", ""),
            memory.data.get("last_shell_command", ""),
            len(memory.data.get("last_written_files", [])),
        )

        print("\n=== Final Answer ===")
        print(state.final_answer)
        print("\n=== Steps ===")
        for s in state.steps:
            if s.get("type") == "tool":
                tool = s.get("tool")
                ok = s.get("result", {}).get("success")
                print(f"- step {s.get('step')}: tool={tool} success={ok}")
                if not ok:
                    err = s.get("result", {}).get("error") or s.get("result", {}).get("stderr", "")
                    if err:
                        print(f"  error: {str(err)[:300]}")
            elif s.get("type") == "model_error":
                print(f"- step {s.get('step')}: model_error")
                print(f"  error: {str(s.get('error', ''))[:300]}")
            elif s.get("type") == "answer":
                mode = s.get("mode", "plan")
                print(f"- step {s.get('step')}: answer (mode={mode})")
            else:
                print(f"- step {s.get('step')}: {s.get('type')}")


if __name__ == "__main__":
    run()
