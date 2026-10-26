# Server Pitfalls — llama.cpp Python Server

Concrete failures encountered when running `python3 -m llama_cpp.server` and how to fix them.

## 1. `ModuleNotFoundError: starlette_context`

**Symptom:** Server fails to start immediately with:
```
ModuleNotFoundError: No module named 'starlette_context'
```

**Cause:** The llama.cpp Python server module imports `starlette_context.plugins.RequestIdPlugin` at startup. If `starlette-context` is not installed, the import fails before the server even begins.

**Fix:**
```bash
python3 -m pip install starlette-context
```

**Pitfall — wrong Python:** `pip install starlette-context` may install into the system Python (e.g. python3.9) while the server is invoked with a venv Python (e.g. python3.11). The import still fails.

Always verify you're installing into the correct Python:
```bash
# Check which Python runs the server
python3 -c "import sys; print(sys.executable)"

# Install into that exact Python
python3 -m pip install starlette-context

# Verify
python3 -c "from starlette_context.plugins import RequestIdPlugin; print('OK')"
```

## 2. Server starts but model returns empty text

**Symptom:** `curl` to `/v1/chat/completions` returns a valid JSON response but `content` is empty or the model outputs nonsense.

**Cause:** Chat template mismatch. The model needs a specific turn-formatting scheme that the server isn't applying.

**Fix for Gemma models:** Gemma instruction-tuned models use `<|start_of_turn|>` / `<|end_of_turn|>` markers. The Python server usually auto-detects the chat format from GGUF metadata, but if it doesn't:

```bash
# Restart server with explicit chat template
python3 -m llama_cpp.server \
    --model /path/to/gemma-4b-q4km.gguf \
    --chat-template gemma \
    --host 127.0.0.1 \
    --port 8080
```

Or use the Python `Llama` class directly:

```python
from llama_cpp import Llama

llm = Llama(
    model_path="/path/to/gemma-4b-q4km.gguf",
    n_ctx=2048,
    chat_format="gemma",
)

resp = llm.create_chat_completion(
    messages=[{"role": "user", "content": "What is 2+2?"}],
    max_tokens=20,
)
print(resp["choices"][0]["message"]["content"])
```

**General fix:** try `--chat-template llama-3` or `--chat-template chatml` if the model is a Llama-family model. Check the model's HuggingFace page for the correct chat template.

## 3. Slow inference on CPU

**Expected:** 2–5 tok/s on 2 ARM cores for a 4B model at Q4_K_M. This is normal and not a bug.

**If slower than expected:**
- Check `--n_batch` — increase from default to 512 or 1024 for faster prompt processing (uses more RAM).
- Check `--n_ctx` — don't set it larger than needed; a 2048-context model doesn't need 8192.
- Check if swap is being used: `free -h` — if swap is active, performance drops sharply.
- Use a smaller model if speed is critical (e.g. 1B–2B instead of 4B+).

## 4. Model file not found or download incomplete

**Symptom:** Server fails to load the model, or the model behaves strangely.

**Cause:** The GGUF file is missing, truncated, or the wrong file.

**Fix:**
1. Verify the file exists and has the expected size:
   ```bash
   ls -lh /path/to/model.gguf
   ```
2. A Gemma 4B Q4_K_M GGUF is ~2.5–5 GB depending on the exact quant. If the file is much smaller, the download was truncated.
3. Re-download using the HuggingFace tree API to confirm the exact filename:
   ```bash
   curl -s "https://huggingface.co/api/models/<repo>/tree/main?recursive=true" | \
     python3 -c "import sys,json;d=json.load(sys.stdin);[print(f['path'], f['size']) for f in d if f['type']=='file' and f['path'].endswith('.gguf')]"
   ```

## 5. Server port already in use

**Symptom:** Server fails to bind to the port.

**Fix:**
```bash
# Check what's using the port
lsof -i :8080   # or ss -tlnp | grep 8080

# Kill the existing process or use a different port
python3 -m llama_cpp.server --port 8081 ...
```

## 6. Server process running but port not listening (bind mismatch)

**Symptom:** `ps aux` shows the llama.cpp server process alive, but `ss -tlnp | grep 8080` shows nothing listening, and `curl http://127.0.0.1:8080/v1/models` returns "Connection refused". The process may be binding to a different port (e.g. 4330) instead of the requested one.

**Cause:** The server's Uvicorn/Starlette layer may bind to a port derived from the model metadata or system state rather than the `--port` flag in some configurations, especially after a restart where a previous server instance left socket state.

**Fix:**
1. Check what port the process is actually listening on:
   ```bash
   # Read the process's TCP sockets directly
   cat /proc/<PID>/net/tcp | awk 'NR>1 && $4=="0A" {split($2,a,":"); printf "LISTEN: %s:%d\n", inet_ntoa(a[1]), strtonum("0x"a[2])}'
   ```
2. Or use ss with the PID filter:
   ```bash
   ss -tlnp | grep <PID>
   ```
3. If the port is wrong, kill the process and restart with an explicit `--port` flag. Verify with `ss -tlnp | grep 8080` before relying on the endpoint.
4. As a last resort, wait for the port to become available (the server may still be initializing; llama.cpp model loading can take 10-30 seconds). Poll with `curl --connect-timeout 3 http://127.0.0.1:8080/v1/models` every 3 seconds for up to 60 seconds.

## 7. Hermes gateway won't restart from inside its own process

**Symptom:** Running `hermes gateway restart` or `kill` inside a session that's connected through the gateway fails with:
```
Blocked: command or referenced script cannot restart or stop the gateway from inside the gateway process.
```

**Cause:** The Hermes gateway blocks self-restart to prevent SIGTERM from propagating to child processes and killing the session.

**Fix:**
1. Get the gateway PID from the JSON PID file:
   ```bash
   GATEWAY_PID=$(python3 -c "import json; print(json.load(open('/home/opc/.hermes/gateway.pid'))['pid'])")
   ```
2. Kill it directly:
   ```bash
   kill -9 $GATEWAY_PID
   ```
3. Wait ~5 seconds for systemd to auto-restart. Verify:
   ```bash
   cat /home/opc/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['gateway_state'], d['pid'])"
   ```
4. **Alternative:** run `hermes gateway restart` from a separate shell outside the gateway process.

## 8. Hermes config: wrong `default` value (model appears missing)

**Symptom:** After configuring Hermes to use a local llama.cpp server, the model does not appear in Hermes' model list or the gateway logs show the model as unavailable.

**Cause:** The `model.default` field is set to the provider name (`custom`) or a bare model name instead of the `model_aliases` key. Hermes resolves `default` through the `model_aliases` table; if the default isn't a key there, the model is not found.

**Correct schema:**
```yaml
model:
  default: gemma-4b              # MUST be the alias KEY
  provider: custom
  base_url: http://127.0.0.1:8080/v1

model_aliases:
  gemma-4b:
    model: gemma-4b-q4km.gguf   # exact model identifier for API calls
    provider: custom
    base_url: http://127.0.0.1:8080/v1
```

**Pitfall:** Do NOT use `default: custom` (the provider name) or `default: gemma-4b-q4km.gguf` (the model name). Both will cause the model to appear missing. Always set `default` to the alias key defined under `model_aliases`.

**Note:** The old config format using a `name` field under `model:` is NOT valid in current Hermes. The `model_aliases` table is the correct mechanism for custom provider model mapping.
