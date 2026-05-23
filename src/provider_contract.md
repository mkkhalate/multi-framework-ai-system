# Provider Contract (Unified)

Every integration should call the same provider adapter interface:

- input: messages, model(optional), temperature(optional), tools(optional)
- output: assistant content, tool calls(optional), raw metadata

Provider selected by:
- `MODEL_PROVIDER` (default: ollama)
- `OLLAMA_BASE_URL`
- `OLLAMA_API_KEY`

This allows swapping model backend without rewriting agent logic.
