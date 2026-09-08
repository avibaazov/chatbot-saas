from datetime import datetime, timezone
from enum import Enum

from pydantic import Field

from app.models.common import MongoBaseModel, PyObjectId


class DocumentStatus(str, Enum):
    """The status field the dashboard UI polls during async ingestion (AGENTS.md §5 step 4)."""

    pending = "pending"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(MongoBaseModel):
    bot_id: PyObjectId
    filename: str
    source_type: str  # "upload" | "url" | "text"
    url: str | None = None  # set when source_type == "url"
    status: DocumentStatus = DocumentStatus.pending
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
