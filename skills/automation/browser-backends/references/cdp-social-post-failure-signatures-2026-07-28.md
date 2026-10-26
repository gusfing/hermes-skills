Direct Chrome CDP social post failure signatures — 2026-07-28

Observed pattern: fresh Chrome `--user-data-dir` profiles in CDP lack login state, so any attempt to open composer or upload media against X/LinkedIn/Instagram lands on auth modal instead of composer. The reliable fix is to use a pre-authenticated profile dir or explicitly authenticate interactively before automation.
