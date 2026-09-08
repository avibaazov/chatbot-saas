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
    font_size: str = "medium"  # "small" | "medium" | "large" — widget maps these to px


class Bot(MongoBaseModel):
    owner_user_id: PyObjectId
    name: str

    # The site the bot is trained on. Captured at creation, ingested once automatically,
    # and re-crawled on demand from the dashboard. Empty only on bots created before this
    # field existed. Its hostname seeds allowed_domains so the embed works on that site
    # (and in the dashboard preview) without the user hand-adding a domain.
    website_url: str = ""

    config: BotConfig = Field(default_factory=BotConfig)

    # Widget auth — public site key + domain allow-list, never cookies. See AGENTS.md §3.
    site_key: str
    allowed_domains: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
