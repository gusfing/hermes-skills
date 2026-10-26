# LM Studio vs llama.cpp on headless Linux ARM64

## Session: 2026-08-19 — Gemma 4B / LM Studio CLI investigation

## What was learned

### LM Studio CLI (`lms`) — not viable standalone on this host

1. **`lms` npm package is broken:** `npm install -g lms` installs a wrapper at
   `/home/opc/.local/bin/lms` but it requires `@lmstudio/cli` which is not a
   declared dependency. Running `lms` throws:
   ```
   Error: Cannot find module '@lmstudio/cli'
   Require stack:
   - /home/opc/.local/lib/node_modules/lms/index.js
   ```
   The npm package `lms@0.0.21` has `bin: {"lms": "index.js"}` and no
   runtime dependencies, but `index.js` does `require('@lmstudio/cli')` which
   doesn't resolve. The package is MIT-licensed and ships from
   https://github.com/lmstudio-ai/lms.

2. **`lms` is not standalone — it ships with the LM Studio Desktop app:**
   Per LM Studio docs (https://lmstudio.ai/docs/cli), "lms ships with LM
   Studio, so you don't need to do any additional installation steps if you
   have LM Studio installed." The CLI is a companion to the Desktop app, not
   a headless inference tool.

3. **LM Studio Desktop for Linux ARM64 exists (v0.4.21 build 2):**
   The download page at https://lmstudio.ai/download publishes AppImage and
   .deb for linux/arm64. SHA512 for arm64 AppImage v0.4.21:
   `f07f0582203a8ea2cd770599005f3fb60a4ee4cd4455796e9b653f06b292bf72dba36a48f27f7568ef94f32e1913fec7209a03a0a3f2fee65287451ade325087`

   But the Desktop app is Electron-based — it needs a display. On a headless
   server with no X display, it's not directly usable.

### llama.cpp CLI — the right tool for headless local inference

For headless Linux ARM64 inference of Gemma 4B (or any GGUF model):

1. **llama.cpp is the correct tool, not LM Studio:** llama.cpp provides
   `llama-cli` and `llama-server` (OpenAI-compatible API) that run headless
   with no display requirement.

2. **Gemma 4B fit:** Gemma 4B Q4_K_M GGUF is ~2.5 GB. On a 10 GB RAM / 2-core
   ARM64 box, it fits. Inference speed on 2 ARM cores: ~2-5 tok/s (slow but
   functional for small tasks).

3. **Install paths:**
   - `pip install llama-cpp-python` — triggers C++ build from source (~10-15
     min on 2 ARM cores). No prebuilt aarch64 wheel on PyPI.
   - Build llama.cpp from source: `git clone https://github.com/ggml-org/llama.cpp && cmake -B build && cmake --build build --config Release`
   - Prebuilt binaries: check https://github.com/ggml-org/llama.cpp/releases

4. **Run directly from HuggingFace Hub:**
   ```bash
   llama-cli -hf google/gemma-4b-it-q4km:Q4_K_M
   llama-server -hf google/gemma-4b-it-q4km:Q4_K_M
   ```

5. **Tiny models for slow hardware:** if 2 cores is too slow, consider Qwen
   0.5B or TinyLlama — noticeably faster on constrained ARM hardware.

## Decision rule

- **Need GUI + model discovery + chat UI?** → LM Studio Desktop (requires
  display, use on laptop with Tailscale).
- **Need headless inference on a server?** → llama.cpp CLI or llama-cpp-python
  bindings. Skip LM Studio entirely.
- **lms npm package installed but broken?** → uninstall it. It's not a fixable
  standalone tool. The dependency on `@lmstudio/cli` is a packaging gap, not
  something pip can resolve.
