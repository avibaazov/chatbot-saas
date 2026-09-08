"""Local User document is a thin join row keyed by Clerk's user id — see app/models/user.py.
This upserts it lazily on first authenticated request rather than requiring a webhook,
so the API works standalone without also wiring Clerk webhooks yet.
"""

from app.models.user import User


async def get_or_create_user(users_col, clerk_user_id: str, email: str = "") -> dict:
    user = await users_col.find_one({"clerk_user_id": clerk_user_id})
    if user:
        return user

    doc = User(clerk_user_id=clerk_user_id, email=email).model_dump(by_alias=True, exclude={"id"})
    result = await users_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
