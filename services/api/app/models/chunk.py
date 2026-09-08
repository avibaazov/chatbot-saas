from datetime import datetime, timezone

from pydantic import Field

from app.models.common import MongoBaseModel, PyObjectId


class Chunk(MongoBaseModel):
    """One embedded slice of a document. `bot_id` is denormalized from the parent
    document so retrieval can filter by bot without a join/lookup on the hot path.
    """

    document_id: PyObjectId
    bot_id: PyObjectId
    chunk_index: int
    text: str
    embedding: list[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
