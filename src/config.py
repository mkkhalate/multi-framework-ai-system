import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    provider: str
    default_model: str
    ollama_base_url: str
    ollama_chat_path: str
    ollama_api_key: str
    max_steps: int
    mcp_enabled: bool
    mcp_config_path: Path
    approval_mode: str
    workspace_root: str
    file_scope_mode: str
    operation_root: str


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    return Settings(
        provider=os.getenv("MODEL_PROVIDER", "ollama"),
        default_model=os.getenv("DEFAULT_MODEL", os.getenv("OLLAMA_MODEL", "qwen3:32b")),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api"),
        ollama_chat_path=os.getenv("OLLAMA_CHAT_PATH", "/v1/chat/completions"),
        ollama_api_key=os.getenv("OLLAMA_API_KEY", ""),
        max_steps=int(os.getenv("AGENT_MAX_STEPS", "8")),
        mcp_enabled=_to_bool(os.getenv("MCP_ENABLED", "true")),
        mcp_config_path=Path(os.getenv("MCP_CONFIG_PATH", "./config/mcp_servers.json")),
        approval_mode=os.getenv("MCP_APPROVAL_MODE", "ask").strip().lower(),
        workspace_root=os.getenv("WORKSPACE_ROOT", "."),
        file_scope_mode=os.getenv("FILE_SCOPE_MODE", "workspace").strip().lower(),
        operation_root=os.getenv("OPERATION_ROOT", os.getenv("WORKSPACE_ROOT", ".")),
    )
