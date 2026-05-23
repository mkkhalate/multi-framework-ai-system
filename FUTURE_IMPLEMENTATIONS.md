# Implementation Status

This document tracks what is already implemented and what remains for the Unified Live Assistant.

## Completed

1. Core Agent Runtime
- Multi-step planning/execution loop using LLM-driven JSON actions.
- Safety policy layer for shell actions (`auto` / `ask` / `block`).
- Runtime settings from `.env` with enforced loading.

2. Local System Tools
- `shell`
- `list_dir`
- `read_file`
- `write_file`
- `search_code`
- `capabilities`

3. Web Discovery + Reading (Free/Open)
- `web_search` (DDGS / DuckDuckGo search backend).
- `fetch_url` (HTTP fetch + HTML content extraction via BeautifulSoup).

4. Interaction + UX
- `reply` tool for direct user interaction.
- `reply` supports interactive mode (`await_user=true`) to ask confirmations/questions and continue execution.
- CLI control commands: `:status`, `:history`, `:capabilities`, `:exit`.

5. Memory + Traceability
- Persistent memory file (`.assistant_memory.json`) for cross-session context.
- Stores history + recent operation context.
- Live runtime logging to console and `logs/runtime.log`.

6. Operational Scope Controls
- Configurable file operation scope:
  - `workspace`
  - `home`
  - `system` (via `OPERATION_ROOT`)

7. Repo Hygiene and Docs
- `.gitignore` for env/secrets/caches/logs/memory/venv and cloned integrations.
- README includes start-to-finish setup and cloning commands.
- Custom license with attribution requirement.

## Remaining

1. Real MCP Execution (not only registry loading)
- Implement active MCP client runtime and actual server tool invocation.
- Route selected assistant actions to MCP servers with fallback behavior.

2. Built-in Camera / Vision Tools
- Add direct tools for webcam capture (`take_selfie`) and image/video input.
- Add face detection and optional face recognition pipeline.
- Add safe/consent-aware handling around camera use.

3. Browser-use as Direct Action Layer
- Wire `browser-use` integration into tool dispatch.
- Add actions like navigate/extract/click/type/submit with structured schemas.

4. Background Daemon / Scheduler / Watchers
- Add long-running mode (`run`/`stop`/`status`) outside interactive shell.
- Add scheduled jobs and file/process watchers.

5. Long-horizon Project Manager
- Task graph model (`todo`, `in_progress`, `blocked`, `done`).
- Checkpoints and resume across sessions.
- Built-in verify/test gates and milestone reports.

6. Stronger Verification Pipeline
- Standard `plan -> execute -> verify -> report`.
- Project-type-aware test/lint strategy.
- Retry + triage playbooks per error class.

7. Advanced Safety/Governance
- Path-level allow/deny matrices.
- Per-tool policy profiles and stronger audit events.
- Sensitive operation confirmation templates.

8. Model Routing and Resilience
- Explicit multi-provider fallback policy.
- Per-task model routing (fast vs deep).
- Health checks and automatic provider failover.

9. Packaging and Reliability
- Better bootstrap/install automation.
- Smoke/integration tests for core flows.
- CI pipeline for lint/type/test/runtime checks.

## More Systems to Evaluate (Open Source)

1. Open Interpreter (computer-use agent patterns)
- Repo: https://github.com/OpenInterpreter/open-interpreter
- Why useful:
  - Strong local computer-action workflow patterns (shell/files/tools).
  - Useful reference for robust “do-anything” orchestration and retries.
- Suggested adoption:
  - Borrow action planning/recovery patterns and tool-sandbox policies.

2. OpenHands (generalist software agent platform)
- Repo: https://github.com/All-Hands-AI/OpenHands
- Why useful:
  - Mature architecture for long-running software tasks and agent sessions.
- Suggested adoption:
  - Reuse ideas for task sessions, checkpoints, and tool protocol boundaries.

3. OpenAdapt (desktop + process automation)
- Repo: https://github.com/OpenAdaptAI/OpenAdapt
- Why useful:
  - Open-source “generative RPA” focused on desktop/web GUI execution.
- Suggested adoption:
  - Evaluate for desktop demonstration/replay and GUI action primitives.

4. Browser-use + Playwright (web action execution)
- Repo: https://github.com/browser-use/browser-use
- Docs: https://playwright.dev/python/docs/intro
- Why useful:
  - Different use than current stack: direct browser action control (navigate/click/type/submit), not just DDGS + fetch_url retrieval.
- Suggested adoption:
  - Integrate as direct tool actions (`browser_open`, `browser_click`, `browser_extract`, `browser_submit`).

5. Screen/OCR Input Stack
- `python-mss`: fast screenshots
- `pyautogui`: mouse/keyboard automation
- `xdotool`/`ydotool` (Linux-native input fallback)
- `pytesseract`: OCR for screen text
- Suggested adoption:
  - Build “read screen + act” pipeline:
    - capture -> OCR -> plan -> mouse/type actions -> verify loop.

