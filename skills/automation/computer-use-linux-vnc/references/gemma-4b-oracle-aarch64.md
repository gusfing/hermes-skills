# Gemma 4B on Oracle Linux aarch64 — 2 ARM cores

Empirically measured inference speed for Gemma 4B IT Q4_K_M GGUF on this host.

- Model: `/home/opc/gemma-4b-q4km.gguf` (5.0 GB, Q4_K_M)
- Source: `lmstudio-community/gemma-4-E4B-it-GGUF` (HuggingFace)
- RAM: ~2.5 GB loaded
- CPU: 2 ARM cores, no GPU
- Speed: ~0.3 tok/s sustained (9 tokens in 31.6s); ~2.5 tok/s for short 25-token generations
- Haiku (25 tok): ~10s
- "What is 2+2?" (9 tok): ~32s
- Suitable for short responses only — expect 30+ second waits for 30+ token outputs
