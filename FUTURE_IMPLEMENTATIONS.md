# Future Implementations

This document tracks planned upgrades for the Unified Live Assistant.

## 1) Project Handling Mode
- Add persistent project state (`project_state.json` or SQLite).
- Add task graph with statuses: `todo`, `in_progress`, `blocked`, `done`.
- Add checkpointing + resumable execution sessions.

## 2) Git-Aware Workflow
- Native tools for:
  - `git status`, `git diff`, `git add`, `git commit` (guarded)
  - branch creation and PR preparation summaries
- Automatic change summaries with risk notes.

## 3) Verification Pipeline
- Standard `plan -> execute -> verify -> report` chain.
- Add test/lint commands per detected project type.
- Add failure triage and retry strategy per command category.

## 4) MCP Runtime Integration
- Move from MCP registry loading to active MCP client execution.
- Route tool calls to configured MCP servers.
- Add server health checks and automatic fallback behavior.

## 5) Browser + Web Task Layer
- Wire `browser-use` as first-class tool actions.
- Add structured browser task schema (navigate/extract/form/submit).
- Add guarded handling for auth-sensitive actions.

## 6) Memory and Context
- Add long-term memory store (SQLite + embeddings).
- Add per-project memory namespaces.
- Add retrieval pipeline for prior decisions and fixes.

## 7) Safety and Governance
- Expand policy engine with:
  - path-level allow/deny rules
  - command category risk labels
  - per-tool approval profiles
- Add audit trail for every action and approval event.

## 8) UX and Operability
- Add daemon mode (`run`, `stop`, `status`).
- Add structured logs and optional JSON output mode.
- Add telemetry for latency, success rate, and error categories.

## 9) Model Routing
- Add provider/model fallback policies.
- Add per-task model selection (cheap/fast vs deep/complex).
- Add automatic model health probe before execution.

## 10) Packaging
- Create install script and reproducible environment setup.
- Add smoke tests for startup, provider call, and core tools.
- Add CI checks for syntax, style, and basic runtime behavior.

