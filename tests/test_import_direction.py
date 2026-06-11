"""PRD R1/§7.1 acceptance: the platform layer is domain-agnostic — it must not
import anything from atlas.domain or atlas.agent (which both depend on it)."""

import re
from pathlib import Path

PLATFORM_DIR = Path(__file__).resolve().parents[1] / "src" / "atlas" / "platform"

FORBIDDEN = re.compile(r"^\s*(from|import)\s+atlas\.(domain|agent)", re.MULTILINE)


def test_platform_never_imports_domain_or_agent():
    offenders = [
        str(path)
        for path in PLATFORM_DIR.rglob("*.py")
        if FORBIDDEN.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"platform files importing domain/agent: {offenders}"
