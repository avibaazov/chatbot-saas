"""Background job queue abstraction. InMemoryQueue runs the job inline (awaited directly)
so the request/response contract — a status field the UI polls — is correct end to end
before Redis exists. Swap for a RedisQueue (Arq) once REDIS_URL is set; nothing that calls
enqueue() needs to change.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol


class JobQueue(Protocol):
    async def enqueue(self, job: Callable[[], Awaitable[None]]) -> None: ...


class InMemoryQueue:
    """NOT for production: no retries, no persistence, no cross-process workers, and the
    caller's request blocks until the job finishes. Exists to make the ingestion pipeline
    runnable and testable before Redis is wired up (AGENTS.md §4).
    """

    async def enqueue(self, job: Callable[[], Awaitable[None]]) -> None:
        await job()


def get_queue(settings) -> JobQueue:
    if settings.redis_url:
        raise NotImplementedError(
            "REDIS_URL is set but the Redis/Arq queue isn't wired up yet."
        )
    return InMemoryQueue()
