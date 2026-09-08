"""Shared helpers for tests that exercise real Mongo queries (bots/documents CRUD —
ownership filtering is the thing under test, so it has to run against real Mongo, not a
fake). Deliberately NOT wired into conftest.py: only the integration test files opt in via
their own local autouse fixture, so the rest of the suite stays network-free.
"""

import app.core.db as db_module
from app.core.db import get_db

TEST_USER_PREFIX = "pytest_"


def reset_db_client() -> None:
    """Motor's client caches the asyncio event loop it was created on. pytest-asyncio
    gives each test function a fresh loop by default, so a client built in test N is dead
    by test N+1 ("Event loop is closed"). Call this at the start of every test that touches
    Mongo so get_client() rebuilds it fresh, bound to the current loop.
    """
    db_module._client = None


async def purge_test_data() -> None:
    """Deletes any user (and their bots/documents/chunks) whose clerk_user_id starts with
    TEST_USER_PREFIX. Run before AND after each test so a crashed previous run doesn't
    leave orphaned data behind for the next one.
    """
    db = get_db()
    async for user in db.users.find({"clerk_user_id": {"$regex": f"^{TEST_USER_PREFIX}"}}):
        owner_id = str(user["_id"])
        async for bot in db.bots.find({"owner_user_id": owner_id}):
            bot_id = str(bot["_id"])
            async for doc in db.documents.find({"bot_id": bot_id}):
                await db.chunks.delete_many({"document_id": str(doc["_id"])})
            await db.documents.delete_many({"bot_id": bot_id})
        await db.bots.delete_many({"owner_user_id": owner_id})
        await db.users.delete_one({"_id": user["_id"]})
