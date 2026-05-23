import os
from typing import Any, Dict, List

import requests


class OllamaCloudAdapter:
    def __init__(self) -> None:
        self.base_url = os.getenv("OLLAMA_BASE_URL", "https://ollama.com/api").rstrip("/")
        self.api_key = os.getenv("OLLAMA_API_KEY", "")
        self.model = os.getenv("DEFAULT_MODEL") or os.getenv("OLLAMA_MODEL", "qwen3:32b")
        self.chat_path = os.getenv("OLLAMA_CHAT_PATH", "/v1/chat/completions")
        self.timeout = int(os.getenv("PROVIDER_TIMEOUT_SECONDS", "120"))

    def _build_candidate_urls(self) -> List[str]:
        base = self.base_url.rstrip("/")
        chat_path = self.chat_path if self.chat_path.startswith("/") else f"/{self.chat_path}"

        # Normalize duplicate "/api/api/..." when users provide both:
        # base=".../api" and chat_path="/api/..."
        if base.endswith("/api") and chat_path.startswith("/api/"):
            chat_path = chat_path[len("/api") :]

        candidates: List[str] = [f"{base}{chat_path}"]

        # Canonical native endpoint from docs:
        # - local base http://localhost:11434/api + /chat
        # - cloud base https://ollama.com/api + /chat
        if base.endswith("/api"):
            candidates.append(f"{base}/chat")
            root = base[: -len("/api")]
            candidates.append(f"{root}/api/chat")
            # OpenAI-compatible endpoint from docs.
            candidates.append(f"{root}/v1/chat/completions")
        elif base.endswith("/v1"):
            candidates.append(f"{base}/chat/completions")
            root = base[: -len("/v1")]
            candidates.append(f"{root}/api/chat")
        else:
            candidates.append(f"{base}/api/chat")
            candidates.append(f"{base}/v1/chat/completions")

        # De-duplicate while preserving order.
        seen = set()
        ordered: List[str] = []
        for url in candidates:
            if url not in seen:
                seen.add(url)
                ordered.append(url)
        return ordered

    def _extract_content(self, data: Dict[str, Any]) -> str:
        # OpenAI-compatible format
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            if isinstance(content, str):
                return content

        # Ollama native format
        msg = data.get("message")
        if isinstance(msg, dict):
            content = msg.get("content", "")
            if isinstance(content, str):
                return content

        # Fallback
        return str(data)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OLLAMA_API_KEY is missing in environment")

        urls = self._build_candidate_urls()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error = ""
        for url in urls:
            # Ollama-native endpoints expect stream flag.
            if url.endswith("/api/chat") or url.endswith("/chat"):
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                }
            else:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                try:
                    data = resp.json()
                except Exception as exc:
                    raise RuntimeError(f"provider_invalid_json url={url} body={resp.text[:800]}") from exc
                return {
                    "content": self._extract_content(data),
                    "raw": data,
                }
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", "unknown")
                body = ""
                try:
                    body = exc.response.text[:500]
                except Exception:
                    body = ""
                last_error = f"provider_http_error status={status} url={url} body={body}"
                # Try next candidate for endpoint-shape mismatches.
                if status in (404, 405):
                    continue
                raise RuntimeError(last_error) from exc
            except requests.RequestException as exc:
                last_error = f"provider_request_error url={url} err={exc}"
                continue

        raise RuntimeError(last_error or "provider_error no candidate endpoint succeeded")
