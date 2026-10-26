# LobeChat Setup — Connecting to a Local LLM

LobeChat (github.com/AIDotNet/lobe-chat, fork of lobehub/lobehub) is an open-source ChatGPT-like web UI. This reference covers deploying LobeChat and wiring it to a locally-running model server.

## What LobeChat supports

- Multi-provider: OpenAI, Claude, Gemini, Ollama, Bedrock, Azure, Mistral, Perplexity, and custom OpenAI-compatible endpoints
- Multi-modal: vision + TTS
- Plugin system (function calling)
- PWA, mobile-adaptive, custom themes
- Local or remote database (PostgreSQL/Drizzle ORM)
- Multi-user management

**Project status:** Last commit Aug 2024 (v1.11.9). 235 stars, 43 forks. Stack: Next.js + TypeScript + Bun.

## Deployment options

### Option 1: npm (development / lightweight)

Requirements: Node.js v18+, npm.

```bash
git clone https://github.com/AIDotNet/lobe-chat
cd lobe-chat
npm install
npm run dev        # → http://localhost:3000
```

### Option 2: Docker (production-ish)

```bash
docker pull lobehub/lobe-chat
docker run -d -p 3000:3000 lobehub/lobe-chat
```

Docker is installed on this box (`/usr/bin/docker`).

### Option 3: Vercel (one-click, no server)

Push to GitHub and deploy on Vercel. Good for hosting the UI remotely while the model server stays local (need to expose the model API or use a tunnel).

## Connecting to a llama.cpp Python server

**Prerequisite:** llama.cpp Python server is running on `http://127.0.0.1:8080` (see main skill).

1. Open LobeChat in the browser (`http://localhost:3000`)
2. Go to Settings → Model Providers
3. Add a **custom provider** (OpenAI-compatible):
   - **Provider name:** anything (e.g. "Local Gemma")
   - **Base URL:** `http://127.0.0.1:8080`
   - **Model name:** `gemma-4b` (or whatever `/v1/models` reports)
   - **API key:** leave empty (local server doesn't require one)
4. Save and select the provider in the chat UI

**Test:** send a message. If the model responds, the wiring is correct.

**Troubleshooting:** if LobeChat shows "model not found" or connection errors:
- Verify the server is running: `curl http://127.0.0.1:8080/v1/models`
- Check LobeChat can reach the URL (CORS is usually not an issue for same-machine localhost)
- Confirm the model name in the custom provider matches exactly what `/v1/models` returns

## Connecting to Ollama

**Prerequisite:** Ollama is running (`ollama serve`), Gemma is imported.

1. Open LobeChat
2. Go to Settings → Model Providers
3. Select **Ollama** from the built-in providers
4. Ollama default URL is `http://localhost:11434` — no custom config needed
5. Select the Gemma model from the Ollama model list

This is the simpler path if Ollama is already set up.

## Environment variables (for Docker / self-hosted)

If deploying LobeChat with Docker and a database:

```bash
docker run -d \
  -p 3000:3000 \
  -e DATABASE_URL="postgresql://…" \
  -e NEXTAUTH_SECRET="…" \
  -e NEXTAUTH_URL="http://localhost:3000" \
  lobehub/lobe-chat
```

For a simple local setup with no database/auth, the defaults work.

## Custom provider API shape

LobeChat's custom OpenAI-compatible provider expects the standard OpenAI chat completions endpoint:

```
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "<model-name>",
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "max_tokens": 128,
  "temperature": 0.7
}
```

The llama.cpp Python server and Ollama both serve this exact shape, so the wiring is straightforward.
