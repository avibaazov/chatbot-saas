from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.common import MongoBaseModel, PyObjectId


class BotConfig(BaseModel):
    """User-editable behavior/appearance. Kept as a nested object so the dashboard can
    PATCH the whole thing at once without touching ownership/auth fields.
    """

    system_prompt: str = "You are a helpful assistant."
    model_tier: str = "haiku"  # "haiku" | "sonnet" — see AGENTS.md §4
    display_name: str = "Assistant"
    primary_color: str = "#000000"


class Bot(MongoBaseModel):
    owner_user_id: PyObjectId
    name: str
    config: BotConfig = Field(default_factory=BotConfig)

    # Widget auth — public site key + domain allow-list, never cookies. See AGENTS.md §3.
    site_key: str
    allowed_domains: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
