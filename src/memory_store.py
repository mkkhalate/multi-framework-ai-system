import json
from pathlib import Path
from typing import Any, Dict, List


class MemoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: Dict[str, Any] = {
            "history": [],
            "last_project_dir": "",
            "last_written_files": [],
            "last_shell_command": "",
        }

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                self.data.update(raw)
        except Exception:
            # Keep default structure on corrupted memory file.
            return

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def append_history(self, item: Dict[str, Any], max_items: int = 300) -> None:
        hist = self.data.setdefault("history", [])
        hist.append(item)
        if len(hist) > max_items:
            self.data["history"] = hist[-max_items:]

    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        hist = self.data.get("history", [])
        if not isinstance(hist, list):
            return []
        return hist[-limit:]

