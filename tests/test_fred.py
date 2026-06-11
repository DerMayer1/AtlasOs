"""FRED ingestion tests over a mocked transport — no network (PRD R4)."""

import httpx
import pandas as pd
import pytest

from atlas.domain.data.fred import (
    MACRO_COLUMNS,
    SERIES,
    FredClient,
    FredIngestionError,
    build_macro_frame,
)


def fake_csv(fred_id: str, start: str = "1990-01-01", periods: int = 480, freq: str = "MS") -> str:
    idx = pd.date_range(start, periods=periods, freq=freq)
    lines = [f"DATE,{fred_id}"]
    base = {"FEDFUNDS": 2.5, "BAA": 5.5, "AAA": 4.5, "T10Y2Y": 1.0,
            "CPIAUCSL": 200.0, "UNRATE": 5.0, "VIXCLS": 18.0}[fred_id]
    for i, d in enumerate(idx):
        value = base + (i % 7) * 0.1 + (i * 0.05 if fred_id == "CPIAUCSL" else 0)
        lines.append(f"{d.date()},{value:.2f}")
    return "\n".join(lines) + "\n"


def make_transport(missing_every: int | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        fred_id = dict(request.url.params)["id"]
        freq = "D" if fred_id in ("T10Y2Y", "VIXCLS") else "MS"
        periods = 12000 if freq == "D" else 480
        body = fake_csv(fred_id, periods=periods, freq=freq)
        if missing_every:  # inject FRED's "." missing markers
            lines = body.splitlines()
            lines = [
                line if i == 0 or i % missing_every else line.rsplit(",", 1)[0] + ",."
                for i, line in enumerate(lines)
            ]
            body = "\n".join(lines)
        return httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


def test_build_macro_frame_shape_and_no_nans(tmp_path):
    client = FredClient(tmp_path, transport=make_transport())
    frame = build_macro_frame(client)
    assert list(frame.columns) == MACRO_COLUMNS
    assert not frame.isna().any().any()
    assert len(frame) >= 24


def test_missing_values_are_dropped_not_propagated(tmp_path):
    client = FredClient(tmp_path, transport=make_transport(missing_every=10))
    frame = build_macro_frame(client)
    assert not frame.isna().any().any()


def test_cache_written_and_merged(tmp_path):
    client = FredClient(tmp_path, transport=make_transport())
    s1 = client.get_series("fed_funds")
    assert (tmp_path / "FEDFUNDS.parquet").exists()
    s2 = client.get_series("fed_funds")  # second call goes through merge path
    pd.testing.assert_series_equal(s1, s2)


def test_http_error_fails_loudly(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(503))
    client = FredClient(tmp_path, transport=transport)
    with pytest.raises(FredIngestionError, match="503"):
        client.get_series("fed_funds")


def test_malformed_payload_fails_loudly(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, text="<html>maintenance"))
    client = FredClient(tmp_path, transport=transport)
    with pytest.raises(FredIngestionError):
        client.get_series("fed_funds")


def test_series_map_covers_required_columns():
    assert set(SERIES) == {"fed_funds", "baa", "aaa", "t10y2y", "cpi_index", "unemployment"}
