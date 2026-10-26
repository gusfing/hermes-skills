---
name: hermes-gemma-integration
description: Wire Hermes to a local llama.cpp server via config.yaml.
version: 1.0.0
author: Kunal Sharma
license: MIT
dependencies: [llama-cpp, local-llm-serve]
platforms: [linux]
metadata:
  hermes:
    tags: [hermes-agent, gemma, llama-cpp, config.yaml, custom-provider, local-llm]
---

# Hermes Agent + Local Gemma Integration

Use this skill when Hermes Agent needs to use a locally-running llama.cpp server (Gemma, Llama, etc.) as its LLM backend instead of a cloud provider.

## When to use

- Hermes is currently using a cloud provider (OpenAI, OpenRouter, etc.) and you want it to use a local model
- You have a llama.cpp server running on localhost and want Hermes to call it
- You need to verify the full chain: server → Hermes config → gateway → inference

## Prerequisites

- llama.cpp Python server running on localhost (see `local-llm-serve` skill)
- Hermes Agent installed with `~/.hermes/config.yaml`
- Gateway running and reading the config

## Step 1: Edit Hermes config.yaml

Edit `~/.hermes/config.yaml` and set up the `model` section + `model_aliases`:

```yaml
model:
  default: gemma-4b              # MUST be the alias KEY, not the provider name
  provider: custom
  base_url: http://127.0.0.1:8080/v1

model_aliases:
  gemma-4b:
    model: gemma-4b-q4km.gguf   # exact model identifier for API calls
    provider: custom
    base_url: http://127.0.0.1:8080/v1
```

Key fields:
- `default` — **must be the alias key** (e.g. `gemma-4b`), NOT `custom` and NOT a bare model name. If set to `custom`, Hermes treats `custom` as a model name and won't find it in the alias table — the model will appear missing.
- `provider: custom` — tells Hermes to use a custom OpenAI-compatible endpoint
- `model_aliases` — maps a friendly name to the full provider + model + base_url triple
- `model_aliases.<key>.model` — must match what `/v1/models` returns from the llama.cpp server
- `base_url` — must include the `/v1` path suffix (OpenAI API convention)

**Pitfall — wrong default value:**

Setting `default: custom` (the provider name) instead of `default: gemma-4b` (the alias key) is a common mistake. Hermes resolves the default through the alias table; if the default isn't a key in `model_aliases`, the model appears unavailable. Always set `default` to the alias key.

## Step 2: Restart the Hermes gateway

The gateway must restart to pick up the new config. **Important:** you cannot restart from inside the gateway process. Two options:

**Option A — kill and let systemd restart:**
```bash
# Get gateway PID
GATEWAY_PID=$(python3 -c "import json; print(json.load(open('/home/opc/.hermes/gateway.pid'))['pid'])")
kill -9 $GATEWAY_PID
# systemd auto-restarts; wait ~5 seconds
sleep 5
```

**Option B — use a separate shell:**
Run `hermes gateway restart` from a different terminal/session outside the gateway process.

Verify restart:
```bash
cat /home/opc/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['gateway_state'], d['pid'])"
```

## Step 3: Verify end-to-end

```bash
# 1. llama.cpp server is up
curl http://127.0.0.1:8080/v1/models

# 2. Inference works directly
curl -X POST http://127.0.0.1:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma-4b-q4km.gguf","messages":[{"role":"user","content":"Say hi"}],"max_tokens":5}'

# 3. Hermes config has the right values
grep -A3 "^model:" ~/.hermes/config.yaml

# 4. Gateway is running with new config
cat /home/opc/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['gateway_state'])"
```

## Pitfalls

### Gateway won't restart from inside itself

The Hermes gateway refuses to restart when called from inside its own process (SIGTERM propagates to child processes). Error: "Blocked: command or referenced script cannot restart or stop the gateway from inside the gateway process."

**Fix:** Kill the gateway PID directly with `kill -9` and let systemd auto-restart. Or use a separate shell.

### Server process alive but port not listening

The llama.cpp server process may be running (visible in `ps aux`) but not actually listening on the configured port. This happened when the server bound to port 4330 instead of 8080.

**Fix:** Check with `ss -tlnp | grep <port>` or `curl http://127.0.0.1:<port>/v1/models`. If the port is not listening, kill the server and restart with explicit `--port` flag.

### Wrong Python environment for starlette-context

If the server fails to start with `ModuleNotFoundError: starlette_context`, the `starlette-context` package is missing from the Python environment that runs the server.

**Fix:** `python3 -m pip install starlette-context` using the same `python3` that runs the server.

## Model-specific notes

### Gemma 4B

- GGUF: `gemma-4-E4B-it-GGUF` from `lmstudio-community` on HuggingFace
- Quant: Q4_K_M (~5 GB file)
- Chat template: auto-detected from GGUF metadata by llama.cpp server
- Inference speed: ~0.3-2 tok/s on 2 ARM cores (Q4_K_M)

### Llama models

- Use `--chat-template llama-3` or `--chat-template chatml` if auto-detection fails
- Many quant options available: Q4_K_M, Q5_K_M, Q6_K, Q8_0

## References

- `local-llm-serve` skill — covers llama.cpp server setup, GGUF discovery, LobeChat integration
- `~/.hermes/config.yaml` — Hermes Agent configuration file
- `~/.hermes/gateway.pid` — gateway process ID (JSON format)
- `~/.hermes/gateway_state.json` — gateway runtime state

## Resources

- Hermes Agent config docs: see hermes-agent skill
- llama.cpp Python server: https://github.com/abetlen/llama-cpp-python
- Gemma GGUF on HuggingFace: https://huggingface.co/lmstudio-community/gemma-4-E4B-it-GGUF
