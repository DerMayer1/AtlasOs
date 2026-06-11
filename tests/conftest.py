import pytest

from atlas.domain.data.synthetic import make_macro_frame
from atlas.platform.audit.artifacts import ArtifactStore
from atlas.platform.audit.snapshots import SnapshotStore

__all__ = ["make_macro_frame"]


@pytest.fixture
def snapshot_store(tmp_path) -> SnapshotStore:
    return SnapshotStore(tmp_path / "snapshots")


@pytest.fixture
def artifact_store(tmp_path) -> ArtifactStore:
    return ArtifactStore(tmp_path / "artifacts")


@pytest.fixture
def macro_snapshot(snapshot_store):
    manifest = snapshot_store.create(
        {"macro": make_macro_frame()}, sources=["synthetic://test"]
    )
    return manifest
