"""The ONLY file that talks to https://api.typesafe.ai/v1/systemone.

Everything measured in docs/research/jev-measured-benchmarks.md is encoded here:
pack questions into one request (latency is flat in question count), 100-way
concurrency over one AsyncClient, backoff on 429/529.

The key is read from .env via python-dotenv and never logged.
"""
from __future__ import annotations

import asyncio
import os
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


class JevUnavailable(RuntimeError):
    """Network, auth or upstream failure. Routes catch this and serve the frozen cache."""


class Jev:
    def __init__(self, key: str | None = None, concurrency: int = 100):
        self._key = key if key is not None else os.environ.get("JEV_API_KEY", "")
        self._concurrency = concurrency
        self._client: httpx.AsyncClient | None = None
        self._sem: asyncio.Semaphore | None = None
        # running totals, for honest on-screen counters
        self.calls = 0
        self.judgments = 0
        self.input_tokens = 0

    # -- lifecycle -------------------------------------------------------
    def _ensure(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(
                limits=httpx.Limits(max_connections=150, max_keepalive_connections=150),
                timeout=httpx.Timeout(120.0),
            )
        if self._sem is None:
            self._sem = asyncio.Semaphore(self._concurrency)

    def prepare(self) -> None:
        """Build the AsyncClient (and its SSL context) WITHOUT sending anything.

        httpx builds the SSLContext synchronously in the constructor and loading the CA
        bundle costs ~0.5s once per process. If that lands inside a timed fan-out it looks
        like the second request was fired half a second late, which is a lie about the
        parallelism. Callers that publish a measurement call this first, so what they time
        is the fan-out and nothing else. No network traffic happens here.
        """
        self._ensure()

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def configured(self) -> bool:
        return bool(self._key)

    # -- the one call ----------------------------------------------------
    async def ask(self, state, questions: dict) -> dict:
        """One request. Every question is evaluated in parallel against one shared state."""
        if not self._key:
            raise JevUnavailable("JEV_API_KEY is not set")
        self._ensure()
        payload = {"model": MODEL, "state": state, "questions": questions}
        headers = {"Authorization": f"Bearer {self._key}", "Content-Type": "application/json"}
        last = "unknown"
        assert self._sem is not None and self._client is not None
        async with self._sem:
            for attempt in range(4):
                try:
                    r = await self._client.post(URL, json=payload, headers=headers)
                except (httpx.TransportError, httpx.HTTPError) as e:
                    last = f"{type(e).__name__}"
                    await asyncio.sleep(0.4 * (attempt + 1))
                    continue
                if r.status_code in (429, 529):
                    last = f"HTTP {r.status_code}"
                    await asyncio.sleep(1.2 * (attempt + 1))
                    continue
                if r.status_code >= 400:
                    raise JevUnavailable(f"HTTP {r.status_code} from Jev")
                data = r.json()
                self.calls += 1
                self.judgments += len(data.get("answers", {}))
                self.input_tokens += data.get("usage", {}).get("input_tokens", 0)
                return data
        raise JevUnavailable(f"Jev unreachable after retries ({last})")

    async def batch(self, jobs: list[tuple]) -> list[dict]:
        """jobs = [(state, questions), ...] - fired concurrently."""
        if not jobs:
            return []
        return await asyncio.gather(*(self.ask(s, q) for s, q in jobs))

    async def ping(self, timeout: float = 8.0) -> bool:
        """Cheap liveness probe used by /api/health. Never raises."""
        try:
            await asyncio.wait_for(
                self.ask("warm", {"w": {"type": "noul", "instructions": "Is this reachable?",
                                        "criteria": {"true": "yes", "false": "no"}}}),
                timeout=timeout,
            )
            return True
        except Exception:
            return False


JEV = Jev()


# -- answer readers: one place that knows Jev's response shape ------------
def noul(a: dict, k: str, default: float = 0.0) -> float:
    try:
        return float(a[k]["noul"])
    except Exception:
        return default


def score(a: dict, k: str, default: float = 0.0) -> float:
    try:
        return float(a[k]["score"])
    except Exception:
        return default


def level(a: dict, k: str, default: str = "") -> str:
    try:
        x = a[k]
        return str(x["legend"][str(round(x["score"]))])
    except Exception:
        return default


def choice(a: dict, k: str, default: str = "") -> str:
    try:
        return str(a[k]["choice"])
    except Exception:
        return default


def conf(a: dict, k: str, default: float = 0.0) -> float:
    """Confidence for any answer type. nouls carry none, so use max(p, 1-p)."""
    try:
        x = a[k]
        if "confidence" in x:
            return float(x["confidence"])
        if x.get("type") == "noul":
            p = float(x["noul"])
            return max(p, 1.0 - p)
    except Exception:
        pass
    return default


def timed():
    t = time.perf_counter()
    return lambda: int((time.perf_counter() - t) * 1000)
