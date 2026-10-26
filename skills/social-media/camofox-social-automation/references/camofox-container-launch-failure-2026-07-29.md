# Camofox launch failure: Linux container, 2026-07-29

## Observed failure

When attempting to launch Camofox inside this container, the browser
process exits immediately with:

```
[err] Sandbox: CanCreateUserNamespace() clone() failure: EPERM
[err] XPCOMGlueLoad error for file /opt/data/.cache/camofox/libmozgtk.so:
[err] libgtk-3.so.0: cannot open shared object file: No such file or directory
[err] Couldn't load XPCOM.
```

Exit code: 255.

## Root cause

Two independent blockers:

1. **Missing GTK3 runtime library** (`libgtk-3.so.0`). The camoufox binary
   links against it; without it, XPCOM fails to load and Firefox cannot start.
2. **Namespace cloning blocked by container policy** (`CanCreateUserNamespace()
   clone() failure: EPERM`). Even if GTK3 is installed, sandboxed namespace
   creation is denied in this container/runtime.

## Implication

Camofox is not runnable in this container as of 2026-07-29. Do not
blindly retry launch; retrying wastes time and does not resolve either
blocker.

## Verified workaround

Use **local Chrome CDP at `127.0.0.1:9222`** as the primary automation
backend. Multi-account isolation is achieved with separate Chrome
`--user-data-dir` profile directories rather than Camofox `userId`s.

Reserve Camofox only when the user moves to a host where it can launch
(e.g. a VM or bare-metal host with GTK3 and proper sandbox permissions).
