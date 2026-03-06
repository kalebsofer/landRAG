from openai import OpenAI

from landrag.core.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 100


def get_openai_client() -> OpenAI:
    settings = get_settings()
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    client = get_openai_client()
    all_embeddings: list[list[float]] = [[] for _ in texts]

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in response.data:
            all_embeddings[i + item.index] = item.embedding

    return all_embeddings


def embed_query(query: str) -> list[float]:
    return embed_texts([query])[0]
