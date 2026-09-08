from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.common import MongoBaseModel, PyObjectId


class Message(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Conversation(MongoBaseModel):
    """Messages are embedded rather than a separate collection — conversations are
    short-lived and read/written as a whole, so there's no benefit to normalizing.
    """

    bot_id: PyObjectId
    visitor_id: str  # anonymous id the widget generates and stores client-side
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
