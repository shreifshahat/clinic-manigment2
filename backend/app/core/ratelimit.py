"""Shared rate limiter (E-05).

The first implementation kept the counters in the memory of a single process,
which meant the effective limit multiplied by the number of worker processes.
This module offers two modes:

``memory``    – in-process counters (fast, exact for a single process).
``database``  – counters stored in PostgreSQL, so the limit is identical for
                every worker and every instance. This is the production
                default.

The database mode stores **no personal data**: the key is a salted hash of the
client address, and only a counter and a time window are kept.
"""

from __future__ import annotations

import hashlib
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

#: Salt used to hash the client address before it is used as a key.
HASH_SALT = os.environ.get("RATE_LIMIT_SALT", "clinic-rate-limit")


def client_key(client_host: str, path_group: str) -> str:
    """A non-reversible key for a client + route group."""
    digest = hashlib.sha256(f"{HASH_SALT}|{client_host}|{path_group}".encode()).hexdigest()
    return f"{path_group}:{digest[:32]}"


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int


class MemoryRateLimiter:
    """Fixed-window limiter kept in the memory of the process."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self._limit = limit
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def check(self, key: str) -> RateLimitResult:
        now = time.monotonic()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self._window:
            bucket.popleft()
        if len(bucket) >= self._limit:
            return RateLimitResult(False, self._limit, 0, self._window)
        bucket.append(now)
        return RateLimitResult(True, self._limit, self._limit - len(bucket), 0)

    def reset(self) -> None:
        self._hits.clear()


class DatabaseRateLimiter:
    """Fixed-window limiter shared by every process (PostgreSQL)."""

    def __init__(self, engine: AsyncEngine, limit: int, window_seconds: int = 60) -> None:
        self._engine = engine
        self._limit = limit
        self._window = window_seconds

    async def check(self, key: str) -> RateLimitResult:
        """Count this request in the current minute window (shared by all workers)."""
        async with self._engine.connect() as connection, connection.begin():
            used = (
                await connection.execute(
                    text(
                        """
                            insert into rate_limit_counters (key, window_start, counter)
                            values (:key, date_trunc('minute', now()), 1)
                            on conflict (key, window_start) do update
                                set counter = rate_limit_counters.counter + 1
                            returning counter
                            """
                    ),
                    {"key": key},
                )
            ).scalar_one()
        count = int(used)
        if count > self._limit:
            retry_after = max(60 - int(time.time() % 60), 1)
            return RateLimitResult(False, self._limit, 0, retry_after)
        return RateLimitResult(True, self._limit, max(self._limit - count, 0), 0)
