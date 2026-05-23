import subprocess
from pathlib import Path
from typing import Any, Dict, List
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup


class ToolRouter:
    def __init__(self, workspace_root: Path, file_scope_mode: str = "workspace", operation_root: Path | None = None) -> None:
        self.workspace_root = workspace_root.resolve()
        self.file_scope_mode = file_scope_mode
        self.operation_root = (operation_root or workspace_root).resolve()

    def _resolve_path(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            if self.file_scope_mode == "home":
                p = (Path.home() / p).resolve()
            elif self.file_scope_mode == "system":
                p = (self.operation_root / p).resolve()
            else:
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
            max_chars = 6000
            stdout = (result.stdout or "")
            stderr = (result.stderr or "")
            if len(stdout) > max_chars:
                stdout = stdout[:max_chars] + "...<truncated>"
            if len(stderr) > max_chars:
                stderr = stderr[:max_chars] + "...<truncated>"
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
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

    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        try:
            if not query.strip():
                return {"success": False, "error": "empty query"}
            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    if not isinstance(item, dict):
                        continue
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", ""),
                        }
                    )
            return {"success": True, "output": results}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def fetch_url(self, url: str, max_chars: int = 8000) -> Dict[str, Any]:
        try:
            if not url.startswith(("http://", "https://")):
                return {"success": False, "error": "url must start with http:// or https://"}

            resp = requests.get(
                url,
                timeout=25,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Safari/537.36"
                    )
                },
            )
            resp.raise_for_status()

            content_type = (resp.headers.get("content-type") or "").lower()
            raw_text = ""
            title = ""

            if "text/html" in content_type or "<html" in resp.text.lower():
                soup = BeautifulSoup(resp.text, "html.parser")
                if soup.title and soup.title.string:
                    title = soup.title.string.strip()
                # Remove noisy tags before text extraction.
                for tag in soup(["script", "style", "noscript", "svg", "header", "footer"]):
                    tag.extract()
                raw_text = " ".join(soup.get_text(separator=" ").split())
            else:
                raw_text = resp.text

            extracted = raw_text[:max_chars]
            return {
                "success": True,
                "output": {
                    "url": url,
                    "status_code": resp.status_code,
                    "content_type": content_type,
                    "title": title,
                    "text": extracted,
                    "truncated": len(raw_text) > max_chars,
                    "total_chars": len(raw_text),
                },
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def reply(self, text: str) -> Dict[str, Any]:
        try:
            message = str(text).strip()
            if not message:
                return {"success": False, "error": "reply text is empty"}
            return {"success": True, "output": message}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def capabilities(self) -> Dict[str, Any]:
        browser_use_repo = self.workspace_root / "integrations" / "browser-use"
        return {
            "success": True,
            "output": {
                "workspace_root": str(self.workspace_root),
                "file_scope_mode": self.file_scope_mode,
                "operation_root": str(self.operation_root),
                "tools": [
                    "shell",
                    "list_dir",
                    "read_file",
                    "write_file",
                    "search_code",
                    "web_search",
                    "fetch_url",
                    "reply",
                ],
                "browser_use_repo_present": browser_use_repo.exists(),
            },
        }
