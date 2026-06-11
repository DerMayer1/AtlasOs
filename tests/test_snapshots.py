import pandas as pd
import pytest

from atlas.platform.audit.snapshots import (
    SnapshotIntegrityError,
    SnapshotNotFoundError,
)
from tests.conftest import make_macro_frame


def test_create_and_load_roundtrip(snapshot_store):
    frame = make_macro_frame()
    manifest = snapshot_store.create({"macro": frame}, sources=["synthetic://test"])
    loaded = snapshot_store.load(manifest.snapshot_id)
    # parquet does not persist the DatetimeIndex freq attribute (metadata only)
    pd.testing.assert_frame_equal(loaded["macro"], frame, check_freq=False)


def test_same_content_same_id(snapshot_store):
    m1 = snapshot_store.create({"macro": make_macro_frame()}, sources=["a"])
    m2 = snapshot_store.create({"macro": make_macro_frame()}, sources=["b"])
    assert m1.snapshot_id == m2.snapshot_id


def test_different_content_different_id(snapshot_store):
    m1 = snapshot_store.create({"macro": make_macro_frame(seed=1)}, sources=["a"])
    m2 = snapshot_store.create({"macro": make_macro_frame(seed=2)}, sources=["a"])
    assert m1.snapshot_id != m2.snapshot_id


def test_tampering_fails_loudly(snapshot_store):
    manifest = snapshot_store.create({"macro": make_macro_frame()}, sources=["a"])
    parquet = snapshot_store.root / manifest.snapshot_id / "macro.parquet"
    parquet.write_bytes(parquet.read_bytes() + b"corruption")
    with pytest.raises(SnapshotIntegrityError, match="hash mismatch"):
        snapshot_store.load(manifest.snapshot_id)


def test_missing_table_file_fails_loudly(snapshot_store):
    manifest = snapshot_store.create({"macro": make_macro_frame()}, sources=["a"])
    (snapshot_store.root / manifest.snapshot_id / "macro.parquet").unlink()
    with pytest.raises(SnapshotIntegrityError, match="missing"):
        snapshot_store.load(manifest.snapshot_id)


def test_unknown_snapshot(snapshot_store):
    with pytest.raises(SnapshotNotFoundError):
        snapshot_store.load("snap_doesnotexist00")


def test_empty_snapshot_rejected(snapshot_store):
    with pytest.raises(ValueError):
        snapshot_store.create({}, sources=["a"])
