# AI Providers

> Reference guide for configuring and using AI providers with FilePilot AI.

---

## Overview

FilePilot AI uses a unified `AIProvider` interface (`filepilot/ai/base.py`) that abstracts over local and cloud AI engines. The summarizer (`filepilot/ai/summarizer.py`) works with any registered provider — no code changes needed to switch between them.

All providers are configured through the **Settings** dialog (or `~/.filepilot/settings.json`).

---

## Provider Comparison

| Provider | Mode | Default URL | API Key Required |
| -------- | ---- | ----------- | ---------------- |
| Ollama | Local | `http://localhost:11434` | No |
| llama.cpp / vLLM | Local | `http://localhost:8080` | No |
| LM Studio | Local | `http://localhost:1234` | No |
| OpenAI | Cloud | `https://api.openai.com/v1` | Yes |
| Anthropic | Cloud | `https://api.anthropic.com` | Yes |
| Custom endpoint | Cloud / Local | User-defined | Varies |

---

## Local Providers

### Ollama

[Ollama](https://ollama.ai/) is the recommended default for local AI — easy to install, no API key needed.

**Quick start:**

```bash
# Install Ollama (macOS / Linux)
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2

# Ollama serves by default on http://localhost:11434
```

**In FilePilot AI:**
1. Open **Settings** → **AI Provider**
2. Select **Ollama**
3. Leave API base as `http://localhost:11434` (or customize if running remotely)
4. Click **Save**

### llama.cpp / LM Studio / vLLM

These providers expose an OpenAI-compatible HTTP API, so FilePilot connects to them through the `LlamaCppProvider` class.

**LM Studio:**

1. Download from [lmstudio.ai](https://lmstudio.ai/)
2. Load a model and start the local inference server
3. The server runs at `http://localhost:1234` (default)

**llama.cpp server:**

```bash
# Start the server
./llama-server -m models/my-model.gguf --port 8080
```

**In FilePilot AI:**
1. Open **Settings** → **AI Provider**
2. Select **llama.cpp**
3. Set the API base to your server URL (e.g. `http://localhost:1234` for LM Studio)
4. Click **Save**

---

## Cloud Providers

### OpenAI

Supports OpenAI models (GPT-4, GPT-4o, GPT-3.5-turbo, etc.) and any OpenAI-compatible API (DeepSeek, Moonshot, Groq, etc.).

**Setup:**

1. Get an API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. In FilePilot AI: **Settings** → **AI Provider** → **OpenAI**
3. Paste your API key
4. (Optional) Change the API base to use a compatible endpoint
5. Click **Save**

**Custom endpoints:**

To use a different OpenAI-compatible provider (e.g. DeepSeek, Groq):

```
API Base: https://api.deepseek.com/v1
```

### Anthropic

Supports Claude models (Claude 3.5 Sonnet, Claude 3 Opus, etc.).

**Setup:**

1. Get an API key from [console.anthropic.com](https://console.anthropic.com/)
2. In FilePilot AI: **Settings** → **AI Provider** → **Anthropic**
3. Paste your API key
4. Click **Save**

### Custom Endpoint

Use this option for self-hosted gateways, proxy servers, or any OpenAI-compatible API that doesn't fit the presets above.

| Field | Description |
|-------|-------------|
| API Base URL | The full endpoint URL (e.g. `https://my-gateway.example.com/v1`) |
| API Key | Authentication token (if required) |
| Model Name | The model identifier to use for requests |

---

## Configuration Reference

### Settings File

Provider configuration is stored in `~/.filepilot/settings.json`:

```json
{
  "ai_provider": "ollama",
  "ollama_base": "http://localhost:11434",
  "llamacpp_base": "http://localhost:8080",
  "openai_key": "...",
  "openai_base": "https://api.openai.com/v1",
  "anthropic_key": "...",
  "anthropic_base": "https://api.anthropic.com",
  "custom_base": "",
  "custom_key": "",
  "custom_model": ""
}
```

API keys are stored in the OS keyring (`keyring`) when available, with encrypted fallback to a local file.

### Embedding API (Semantic Search)

Semantic search uses the configured AI provider's `embed()` method to compute file embeddings during indexing, then re-ranks Whoosh results by cosine similarity.

| Provider | Supports `embed()` | Notes |
| -------- | ------------------ | ----- |
| Ollama | Yes | Uses `/api/embeddings` endpoint |
| llama.cpp / LM Studio | Yes | Uses `/v1/embeddings` endpoint (OpenAI-compatible) |
| OpenAI | Yes | Uses `/embeddings` endpoint with `text-embedding-3-small` by default |
| Anthropic | **No** | Falls back to Whoosh score ordering (semantic checkbox has no effect) |
| Custom endpoint | Varies | Works if the endpoint supports OpenAI-compatible `POST /embeddings` |

Embeddings are cached in `~/.filepilot/embeddings.json` and computed incrementally during index builds. The `embedding_extractor` callback can be configured to determine which text to embed (defaults to file content).

### Programmatic Usage

```python
from filepilot.ai.cloud_ai import OpenAIProvider

provider = OpenAIProvider(
    api_key="sk-...",
    api_base="https://api.openai.com/v1",
    model="gpt-4o",
)

result = provider.generate(
    prompt="Summarize this file",
    system_prompt="You are a helpful assistant",
    temperature=0.3,
)
```

---

## Privacy

- **Local providers** (Ollama, llama.cpp): All processing stays on your machine — no data leaves your network.
- **Cloud providers** (OpenAI, Anthropic): Only the content you explicitly choose to summarize is sent to the provider. File scanning, indexing, duplicate detection, and organization never use AI.
- **API keys** are stored in your operating system's credential manager, never in plain text.
