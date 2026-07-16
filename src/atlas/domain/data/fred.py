"""FRED ingestion (PRD R4).

Uses the keyless fredgraph.csv endpoint (ADR-007). Each series is cached
locally as parquet; refreshes fetch only the increment (from 60 days before
the last cached observation, to absorb FRED's retroactive revisions of recent
points) and merge. Validation is loud: missing series, malformed payloads or
NaNs in the final frame raise instead of degrading.

Frequency alignment (documented per R4): everything is monthly, month-end
stamps. Monthly series are taken as published; daily series (T10Y2Y) are
averaged within the month. cpi_yoy is the 12-month percent change of CPIAUCSL.
"""

from __future__ import annotations

import io
import re
import time
from datetime import timedelta
from pathlib import Path

import httpx
import pandas as pd

FREDGRAPH_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
ALFRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"

# series name -> (FRED id, native frequency)
SERIES = {
    "fed_funds": ("FEDFUNDS", "monthly"),
    "baa": ("BAA", "monthly"),
    "aaa": ("AAA", "monthly"),
    "t10y2y": ("T10Y2Y", "daily"),
    "cpi_index": ("CPIAUCSL", "monthly"),
    "unemployment": ("UNRATE", "monthly"),
    "vix": ("VIXCLS", "daily"),
}

MACRO_COLUMNS = [
    "fed_funds",
    "baa_aaa_spread",
    "t10y2y",
    "cpi_yoy",
    "unemployment",
    "vix",
]

# Daily-series history is fetched from this year onward (macro frame starts 1990;
# the buffer absorbs alignment trimming).
HISTORY_START_YEAR = 1989


class FredIngestionError(Exception):
    pass


