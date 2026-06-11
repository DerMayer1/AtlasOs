"""Addressable artifact store: every number an engine emits lives here.

Layout: <root>/<run_id>/<name> ; artifact_id = "<run_id>/<name>".
Artifacts are write-once: an engine cannot overwrite a published artifact.
"""

from __future__ import annotations

from pathlib import Path

from atlas.platform.audit.snapshots import _sha256_file
from atlas.platform.contracts.schemas import Artifact, ArtifactKind

_KIND_BY_SUFFIX = {
    ".csv": ArtifactKind.CSV,
    ".parquet": ArtifactKind.PARQUET,
    ".json": ArtifactKind.JSON,
    ".png": ArtifactKind.PNG,
}


class ArtifactStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def publish(self, run_id: str, name: str, data: bytes) -> Artifact:
        suffix = Path(name).suffix.lower()
        if suffix not in _KIND_BY_SUFFIX:
            raise ValueError(f"unsupported artifact type {suffix!r} for {name!r}")
        run_dir = self.root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / name
        if path.exists():
            raise FileExistsError(f"artifact {run_id}/{name} already published")
        path.write_bytes(data)
        return Artifact(
            artifact_id=f"{run_id}/{name}",
            run_id=run_id,
            name=name,
            kind=_KIND_BY_SUFFIX[suffix],
            path=str(path),
            sha256=_sha256_file(path),
            size_bytes=path.stat().st_size,
        )

    def open_path(self, artifact_id: str) -> Path:
        path = self.root / artifact_id
        if not path.exists():
            raise FileNotFoundError(f"artifact {artifact_id!r} not found")
        return path
