import json
from pathlib import Path

from dotenv import load_dotenv

from config import load_settings
from mcp_registry import MCPRegistry
from orchestrator import UnifiedOrchestrator
from policy import SafetyPolicy
from provider_adapter import OllamaCloudAdapter
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


def run() -> None:
    _load_env()
    settings = load_settings()

    if not settings.ollama_api_key:
        raise RuntimeError("Set OLLAMA_API_KEY in system_builder/.env")

    workspace_root = Path(settings.workspace_root)
    llm = OllamaCloudAdapter()
    tools = ToolRouter(workspace_root=workspace_root)
    policy = SafetyPolicy(approval_mode=settings.approval_mode)
    orchestrator = UnifiedOrchestrator(
        llm=llm,
        tools=tools,
        policy=policy,
        max_steps=settings.max_steps,
    )

    mcp = MCPRegistry(settings.mcp_config_path)
    if settings.mcp_enabled:
        mcp.load()

    print("Unified Live Assistant ready.")
    print("Commands: :status, :history, :capabilities, :exit")

    history = []
    while True:
        user_input = input("\nGoal> ").strip()
        if not user_input:
            continue
        if user_input in {":exit", "exit", "quit"}:
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

        state = orchestrator.run_goal(user_input, _confirm_command)
        history.append({"goal": user_input, "final_answer": state.final_answer, "steps": state.steps})

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