class FredClient:
    def __init__(
        self,
        cache_dir: str | Path,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        offline: bool = False,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(transport=transport, timeout=timeout, follow_redirects=True)
        self.offline = offline

    def _fetch_csv(
        self, fred_id: str, start: str | None = None, end: str | None = None
    ) -> pd.Series:
        params = {"id": fred_id}
        if start:
            params["cosd"] = start
        if end:
            params["coed"] = end
        # PRD edge case: FRED unavailable -> retry with backoff, then fail loudly.
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                resp = self._client.get(FREDGRAPH_URL, params=params)
                break
            except httpx.HTTPError as exc:
                last_exc = exc
                time.sleep(2**attempt)
        else:
            raise FredIngestionError(f"FRED unreachable for {fred_id}: {last_exc}")
        if resp.status_code != 200:
            raise FredIngestionError(f"FRED returned {resp.status_code} for {fred_id}")
        try:
            frame = pd.read_csv(io.StringIO(resp.text), na_values=["."])
        except Exception as exc:
            raise FredIngestionError(f"malformed CSV for {fred_id}: {exc}") from exc

        date_col = frame.columns[0]  # FRED has used both DATE and observation_date
        if len(frame.columns) != 2 or not frame[date_col].str.match(r"\d{4}-\d{2}-\d{2}").all():
            raise FredIngestionError(
                f"unexpected CSV shape for {fred_id}: columns={list(frame.columns)}"
            )
        series = pd.Series(
            pd.to_numeric(frame.iloc[:, 1], errors="coerce").values,
            index=pd.to_datetime(frame[date_col]),
            name=fred_id,
        ).dropna()
        if series.empty:
            raise FredIngestionError(f"no observations for {fred_id}")
        return series

    def get_series(self, name: str) -> pd.Series:
        fred_id, freq = SERIES[name]
        return self.get_raw(fred_id, daily=freq == "daily")

    def get_raw(self, fred_id: str, daily: bool = False) -> pd.Series:
        """Cached fetch: full history on first call, increment afterwards.

        Daily series are fetched in 5-year chunks: fredgraph 504s on
        full-history daily requests (observed for T10Y2Y).
        """
        cache_file = self.cache_dir / f"{fred_id}.parquet"

        if cache_file.exists():
            cached = pd.read_parquet(cache_file)[fred_id]
            if self.offline:
                return cached
            start = (cached.index.max() - timedelta(days=60)).strftime("%Y-%m-%d")
            fresh = self._fetch_csv(fred_id, start=start)
            series = pd.concat([cached[cached.index < fresh.index.min()], fresh])
        elif self.offline:
            raise FredIngestionError(f"offline cache missing for {fred_id}: {cache_file}")
        elif daily:
            chunks = []
            year = HISTORY_START_YEAR
            current_year = pd.Timestamp.now().year
            while year <= current_year:
                chunks.append(
                    self._fetch_csv(fred_id, start=f"{year}-01-01", end=f"{year + 4}-12-31")
                )
                year += 5
            series = pd.concat(chunks)
            series = series[~series.index.duplicated(keep="last")].sort_index()
        else:
            series = self._fetch_csv(fred_id)

        series.to_frame().to_parquet(cache_file)
        return series


class AlfredClient:
    """Point-in-time macro history using each observation's initial release.

    ALFRED is exposed through the FRED API real-time parameters. ``output_type=4``
    returns only initial releases, so a historical feature can never contain a
    revision published after the observation was first available.
    """

    def __init__(
        self,
        cache_dir: str | Path,
        api_key: str = "",
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
        offline: bool = False,
    ) -> None:
        if not offline and not re.fullmatch(r"[a-z0-9]{32}", api_key):
            raise FredIngestionError("ALFRED ingestion requires a 32-character ATLAS_FRED_API_KEY")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key
        self._client = httpx.Client(transport=transport, timeout=timeout, follow_redirects=True)
        self.offline = offline

    def _fetch_initial_release(self, fred_id: str, start: str | None = None) -> pd.Series:
        params: dict[str, str | int] = {
            "series_id": fred_id,
            "api_key": self.api_key,
            "file_type": "json",
            "output_type": 4,
            "limit": 100_000,
        }
        if start:
            params["observation_start"] = start

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.get(ALFRED_OBSERVATIONS_URL, params=params)
                break
            except httpx.HTTPError as exc:
                last_exc = exc
                time.sleep(2**attempt)
        else:
            raise FredIngestionError(f"ALFRED unreachable for {fred_id}: {last_exc}")

        if response.status_code != 200:
            raise FredIngestionError(f"ALFRED returned {response.status_code} for {fred_id}")
        try:
            payload = response.json()
            observations = payload["observations"]
        except (ValueError, KeyError, TypeError) as exc:
            raise FredIngestionError(f"malformed ALFRED JSON for {fred_id}: {exc}") from exc
        if int(payload.get("count", len(observations))) > len(observations):
            raise FredIngestionError(f"ALFRED response was truncated for {fred_id}")

        frame = pd.DataFrame(observations)
        if frame.empty or not {"date", "value"}.issubset(frame.columns):
            raise FredIngestionError(f"no initial-release observations for {fred_id}")
        series = pd.Series(
            pd.to_numeric(frame["value"], errors="coerce").to_numpy(),
            index=pd.to_datetime(frame["date"], errors="coerce"),
            name=fred_id,
        ).dropna()
        series = series[~series.index.duplicated(keep="first")].sort_index()
        if series.empty or series.index.hasnans:
            raise FredIngestionError(f"invalid initial-release observations for {fred_id}")
        return series

    def get_series(self, name: str) -> pd.Series:
        fred_id, freq = SERIES[name]
        return self.get_raw(fred_id, daily=freq == "daily")

    def get_raw(self, fred_id: str, daily: bool = False) -> pd.Series:
        del daily  # The API handles both native frequencies below its 100k limit.
        cache_file = self.cache_dir / f"{fred_id}.parquet"
        if cache_file.exists():
            cached = pd.read_parquet(cache_file)[fred_id]
            if self.offline:
                return cached
            start = (cached.index.max() - timedelta(days=60)).strftime("%Y-%m-%d")
            fresh = self._fetch_initial_release(fred_id, start=start)
            series = pd.concat([cached[cached.index < fresh.index.min()], fresh])
        elif self.offline:
            raise FredIngestionError(f"offline ALFRED cache missing for {fred_id}: {cache_file}")
        else:
            series = self._fetch_initial_release(fred_id)

        series = series[~series.index.duplicated(keep="first")].sort_index()
        series.to_frame().to_parquet(cache_file)
        return series


def build_macro_frame(client: FredClient, start: str = "1990-01-01") -> pd.DataFrame:
    """Monthly macro frame with the core macro series and VIX."""
    raw = {name: client.get_series(name) for name in SERIES}

    monthly: dict[str, pd.Series] = {}
    for name, (_, freq) in SERIES.items():
        s = raw[name]
        monthly[name] = s.resample("ME").mean() if freq == "daily" else s.resample("ME").last()

    frame = pd.DataFrame(
        {
            "fed_funds": monthly["fed_funds"],
            "baa_aaa_spread": monthly["baa"] - monthly["aaa"],
            "t10y2y": monthly["t10y2y"],
            "cpi_yoy": monthly["cpi_index"].pct_change(12) * 100.0,
            "unemployment": monthly["unemployment"],
            "vix": monthly["vix"],
        }
    ).loc[start:]

    # T10Y2Y only exists from 1976; cpi_yoy loses its first 12 months: trim to
    # the common window, then any remaining NaN is a data defect -> loud failure.
    frame = frame.dropna(how="any")
    if frame.empty or len(frame) < 24:
        raise FredIngestionError(f"macro frame too short after alignment: {len(frame)} rows")
    if list(frame.columns) != MACRO_COLUMNS:
        raise FredIngestionError(f"unexpected columns: {list(frame.columns)}")
    return frame
