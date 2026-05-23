# Unified Live Assistant (Ollama Cloud + Local Tools + MCP Registry)

This runtime is a complete local assistant loop with:
- Multi-step planning/execution
- Policy-gated shell execution
- File and code-search tools
- MCP server registry loading
- Ollama Cloud as model backend

## Start to Finish Setup

### 1) Create workspace and enter project

```bash
cd /home/mayur/Desktop/ai
# if not already present:
# mkdir -p system_builder
cd system_builder
```

### 2) Clone integration repositories

```bash
mkdir -p integrations
cd integrations

git clone https://github.com/langchain-ai/langgraph.git
git clone https://github.com/pydantic/pydantic-ai.git
git clone https://github.com/browser-use/browser-use.git
git clone https://github.com/OpenHands/OpenHands.git
git clone https://github.com/crewAIInc/crewAI.git
git clone https://github.com/run-llama/llama_index.git
git clone https://github.com/deepset-ai/haystack.git
git clone https://github.com/Skyvern-AI/skyvern.git

cd ..
```

### 3) Configure environment

```bash
cp .env.example .env
# edit .env and set:
# - OLLAMA_API_KEY
# - OLLAMA_MODEL (example: gemma4:31b-cloud)
```

### 4) Verify integration folders

```bash
ls -1 integrations
```

### 5) Run assistant

```bash
./run.sh
```

## Interactive commands
- `:status` provider, model, safety, MCP summary, capabilities
- `:capabilities` tool and integration presence snapshot
- `:history` last 5 goals
- `:exit` stop

## Tooling available to the model
- `shell`
- `list_dir`
- `read_file`
- `write_file`
- `search_code`
- `capabilities`

## Safety behavior
`MCP_APPROVAL_MODE` controls high-risk shell commands:
- `auto`: execute automatically
- `ask`: request approval
- `block`: reject high-risk commands

Hard-block destructive command patterns are always denied.

## Notes on integrated repos
The cloned frameworks in `integrations/` are available as source and reference context.
This runtime is intentionally unified at the orchestration layer first, so behavior is reliable before deeper framework-specific adapters are added.
