"""FRED ingestion tests over a mocked transport — no network (PRD R4)."""

import httpx
import pandas as pd
import pytest

from atlas.domain.data.fred import (
    MACRO_COLUMNS,
    SERIES,
    AlfredClient,
    FredClient,
    FredIngestionError,
    build_macro_frame,
)

ALFRED_KEY = "a" * 32


def fake_csv(fred_id: str, start: str = "1990-01-01", periods: int = 480, freq: str = "MS") -> str:
    idx = pd.date_range(start, periods=periods, freq=freq)
    lines = [f"DATE,{fred_id}"]
    base = {
        "FEDFUNDS": 2.5,
        "BAA": 5.5,
        "AAA": 4.5,
        "T10Y2Y": 1.0,
        "CPIAUCSL": 200.0,
        "UNRATE": 5.0,
        "VIXCLS": 18.0,
    }[fred_id]
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


def test_offline_mode_reads_cache_without_network(tmp_path):
    online = FredClient(tmp_path, transport=make_transport())
    expected = online.get_series("fed_funds")
    offline = FredClient(
        tmp_path,
        transport=httpx.MockTransport(lambda request: httpx.Response(503)),
        offline=True,
    )
    pd.testing.assert_series_equal(offline.get_series("fed_funds"), expected)


def test_offline_mode_fails_when_cache_is_missing(tmp_path):
    client = FredClient(tmp_path, offline=True)
    with pytest.raises(FredIngestionError, match="offline cache missing"):
        client.get_series("fed_funds")


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
    assert set(SERIES) == {
        "fed_funds",
        "baa",
        "aaa",
        "t10y2y",
        "cpi_index",
        "unemployment",
        "vix",
    }


def test_alfred_fetches_initial_releases_and_caches_them(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        assert params["output_type"] == "4"
        assert params["api_key"] == ALFRED_KEY
        return httpx.Response(
            200,
            json={
                "count": 3,
                "observations": [
                    {"date": "2020-01-01", "value": "1.0", "realtime_start": "2020-02-01"},
                    {"date": "2020-02-01", "value": "1.1", "realtime_start": "2020-03-01"},
                    {"date": "2020-03-01", "value": ".", "realtime_start": "2020-04-01"},
                ],
            },
        )

    client = AlfredClient(tmp_path, ALFRED_KEY, transport=httpx.MockTransport(handler))
    series = client.get_raw("FEDFUNDS")

    assert series.to_dict() == {
        pd.Timestamp("2020-01-01"): 1.0,
        pd.Timestamp("2020-02-01"): 1.1,
    }
    assert (tmp_path / "FEDFUNDS.parquet").exists()


def test_alfred_requires_key_but_allows_offline_cache(tmp_path):
    with pytest.raises(FredIngestionError, match="ATLAS_FRED_API_KEY"):
        AlfredClient(tmp_path)

    expected = pd.Series([1.0], index=pd.DatetimeIndex(["2020-01-01"]), name="FEDFUNDS")
    expected.to_frame().to_parquet(tmp_path / "FEDFUNDS.parquet")
    offline = AlfredClient(tmp_path, offline=True)
    pd.testing.assert_series_equal(offline.get_raw("FEDFUNDS"), expected)
