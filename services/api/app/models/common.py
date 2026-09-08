"""Shared model plumbing. Mongo's `_id` (an ObjectId) is represented on the Python side as
a plain str — good enough for our needs and avoids fighting pydantic v2 over BSON types.
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class MongoBaseModel(BaseModel):
    """Base for every document model. `id` maps to Mongo's `_id` via alias so
    `model_dump(by_alias=True)` produces a dict ready to insert/replace as-is.
    """

    id: PyObjectId | None = Field(default=None, alias="_id")

    model_config = ConfigDict(populate_by_name=True)
