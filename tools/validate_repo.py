"""
Purpose: validate that this repository is a well-formed wrapper around an agent skill.
When used: before every release, in CI, and after any change to repository files.
Why it exists: it catches missing files, broken links, wrong icon paths, case collisions and build residue, and it runs the self-tests that the skill already ships.
Inputs: none. The repository root is the parent folder of tools/. Requires Python 3 and PyYAML.
Outputs: one PASS, FAIL or NOT RUN line per check, then a summary. Exit code 0 when no check failed, 1 otherwise.
Behaviour: read-only. It never repairs anything. Skill self-tests run only when their docstring says that they need no external inputs; they run with a timeout and without writing bytecode.
Failure semantics: any FAIL gives a non-zero exit code. NOT RUN means the invocation could not be determined from the docstring; it is reported, never guessed.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RESIDUE_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".venv", "venv"}
RESIDUE_FILES = {".DS_Store"}
RESIDUE_SUFFIX = {".pyc", ".pyo"}
SELFTEST_TIMEOUT = 120

results: list[tuple[str, str, str]] = []


def record(status: str, label: str, detail: str = "") -> None:
    results.append((status, label, detail))
    print(f"{status:7} {label}" + (f" - {detail}" if detail else ""))


def all_files() -> list[Path]:
    out = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        out.extend(Path(dirpath, f) for f in filenames)
    return out


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise ValueError("no YAML frontmatter")
    data = yaml.safe_load(m.group(1))
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a mapping")
    return data


def residue() -> list[str]:
    found = []
    for p in ROOT.rglob("*"):
        if ".git" in p.relative_to(ROOT).parts:
            continue
        if p.name in RESIDUE_DIRS or p.name in RESIDUE_FILES or p.suffix in RESIDUE_SUFFIX:
            found.append(p.relative_to(ROOT).as_posix())
    return found


def check_required(readme: str) -> None:
    required = [
        "SKILL.md", "README.md", "README.it.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
        ".gitignore", "requirements-dev.txt", ".github/workflows/validate.yml", "tools/validate_repo.py", "docs",
    ]
    if "](LICENSE)" in readme:
        required.append("LICENSE")
    if "docs/assets/logo" in readme:
        required += ["docs/assets/logo.svg", "docs/assets/logo.png"]
    for rel in required:
        record("PASS" if (ROOT / rel).exists() else "FAIL", f"required: {rel}")


def check_frontmatter() -> dict:
    try:
        fm = frontmatter(ROOT / "SKILL.md")
    except Exception as exc:  # noqa: BLE001 - report any parse failure
        record("FAIL", "SKILL.md frontmatter", str(exc))
        return {}
    name, desc = fm.get("name"), fm.get("description")
    ok_name = isinstance(name, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) is not None
    record("PASS" if ok_name else "FAIL", "frontmatter name", str(name))
    record("PASS" if isinstance(desc, str) and desc.strip() else "FAIL", "frontmatter description")
    return fm


def check_icons() -> None:
    for yml in sorted((ROOT / "agents").glob("*.yaml")) if (ROOT / "agents").exists() else []:
        data = yaml.safe_load(yml.read_text(encoding="utf-8")) or {}
        iface = data.get("interface", {}) if isinstance(data, dict) else {}
        for key, value in iface.items():
            if key.startswith("icon") and isinstance(value, str):
                target = (ROOT / value).resolve()  # icon paths resolve from the skill root
                inside = ROOT in target.parents
                record("PASS" if inside and target.is_file() else "FAIL", f"icon path {yml.name}:{key}", value)


def check_collisions() -> None:
    seen: dict[str, str] = {}
    clash = []
    for p in all_files():
        rel = p.relative_to(ROOT).as_posix()
        key = rel.lower()
        if key in seen and seen[key] != rel:
            clash.append((seen[key], rel))
        seen[key] = rel
    record("PASS" if not clash else "FAIL", "no case-insensitive name collisions", "; ".join(f"{a} / {b}" for a, b in clash))


LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)\)|!\[[^\]]*\]\(([^)\s]+)\)")


def check_links() -> None:
    broken = []
    for md in sorted(ROOT.rglob("*.md")):
        if ".git" in md.relative_to(ROOT).parts:
            continue
        text = md.read_text(encoding="utf-8")
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        for m in LINK.finditer(text):
            target = (m.group(1) or m.group(2)).split("#")[0]
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            if not (md.parent / target).exists():
                broken.append(f"{md.relative_to(ROOT).as_posix()} -> {target}")
    record("PASS" if not broken else "FAIL", "relative Markdown links resolve", "; ".join(broken))
    # raw <img src> in README logo blocks
    for md in (ROOT / "README.md", ROOT / "README.it.md"):
        for src in re.findall(r'<img[^>]+src="([^"]+)"', md.read_text(encoding="utf-8")):
            if not re.match(r"^[a-z][a-z0-9+.-]*:", src) and not (md.parent / src).exists():
                record("FAIL", f"image in {md.name}", src)


def selftests() -> list[Path]:
    cands = []
    for pattern in ("scripts/regression*.py", "scripts/*selftest*.py", "scripts/validate*.py", "tests/test_*.py"):
        cands += sorted(ROOT.glob(pattern))
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def run_selftests() -> None:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    for script in selftests():
        rel = script.relative_to(ROOT).as_posix()
        doc = ast.get_docstring(ast.parse(script.read_text(encoding="utf-8"))) or ""
        inputs = re.search(r"^Inputs/parameters:\s*(.+)$", doc, re.M | re.I)
        if not inputs or "no external inputs" not in inputs.group(1).lower():
            record("NOT RUN", f"self-test {rel}", "invocation not determinable from docstring")
            continue
        try:
            proc = subprocess.run([sys.executable, "-B", str(script)], cwd=ROOT, env=env, capture_output=True, text=True, timeout=SELFTEST_TIMEOUT)
        except subprocess.TimeoutExpired:
            record("FAIL", f"self-test {rel}", f"timeout after {SELFTEST_TIMEOUT}s")
            continue
        record("PASS" if proc.returncode == 0 else "FAIL", f"self-test {rel}", f"exit code {proc.returncode}")
        if proc.returncode != 0:
            print((proc.stdout + proc.stderr)[-1500:])


def main() -> int:
    skill_present = (ROOT / "SKILL.md").exists()
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    check_required(readme)
    if skill_present:
        check_frontmatter()
        check_icons()
    check_collisions()
    if readme:
        check_links()
    found = residue()
    record("PASS" if not found else "FAIL", "no build residue", ", ".join(found[:10]))
    if skill_present:
        run_selftests()
        found_after = residue()
        record("PASS" if not found_after else "FAIL", "no build residue after self-tests", ", ".join(found_after[:10]))
    failed = [r for r in results if r[0] == "FAIL"]
    skipped = [r for r in results if r[0] == "NOT RUN"]
    print(f"\n{len(results) - len(failed) - len(skipped)} passed, {len(failed)} failed, {len(skipped)} not run")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
