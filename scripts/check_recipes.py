#!/usr/bin/env python3
"""Integrity checks for the recipe files — the cheapest gate a Markdown skill can have.

Three checks, none of which need an API key or a paid call:

1. Every ```python block in models/*.md and SKILL.md compiles (py_compile).
2. Every recipe path named in SKILL.md's routing table actually exists.
3. Each model ID is spelled the same everywhere it appears across the repo.

Exit 0 if all pass, 1 otherwise. Run: python scripts/check_recipes.py
"""
from __future__ import annotations

import py_compile
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Free names the snippets reference; stubbed so compilation reflects syntax, not context.
STUB = "prompt = 'x'\nreference_images = []\nimage_path = None\noutput_path = 'o'\nseed = 0\n"


def compile_blocks() -> list[str]:
    errors = []
    md_files = sorted((ROOT / "models").glob("*.md")) + [ROOT / "SKILL.md"]
    for md in md_files:
        blocks = re.findall(r"```python\n(.*?)```", md.read_text(encoding="utf-8"), re.S)
        for i, block in enumerate(blocks):
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(STUB + block)
                tmp = f.name
            try:
                py_compile.compile(tmp, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(f"{md.name}[block {i}] does not compile: {e.msg}")
    return errors


def check_recipe_paths() -> list[str]:
    errors = []
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for rel in re.findall(r"`(models/[\w.-]+\.md)`", skill):
        if not (ROOT / rel).is_file():
            errors.append(f"routing table points at missing recipe: {rel}")
    return errors


def check_model_ids() -> list[str]:
    """Every model ID must be spelled identically wherever it appears.

    Anchor on the IDs declared in each recipe's metadata table, then confirm no
    file uses a near-miss variant (same family, different suffix) of that ID.
    """
    errors = []
    ids = set()
    for md in (ROOT / "models").glob("*.md"):
        for m in re.findall(r"\|\s*Model ID\s*\|\s*`([^`]+)`\s*\|", md.read_text(encoding="utf-8")):
            ids.add(m)
    all_text = {p: p.read_text(encoding="utf-8") for p in ROOT.glob("*.md")}
    all_text.update({p: p.read_text(encoding="utf-8") for p in (ROOT / "models").glob("*.md")})
    for canonical in sorted(ids):
        # e.g. canonical gemini-3-pro-image must not coexist with gemini-3-pro-image-preview
        variant = re.compile(re.escape(canonical) + r"-[\w.-]+")
        for path, text in all_text.items():
            hits = {h for h in variant.findall(text) if h != canonical}
            for h in hits:
                errors.append(f"{path.name}: '{h}' looks like a stale variant of '{canonical}'")
    return errors


def main() -> int:
    all_errors = compile_blocks() + check_recipe_paths() + check_model_ids()
    if all_errors:
        print("FAIL:")
        for e in all_errors:
            print(f"  - {e}")
        return 1
    print("OK: snippets compile, recipe paths resolve, model IDs are consistent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
