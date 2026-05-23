import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List


class ToolRouter:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = (self.workspace_root / p).resolve()
        return p

    def run_shell(self, command: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.workspace_root),
            )
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        try:
            p = self._resolve_path(path)
            if not p.exists() or not p.is_dir():
                return {"success": False, "error": f"directory not found: {path}"}
            items: List[str] = []
            for child in sorted(p.iterdir()):
                kind = "d" if child.is_dir() else "f"
                items.append(f"{kind} {child.name}")
            return {"success": True, "output": "\n".join(items)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def read_file(self, path: str) -> Dict[str, Any]:
        try:
            p = self._resolve_path(path)
            if not p.exists() or not p.is_file():
                return {"success": False, "error": f"file not found: {path}"}
            return {"success": True, "output": p.read_text(encoding="utf-8")}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def write_file(self, path: str, content: str) -> Dict[str, Any]:
        try:
            p = self._resolve_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "output": f"wrote {p}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def search_code(self, pattern: str, path: str = ".") -> Dict[str, Any]:
        target = self._resolve_path(path)
        try:
            cmd = ["rg", "-n", "--hidden", "--glob", "!.git", pattern, str(target)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode in (0, 1):
                return {"success": True, "output": result.stdout.strip()}
            return {"success": False, "error": result.stderr.strip()}
        except FileNotFoundError:
            return {"success": False, "error": "rg is not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def capabilities(self) -> Dict[str, Any]:
        browser_use_repo = self.workspace_root / "integrations" / "browser-use"
        return {
            "success": True,
            "output": {
                "workspace_root": str(self.workspace_root),
                "tools": ["shell", "list_dir", "read_file", "write_file", "search_code"],
                "browser_use_repo_present": browser_use_repo.exists(),
            },
        }
