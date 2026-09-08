"""Minimal in-memory rate limiter. Fixed-window counter per key, process-local — same
caveat as InMemoryQueue: doesn't survive restarts, doesn't work across multiple instances.
Good enough to actually enforce a limit on the widget endpoint today; swap for a
Redis-backed limiter (INCR + EXPIRE) once Redis exists, same call signature.
"""

from __future__ import annotations

import time

_WINDOW_SECONDS = 60
_buckets: dict[str, tuple[int, float]] = {}  # key -> (count, window_start)


def is_rate_limited(key: str, *, max_per_minute: int) -> bool:
    now = time.monotonic()
    count, window_start = _buckets.get(key, (0, now))

    if now - window_start >= _WINDOW_SECONDS:
        count, window_start = 0, now

    count += 1
    _buckets[key] = (count, window_start)

    return count > max_per_minute