## Security Notes for Agentic Desktop/Web Control

1. Prompt injection and unsafe action risk increases with browser + desktop control.
2. Require explicit confirmation for state-changing actions by default.
3. Add allow/deny policies for domains, paths, and command classes.
4. Log all high-risk actions with before/after screenshots when possible.

## Additional Open-Source Options (Expanded)

1. Agent Orchestration Frameworks
- LangGraph: https://github.com/langchain-ai/langgraph
- CrewAI: https://github.com/crewAIInc/crewAI
- LlamaIndex: https://github.com/run-llama/llama_index
- Haystack: https://github.com/deepset-ai/haystack
- Suggested use:
  - Different use than current loop: graph-native branching, durable checkpoints, and advanced workflow replay.
  - Borrow checkpoint, branching, and replay patterns.

2. Desktop GUI Automation Variants
- AutoKey (Linux automation): https://github.com/autokey/autokey
- SikuliX (image-based GUI automation): https://github.com/RaiMan/SikuliX1
- Suggested use:
  - Keep as fallbacks when pyautogui/xdotool reliability is low.

3. OCR and Document Vision (Open Source)
- Tesseract OCR: https://github.com/tesseract-ocr/tesseract
- pytesseract wrapper: https://github.com/madmaze/pytesseract
- EasyOCR: https://github.com/JaidedAI/EasyOCR
- PaddleOCR: https://github.com/PaddlePaddle/PaddleOCR
- Suggested use:
  - Multi-engine OCR fallback chain:
    - Tesseract fast pass -> EasyOCR/PaddleOCR fallback.

4. Computer Vision Perception
- OpenCV: https://github.com/opencv/opencv
- MediaPipe: https://github.com/google-ai-edge/mediapipe
- YOLO (Ultralytics): https://github.com/ultralytics/ultralytics
- Suggested use:
  - Detect UI components, icons, buttons, and dynamic page regions.

5. Face Recognition / Biometrics (Open Source)
- face_recognition (dlib): https://github.com/ageitgey/face_recognition
- DeepFace: https://github.com/serengil/deepface
- InsightFace: https://github.com/deepinsight/insightface
- Suggested use:
  - Optional user identity modules with explicit consent-only mode.

6. Voice Stack (Offline/Open Source)
- Vosk ASR: https://github.com/alphacep/vosk-api
- Whisper.cpp: https://github.com/ggerganov/whisper.cpp
- Piper TTS: https://github.com/rhasspy/piper
- Coqui TTS: https://github.com/coqui-ai/TTS
- openWakeWord: https://github.com/dscripka/openWakeWord
- Suggested use:
  - Full local speech loop:
    - wake word -> STT -> planner -> action -> TTS response.

7. Browser Automation Alternatives
- Playwright Python: https://github.com/microsoft/playwright-python
- Selenium: https://github.com/SeleniumHQ/selenium
- Helium (high-level wrapper): https://github.com/mherrmann/helium
- Suggested use:
  - Keep browser-use primary; use Playwright direct for brittle edge cases.

8. Workflow Scheduling / Daemons
- APScheduler: https://github.com/agronholm/apscheduler
- Celery: https://github.com/celery/celery
- Prefect: https://github.com/PrefectHQ/prefect
- Suggested use:
  - Different use than current interactive runtime: background jobs, queues, workers, and restart recovery.

9. Memory + Knowledge Stores (Open Source)
- SQLite (already implemented for light state via local JSON-style memory equivalent; keep SQLite as optional migration target).
- PostgreSQL: https://github.com/postgres/postgres
- Qdrant vector DB: https://github.com/qdrant/qdrant
- Chroma: https://github.com/chroma-core/chroma
- FAISS: https://github.com/facebookresearch/faiss
- Suggested use:
  - Different use than current memory file: long-term semantic retrieval and scalable multi-project memory.
  - Split memory into:
    - episodic (task logs), semantic (retrieval), procedural (successful playbooks).

10. Tool Sandbox / Guard Rails
- Firejail: https://github.com/netblue30/firejail
- Bubblewrap: https://github.com/containers/bubblewrap
- gVisor: https://github.com/google/gvisor
- Suggested use:
  - Execute high-risk shell/browser actions in constrained sandboxes.

11. Evaluation / Benchmarks for Agent Reliability
- AgentBench: https://github.com/THUDM/AgentBench
- GAIA benchmark: https://huggingface.co/gaia-benchmark
- WebArena: https://github.com/web-arena-x/webarena
- Suggested use:
  - Track progress with repeatable benchmark tasks and pass-rate metrics.

12. Observability / Tracing
- OpenTelemetry: https://github.com/open-telemetry/opentelemetry-python
- MLflow: https://github.com/mlflow/mlflow
- Langfuse (OSS observability): https://github.com/langfuse/langfuse
- Suggested use:
  - Different use than current runtime.log: structured distributed traces, dashboards, and long-term analytics.
