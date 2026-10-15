# Python implementation discipline

Apply this discipline to every bundled Python module and to future code changes.

## Core principles

- Prefer the smallest correct implementation.
- Keep control flow explicit and locally understandable.
- Avoid speculative abstractions, generic frameworks, and unnecessary indirection.
- Prefer the Python standard library unless a dependency materially improves correctness.
- Use descriptive English identifiers, comments, docstrings, error messages, and test names.
- Validate inputs at trust boundaries and fail explicitly.
- Do not hide failures behind broad exception handling.
- Keep network destinations allow-listed and visible in source.
- Keep side effects narrow and intentional.
- Separate deterministic transport/parsing from model-level interpretation.
- Optimize for readability before cleverness.
- Preserve stable interfaces unless a behavioral change requires otherwise.

## Testing principles

- Keep deterministic tests independent from live network access.
- Test routing, parameter validation, JSON envelopes, and failure semantics.
- Run package regression checks after structural, metadata, code, or reference changes.
- Verify importability and package hygiene.
- Never claim a live source works unless a live request actually succeeded.
