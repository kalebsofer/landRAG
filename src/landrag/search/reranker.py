import cohere

from landrag.core.config import get_settings


def get_cohere_client() -> cohere.ClientV2:
    settings = get_settings()
    return cohere.ClientV2(api_key=settings.cohere_api_key)


def rerank(query: str, texts: list[str], top_n: int = 10) -> list[dict]:
    client = get_cohere_client()
    response = client.rerank(
        model="rerank-v3.5",
        query=query,
        documents=texts,
        top_n=top_n,
    )
    return [{"index": r.index, "score": r.relevance_score} for r in response.results]
