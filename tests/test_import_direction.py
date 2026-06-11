"""PRD R1 acceptance: platform/ must not import anything from domain/."""

import re
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parents[1] / "src" / "atlas" / "platform"

FORBIDDEN = re.compile(r"^\s*(from|import)\s+atlas\.domain", re.MULTILINE)


def test_platform_never_imports_domain():
    offenders = [
        str(path)
        for path in PLATFORM_DIR.rglob("*.py")
        if FORBIDDEN.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"platform files importing domain: {offenders}"
