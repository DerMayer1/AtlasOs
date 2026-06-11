"""Atlas — macro-financial monitoring platform.

Layering rule (enforced by tests/test_import_direction.py):
    atlas.domain  -> may import atlas.platform
    atlas.platform -> must NEVER import atlas.domain
"""

__version__ = "0.1.0"
