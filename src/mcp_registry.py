import json
from pathlib import Path
from typing import Any, Dict, List


class MCPRegistry:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.servers: List[Dict[str, Any]] = []

    def load(self) -> None:
        if not self.config_path.exists():
            self.servers = []
            return

        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        servers = raw.get("servers", [])
        if not isinstance(servers, list):
            self.servers = []
            return
        self.servers = [s for s in servers if isinstance(s, dict)]

    def as_dict(self) -> Dict[str, Any]:
        return {"count": len(self.servers), "servers": self.servers}

    def summary(self) -> str:
        if not self.servers:
            return "MCP: no servers configured"

        lines = ["MCP servers:"]
        for s in self.servers:
            name = s.get("name", "unknown")
            transport = s.get("transport", "unknown")
            command = s.get("command", "")
            args = " ".join(s.get("args", [])) if isinstance(s.get("args"), list) else ""
            lines.append(f"- {name} ({transport}) -> {command} {args}".strip())
        return "\n".join(lines)
