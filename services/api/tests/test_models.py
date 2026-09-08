from app.models import Bot, Chunk, Conversation, Document, DocumentStatus, Message, User


def test_bot_defaults_and_mongo_dict():
    bot = Bot(owner_user_id="000000000000000000000000", name="Test Bot", site_key="sk_test")
    assert bot.config.model_tier == "haiku"
    assert bot.allowed_domains == []

    data = bot.model_dump(by_alias=True, exclude={"id"})
    assert "_id" not in data
    assert data["name"] == "Test Bot"
    assert data["config"]["display_name"] == "Assistant"


def test_document_status_defaults_pending():
    doc = Document(bot_id="000000000000000000000000", filename="faq.pdf", source_type="upload")
    assert doc.status == DocumentStatus.pending
    assert doc.error is None


def test_chunk_round_trip_from_mongo_doc():
    # Simulates what motor hands back: a dict with a real _id.
    raw = {
        "_id": "111111111111111111111111",
        "document_id": "000000000000000000000000",
        "bot_id": "000000000000000000000000",
        "chunk_index": 0,
        "text": "hello world",
        "embedding": [0.1, 0.2, 0.3],
    }
    chunk = Chunk(**raw)
    assert chunk.id == "111111111111111111111111"
    assert len(chunk.embedding) == 3


def test_conversation_with_messages():
    convo = Conversation(
        bot_id="000000000000000000000000",
        visitor_id="visitor-abc",
        messages=[Message(role="user", content="hi")],
    )
    assert convo.messages[0].role == "user"


def test_user_requires_clerk_id_and_email():
    user = User(clerk_user_id="user_abc123", email="a@b.com")
    assert user.clerk_user_id == "user_abc123"
