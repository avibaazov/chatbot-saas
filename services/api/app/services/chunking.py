"""Naive fixed-size chunker with overlap. Good enough to unblock the ingestion pipeline;
swap for something token-aware (tiktoken, or the embeddings provider's own tokenizer)
before this needs to handle real documents at scale.
"""


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        chunks.append(text[start : start + chunk_size])
        start += step
    return chunks
