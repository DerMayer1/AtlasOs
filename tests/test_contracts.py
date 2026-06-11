import pytest
from pydantic import ValidationError

from atlas.platform.contracts.schemas import (
    CONTRACT_VERSION,
    AnalysisRequest,
    Artifact,
    ArtifactKind,
)


def test_request_defaults_carry_contract_version():
    req = AnalysisRequest(request_id="r1", engine="impairment", snapshot_id="snap_abc")
    assert req.contract_version == CONTRACT_VERSION
    assert req.params == {}


def test_artifact_requires_valid_sha256():
    with pytest.raises(ValidationError):
        Artifact(
            artifact_id="run/x.csv",
            run_id="run",
            name="x.csv",
            kind=ArtifactKind.CSV,
            path="x.csv",
            sha256="not-a-hash",
            size_bytes=10,
        )


def test_artifact_is_immutable():
    art = Artifact(
        artifact_id="run/x.csv",
        run_id="run",
        name="x.csv",
        kind=ArtifactKind.CSV,
        path="x.csv",
        sha256="0" * 64,
        size_bytes=10,
    )
    with pytest.raises(ValidationError):
        art.sha256 = "1" * 64  # type: ignore[misc]


def test_snapshot_id_is_mandatory():
    with pytest.raises(ValidationError):
        AnalysisRequest(request_id="r1", engine="impairment")  # type: ignore[call-arg]
