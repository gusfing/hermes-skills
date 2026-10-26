---
name: local-llm-serve
description: Run local GGUF models as OpenAI API with LobeChat.
version: 1.0.0
author: Orchestra Research
license: MIT
dependencies: [llama-cpp-python, curl]
platforms: [linux, macos]
metadata:
  hermes:
    tags: [local-llm, llama-cpp, ollama, openai-api, GGUF, inference-server, LobeChat, python-server]
---

# Local LLM Serving

Use this skill when the user wants to run a local LLM (Gemma, Llama, Qwen, etc.) as an OpenAI-compatible API server and optionally connect it to a chat UI like LobeChat.

## When to use

- Run a GGUF model locally and expose it via an OpenAI-compatible HTTP API
- Choose between llama.cpp Python server, C++ llama-server, or Ollama
- Connect a frontend (LobeChat, custom UI) to a local model
- Debug server startup failures, missing dependencies, or chat template issues
- Decide which quant fits the available RAM/VRAM

## Decision guide: which server?

| Option | Best when | Setup cost | Notes |
|--------|-----------|-----------|-------|
| **llama.cpp Python server** (`python3 -m llama_cpp.server`) | llama-cpp-python already installed (venv, pip) | Lowest — no build, just `pip install starlette-context` | OpenAI-compatible API on port 8080 by default; `--model` points to a local GGUF |
| **C++ llama-server** (`llama-server -hf …`) | Want direct-from-Hub loading, or llama.cpp C++ build already available | Medium — requires building llama.cpp or installing via brew/winget | Can pull GGUF straight from HuggingFace Hub with `-hf repo:quant` |
| **Ollama** | Want the slickest UX, model management via `ollama pull/create`, and a LobeChat Ollama provider out of the box | Medium — install Ollama binary, then import GGUF via Modelfile | Ollama serves its own API; LobeChat has native Ollama provider support |

**Rule of thumb:** if `llama-cpp-python` is already in the environment, use the Python server. It's the fastest path to an OpenAI-compatible endpoint. If starting fresh and want Ollama's model management, install Ollama.

## GGUF / quant selection

- Start with `Q4_K_M` for general chat on CPU — good quality/size tradeoff.
- Prefer the exact quant the HuggingFace repo marks as compatible; use the repo's local-app page (`?local-app=llama.cpp`) as the source of truth.
- For code/technical work, `Q5_K_M` or `Q6_K` if memory allows.
- Gemma models: prefer `lmstudio-community/<model>-GGUF` repos — they publish llama.cpp-compatible quants.
- Tree API for exact filenames: `https://huggingface.co/api/models/<repo>/tree/main?recursive=true`

## llama.cpp Python server — step by step

### 1. Ensure llama-cpp-python is installed

```bash
python3 -m pip install llama-cpp-python
```

### 2. Install the missing server dependency

**Critical pitfall:** `python3 -m llama_cpp.server` imports `starlette_context.plugins.RequestIdPlugin`. If `starlette-context` is not installed, the server fails at startup with `ModuleNotFoundError`. Install it in the **same Python** that will run the server:

```bash
python3 -m pip install starlette-context
```

**Pitfall — wrong Python:** if `pip install starlette-context` ran in the system Python (e.g. python3.9) but the server is invoked with a venv Python (e.g. python3.11), the import still fails. Always use `python3 -m pip install ...` where `python3` is the exact interpreter that runs the server.

### 3. Start the server

```bash
python3 -m llama_cpp.server \
    --model /path/to/model.gguf \
    --host 127.0.0.1 \
    --port 8080 \
    --n_ctx 2048 \
    --n_batch 512
```

Key flags:
- `--model` — path to the GGUF file (already downloaded)
- `--host` — `127.0.0.1` for local-only (default); `0.0.0.0` to expose on the network
- `--port` — default 8080
- `--n_ctx` — context window size (e.g. 2048, 4096)
- `--n_batch` — batch size for prompt processing (larger = faster prompt eval, more RAM)

### 4. Verify

```bash
# List models
curl http://127.0.0.1:8080/v1/models

# Chat completion
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemma-4b",
    "messages": [{"role": "user", "content": "Say hi"}],
    "max_tokens": 5,
    "temperature": 0.7
  }'
```

Expected response shape: `{"choices":[{"message":{"content":"…"}}]`.

### 5. Chat format for Gemma

Gemma instruction-tuned models require the `<|start_of_turn|>` / `<|end_of_turn|>` turn markers. When using the Python server, the `chat_format` is auto-detected from the GGUF metadata in most cases, but if responses are empty or malformed, try explicit format:

