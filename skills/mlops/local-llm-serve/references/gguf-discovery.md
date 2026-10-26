# GGUF Discovery Workflow

How to find the right GGUF file for a model on HuggingFace, step by step.

## 1. Find candidate repos

Search HuggingFace for llama.cpp-compatible models:

```
https://huggingface.co/models?apps=llama.cpp&sort=trending
https://huggingface.co/models?search=<model-family>&apps=llama.cpp&sort=trending
```

For Gemma specifically, the `lmstudio-community` org publishes well-maintained GGUF quants:

```
https://huggingface.co/lmstudio-community?search=gemma
```

## 2. Open the local-app page

For any candidate repo, open:

```
https://huggingface.co/<repo>?local-app=llama.cpp
```

This page shows:
- The recommended quant label (e.g. `Q4_K_M`)
- The exact filename
- The file size
- A ready-to-copy `llama-server` or `llama-cli` command

Treat this as the source of truth. If the page shows `UD-Q4_K_M`, use that exact label — don't normalize it.

## 3. Confirm with the tree API

The local-app page is a UI — verify the file actually exists:

```
https://huggingface.co/api/models/<repo>/tree/main?recursive=true
```

Filter for entries where:
- `type` is `"file"`
- `path` ends with `.gguf`
- The path does NOT start with `BF16/` (those are shards, not standalone GGUFs)
- The path does NOT start with `mmproj-` (those are multimodal projectors, not the main model)

Use `path` and `size` from the tree API as the definitive filename and byte size.

## 4. Reconstruct the download URL

Once you have the exact filename:

```
https://huggingface.co/<repo>/resolve/main/<filename>
```

Download with curl:

```bash
curl -L -o model.gguf "https://huggingface.co/<repo>/resolve/main/<filename>"
```

## 5. Quant selection heuristics (when the local-app page is ambiguous)

- **Q4_K_M** — general chat, best quality/size tradeoff for CPU
- **Q5_K_M** — code/technical, if memory allows
- **Q6_K** — higher quality, ~50% larger than Q4
- **Q8_0** — near-BF16 quality, 2× the size of Q4
- **IQ4_XS / IQ4_NL** — "imatrix" quants, smaller than Q4 with comparable quality for some models
- **Q3_K_M** — tight RAM budgets, noticeable quality drop
- **Q2** variants — only if the user explicitly prioritizes fit over quality

Don't normalize repo-native labels. If the repo uses `UD-Q4_K_M`, report it as-is.

## Example: Gemma 4B

```bash
# 1. Find the repo
# Search: https://huggingface.co/models?search=gemma&apps=llama.cpp

# 2. Open local-app
# https://huggingface.co/lmstudio-community/gemma-4-E4B-it-GGUF?local-app=llama.cpp
# Shows: Q4_K_M, file: gemma-4-E4B-it-Q4_K_M.gguf

# 3. Confirm with tree API
# https://huggingface.co/api/models/lmstudio-community/gemma-4-E4B-it-GGUF/tree/main?recursive=true
# Confirms: gemma-4-E4B-it-Q4_K_M.gguf exists

# 4. Download
curl -L -o gemma-4b-q4km.gguf \
  "https://huggingface.co/lmstudio-community/gemma-4-E4B-it-GGUF/resolve/main/gemma-4-E4B-it-Q4_K_M.gguf"
```
