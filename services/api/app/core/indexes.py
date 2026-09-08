"""Classic Mongo indexes for the collections in app/models/. Call create_indexes() once
at startup (see app/main.py lifespan).

NOT included here: the Atlas Vector Search index on chunks.embedding. Vector Search
indexes are a separate Atlas-managed resource (created via the Atlas UI, Admin API, or
Terraform), not a classic `create_index()` call — that gets set up in AGENTS.md §5 step 4
when we build ingestion.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("clerk_user_id", unique=True)

    await db.bots.create_index("owner_user_id")
    await db.bots.create_index("site_key", unique=True)

    await db.documents.create_index("bot_id")

    await db.chunks.create_index("document_id")
    await db.chunks.create_index("bot_id")

    await db.conversations.create_index("bot_id")
    await db.conversations.create_index([("bot_id", 1), ("visitor_id", 1)])