```python
from llama_cpp import Llama

llm = Llama(
    model_path="/path/to/gemma-4b-q4km.gguf",
    n_ctx=2048,
    chat_format="gemma",   # Gemma-specific chat format
)

resp = llm.create_chat_completion(
    messages=[
        {"role": "user", "content": "What is 2+2?"},
    ],
    max_tokens=20,
)
print(resp["choices"][0]["message"]["content"])
```

If the server is already running and Gemma responds with empty text, the issue is likely the chat template. Restart with `--chat-template gemma` or use the `Llama` Python class directly with `chat_format="gemma"`.

## Ollama — quick setup

### Install

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Import a GGUF model

Create a `Modelfile`:

```
FROM /path/to/model.gguf
```

```bash
ollama create gemma4b -f Modelfile
ollama run gemma4b
```

Ollama serves an API on `http://localhost:11434`. LobeChat has a built-in Ollama provider that connects to it.

## LobeChat integration

LobeChat (github.com/AIDotNet/lobe-chat, fork of lobehub/lobehub) is an open-source ChatGPT-like UI supporting multiple AI providers.

### Connect to llama.cpp Python server

1. Start the llama.cpp server (see above) on `http://127.0.0.1:8080`
2. Deploy LobeChat (npm or Docker — see below)
3. In LobeChat settings, add a **custom provider** (OpenAI-compatible):
   - Base URL: `http://127.0.0.1:8080`
   - Model name: `gemma-4b` (or whatever the server reports)
   - API key: not required for local server

### Connect to Ollama

1. Start Ollama (`ollama serve`)
2. Deploy LobeChat
3. In LobeChat, select the **Ollama** provider — no custom config needed

### Deploy LobeChat

**Via npm (development):**
```bash
git clone https://github.com/AIDotNet/lobe-chat
cd lobe-chat
npm install
npm run dev        # → localhost:3000
```

**Via Docker:**
```bash
docker pull lobehub/lobe-chat
docker run -d -p 3000:3000 lobehub/lobe-chat
```

Requirements: Node.js v18+, npm. Bun is preferred by the project but npm works.

## Common pitfalls

### Server won't start — `ModuleNotFoundError: starlette_context`

The llama.cpp Python server requires `starlette-context`. Install it in the same Python environment:

```bash
python3 -m pip install starlette-context
```

Verify: `python3 -c "from starlette_context.plugins import RequestIdPlugin; print('OK')"`.

### Server starts but model responds with empty text

Likely a chat template mismatch. For Gemma models, ensure the chat format is `gemma` (turn markers `<|start_of_turn|>` / `<|end_of_turn|>`). Restart the server with `--chat-template gemma` or use the Python `Llama` class directly.

### Slow inference on CPU

Expect 2–5 tok/s on 2 ARM cores for a 4B model at Q4_K_M. This is normal. For faster inference, use a smaller model (e.g. 1B–2B) or a machine with more cores / a GPU.

### Model file not found / download fails

Verify the GGUF file exists and is the right size. A Gemma 4B Q4_K_M GGUF is ~2.5–5 GB depending on the quant. Use the HuggingFace tree API to confirm the exact filename and size.

## LM Studio CLI — when NOT to use it

LM Studio's CLI (`lms`) is **not** a good fit for headless servers:

- The `lms` npm package is often broken (missing `@lmstudio/cli` dependency) — `npm install lms` alone does not give you a working `lms` binary.
- `lms` is bundled with the LM Studio Desktop app, not a standalone tool. Installing the Desktop AppImage gives you `lms`, but the Desktop app is an Electron GUI that needs a display.
- On a headless server, skip LM Studio entirely. Use llama.cpp Python server, C++ llama-server, or Ollama — all give you an OpenAI-compatible API without a GUI.

## References

- **[hermes-gemma-integration](https://github.com/Orchestra-Research/hermes-agent/tree/main/skills/mlops/hermes-gemma-integration)** — Wire Hermes Agent to a local llama.cpp server via config.yaml (model section, gateway restart, end-to-end verification)
- **[gguf-discovery.md](references/gguf-discovery.md)** — HuggingFace tree API workflow, exact filename extraction, quant selection heuristics
- **[server-pitfalls.md](references/server-pitfalls.md)** — starlette-context trap, Python version mismatch, chat template debugging, empty-response recovery, server port-binding gotcha
- **[lobe-chat-setup.md](references/lobe-chat-setup.md)** — LobeChat deployment options, provider config, custom OpenAI-compatible endpoint wiring

## Resources

- **llama.cpp**: https://github.com/ggml-org/llama.cpp
- **llama-cpp-python**: https://github.com/abetlen/llama-cpp-python
- **HuggingFace GGUF + llama.cpp**: https://huggingface.co/docs/hub/gguf-llamacpp
- **Ollama**: https://ollama.com
- **LobeChat**: https://github.com/AIDotNet/lobe-chat
- **Gemma chat templates**: see HuggingFace Gemma documentation for turn marker format
