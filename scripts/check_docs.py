"""Check relative Markdown file links and required foundation documents offline."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors = []
for document in ROOT.rglob("*.md"):
    if any(part.startswith(".") and part != ".github" for part in document.relative_to(ROOT).parts):
        continue
    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
        if ":" in target or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        if path and not (document.parent / path).exists():
            errors.append(f"{document.relative_to(ROOT)}: missing {target}")
for path in (
    "README.md",
    "LICENSE",
    "SECURITY.md",
    "DATA_POLICY.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "ROADMAP.md",
    "FUNDING.md",
    "CODE_OF_CONDUCT.md",
    "schemas/evidence-passport.schema.json",
):
    if not (ROOT / path).exists():
        errors.append(f"Missing required file: {path}")
if errors:
    raise SystemExit("\n".join(errors))
print("Required documents and relative Markdown links pass")
