"""Wiring that turns a document into an ingestion job.

Two layers per source type:

- ``run_*_ingestion`` — the coroutine that actually does the work (chunk -> embed ->
  upsert), with its own error handling. Safe to hand to a background task.
- ``enqueue_*_ingestion`` — schedule it. With ``settings.ingest_inline`` (the default:
  dev, tests, small single-instance deploys) the job is awaited before the request
  returns, so the response already carries a terminal status. Otherwise it goes to
  Starlette's ``BackgroundTasks`` and the request returns immediately with
  ``status=pending`` — which is what you want behind a host that imposes request
  timeouts. Neither path survives a process restart mid-job; that needs Redis + a real
  worker (AGENTS.md §4).

Kept out of app.services.ingestion (which stays dependency-light and unit-testable
against fake collections) — this module is the part that knows about settings, the web
fetcher, and the request lifecycle.
"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any

from fastapi import BackgroundTasks

from app.core.config import Settings
from app.services.embeddings import get_embeddings_provider
from app.services.ingestion import ingest_document, ingest_url
from app.services.web_fetch import fetch_url

logger = logging.getLogger(__name__)


async def run_text_ingestion(
    db: Any, settings: Settings, *, document_id: Any, text: str, bot_id: str
) -> None:
    embeddings = get_embeddings_provider(settings)
    try:
        await ingest_document(
            documents_col=db.documents,
            chunks_col=db.chunks,
            document_id=document_id,
            text=text,
            bot_id=bot_id,
            embeddings=embeddings,
        )
    except Exception:
        # ingest_document already recorded status=failed + error before re-raising (that
        # re-raise is for a real queue's retry/alerting). Here nothing upstream is waiting
        # on the result, so log and swallow rather than let a background task blow up.
        logger.exception("text ingestion failed for document %s", document_id)


async def run_url_ingestion(
    db: Any, settings: Settings, *, document_id: Any, url: str, bot_id: str
) -> None:
    embeddings = get_embeddings_provider(settings)
    try:
        await ingest_url(
            documents_col=db.documents,
            chunks_col=db.chunks,
            document_id=document_id,
            url=url,
            bot_id=bot_id,
            embeddings=embeddings,
            fetch=partial(fetch_url, allow_private=settings.ingest_allow_private_hosts),
        )
    except Exception:
        logger.exception("url ingestion failed for document %s", document_id)  # see run_text_ingestion


async def enqueue_text_ingestion(
    db: Any,
    settings: Settings,
    *,
    document_id: Any,
    text: str,
    bot_id: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    if settings.ingest_inline or background_tasks is None:
        await run_text_ingestion(db, settings, document_id=document_id, text=text, bot_id=bot_id)
    else:
        background_tasks.add_task(
            run_text_ingestion, db, settings, document_id=document_id, text=text, bot_id=bot_id
        )


async def enqueue_url_ingestion(
    db: Any,
    settings: Settings,
    *,
    document_id: Any,
    url: str,
    bot_id: str,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    if settings.ingest_inline or background_tasks is None:
        await run_url_ingestion(db, settings, document_id=document_id, url=url, bot_id=bot_id)
    else:
        background_tasks.add_task(
            run_url_ingestion, db, settings, document_id=document_id, url=url, bot_id=bot_id
        )
