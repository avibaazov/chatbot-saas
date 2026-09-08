from datetime import datetime, timezone

from pydantic import Field

from app.models.common import MongoBaseModel


class User(MongoBaseModel):
    """A dashboard user. Auth identity lives in Clerk — this document is our copy,
    keyed by Clerk's user id, that bots/ownership checks join against.
    """

    clerk_user_id: str
    email: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
