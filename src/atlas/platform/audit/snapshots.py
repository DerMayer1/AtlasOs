"""Immutable, hash-verified data snapshots (PRD R2).

Layout on disk:
    <root>/<snapshot_id>/manifest.json
    <root>/<snapshot_id>/<table>.parquet

Rules:
- snapshot_id is derived from the content hashes -> identical input data
  produces the same id; nothing is ever overwritten.
- load() verifies every table hash; a mismatch raises SnapshotIntegrityError
  loudly instead of silently serving corrupted or substituted data.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from atlas.platform.contracts.schemas import SnapshotManifest, SnapshotTable, utcnow

MANIFEST_FILE = "manifest.json"


class SnapshotNotFoundError(Exception):
    pass


class SnapshotIntegrityError(Exception):
    pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _frame_content_hash(df: pd.DataFrame) -> str:
    """Hash logical content (not parquet bytes) so the id is stable per dataset."""
    h = hashlib.sha256()
    h.update(",".join(map(str, df.columns)).encode())
    h.update(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    return h.hexdigest()


class SnapshotStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        tables: Mapping[str, pd.DataFrame],
        sources: list[str],
        period_start: str | None = None,
        period_end: str | None = None,
    ) -> SnapshotManifest:
        if not tables:
            raise ValueError("a snapshot must contain at least one table")

        content = hashlib.sha256()
        for name in sorted(tables):
            content.update(name.encode())
            content.update(_frame_content_hash(tables[name]).encode())
        snapshot_id = f"snap_{content.hexdigest()[:16]}"

        snap_dir = self.root / snapshot_id
        if snap_dir.exists():
            return self.manifest(snapshot_id)  # identical content already frozen

        tmp_dir = self.root / f".tmp_{snapshot_id}"
        tmp_dir.mkdir(parents=True, exist_ok=False)
        try:
            table_entries: list[SnapshotTable] = []
            for name in sorted(tables):
                file_name = f"{name}.parquet"
                file_path = tmp_dir / file_name
                tables[name].to_parquet(file_path, index=True)
                table_entries.append(
                    SnapshotTable(
                        name=name,
                        file=file_name,
                        sha256=_sha256_file(file_path),
                        rows=len(tables[name]),
                    )
                )

            manifest = SnapshotManifest(
                snapshot_id=snapshot_id,
                created_at=utcnow(),
                sources=sources,
                period_start=period_start,
                period_end=period_end,
                tables=table_entries,
            )
            (tmp_dir / MANIFEST_FILE).write_text(manifest.model_dump_json(indent=2))
            tmp_dir.rename(snap_dir)  # atomic publish: never a half-written snapshot
        except BaseException:
            for p in tmp_dir.glob("*"):
                p.unlink()
            tmp_dir.rmdir()
            raise
        return manifest

    def manifest(self, snapshot_id: str) -> SnapshotManifest:
        path = self.root / snapshot_id / MANIFEST_FILE
        if not path.exists():
            raise SnapshotNotFoundError(f"snapshot {snapshot_id!r} not found under {self.root}")
        return SnapshotManifest.model_validate(json.loads(path.read_text()))

    def load(self, snapshot_id: str, verify: bool = True) -> dict[str, pd.DataFrame]:
        manifest = self.manifest(snapshot_id)
        snap_dir = self.root / snapshot_id
        out: dict[str, pd.DataFrame] = {}
        for table in manifest.tables:
            file_path = snap_dir / table.file
            if not file_path.exists():
                raise SnapshotIntegrityError(
                    f"snapshot {snapshot_id}: table file {table.file} is missing"
                )
            if verify and _sha256_file(file_path) != table.sha256:
                raise SnapshotIntegrityError(
                    f"snapshot {snapshot_id}: hash mismatch for {table.file} "
                    "(data was modified after freezing)"
                )
            out[table.name] = pd.read_parquet(file_path)
        return out
