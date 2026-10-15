# Contributing

Thank you for helping to improve **ransomware-tracker**.

## The central rule

The skill states one rule that every change must keep:

> Only `scripts/coverage_gate.py` may authorize maximum-effort completion.

Do not add a second path that lets an answer finish before this gate agrees.

## Before you open a pull request

1. Read `SKILL.md` and the file you plan to change.
2. Keep changes small and explain the reason.
3. If you change the skill itself (`SKILL.md`, `agents/`, `references/`, `scripts/`, `assets/`, `tests/`), add an entry to `CHANGELOG.md` and update the version in `SKILL.md`.
4. Run the checks:

```bash
pip install -r requirements-dev.txt
python tests/test_code.py
python scripts/regression.py
python tools/validate_repo.py
```

5. Do not commit caches, virtual environments or secrets.

## What belongs in the wrapper

Files outside the skill payload (README, docs, CI, `tools/`) describe the skill. They must match what the skill really does. If a claim depends on a vendor product or service, say so and link to the vendor documentation.

## Reporting a problem

For a security problem, follow [SECURITY.md](SECURITY.md). For anything else, open an issue.

## License

By contributing you agree that your contribution is licensed under the Apache License 2.0.
