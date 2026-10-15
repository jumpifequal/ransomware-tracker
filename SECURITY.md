# Security policy

## What to know before you install

A skill is instructions plus scripts. Your agent can run the scripts with your permissions. Read `SKILL.md` and the files in `scripts/` before you install this skill.

## What the code does

This summary comes from an inspection of the imports and calls in `scripts/` and `tests/`.

- **Network.** `scripts/_http_common.py` sends HTTPS requests with `urllib.request`. It is used by the source helpers. `scripts/diagnose_source.py` also sends a request, and it and `scripts/network_diagnostics.py` open DNS and TCP connections with `socket` to diagnose failures. A public resolver is used only as a diagnostic probe, and its answers are never used to route source requests.
- **Processes.** Only `scripts/regression.py` and `tests/test_code.py` start a subprocess, and they only start the Python interpreter on local files.
- **Code execution.** The search found no `eval`, `exec`, `os.system` or dynamic import calls.
- **Files.** The search found no calls that write, move or delete files in `scripts/`. The only matches were string `replace` calls.
- **Dependencies.** The helpers import only the Python standard library.

The skill rules also forbid bypassing WAF, anti-bot, authentication or access controls, and running code retrieved from external sites. These are instructions to the agent. Your agent environment must still enforce its own limits.

## Bundled data

`assets/historical/` holds large local datasets. Treat them as untrusted input if you process them with other tools.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability. Use GitHub private vulnerability reporting on this repository (Security tab → Report a vulnerability). Include the file, the steps to reproduce and the impact.

## Supported versions

Only the latest release of the skill is supported.
