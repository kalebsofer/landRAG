from rank_bm25 import BM25Okapi

from landrag.core.pinecone import build_metadata_filter, get_pinecone_index
from landrag.ingestion.embedder import embed_query
from landrag.search.reranker import rerank


def bm25_rescore(texts: list[str], query: str) -> list[float]:
    tokenized_corpus = [doc.lower().split() for doc in texts]
    tokenized_query = query.lower().split()
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)
    return scores.tolist()


def combine_scores(
    dense_scores: list[float],
    bm25_scores: list[float],
    dense_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> list[float]:
    # Normalize BM25 scores to 0-1 range
    max_bm25 = max(bm25_scores) if bm25_scores and max(bm25_scores) > 0 else 1.0
    normalized_bm25 = [s / max_bm25 for s in bm25_scores]

    return [dense_weight * d + bm25_weight * b for d, b in zip(dense_scores, normalized_bm25)]


def execute_search_pipeline(query: str, filters=None, limit: int = 10) -> dict:
    """Execute the full search pipeline: embed → Pinecone → BM25 → rerank."""
    query_embedding = embed_query(query)

    index = get_pinecone_index()
    pinecone_filter = build_metadata_filter(filters)
    pinecone_results = index.query(
        vector=query_embedding,
        top_k=20,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None,
    )

    if not pinecone_results.matches:
        return {"results": [], "total_estimate": 0}

    texts = [m.metadata.get("text", "") for m in pinecone_results.matches]
    dense_scores = [m.score for m in pinecone_results.matches]
    chunk_ids = [m.id for m in pinecone_results.matches]

    bm25_scores_list = bm25_rescore(texts, query)
    combine_scores(dense_scores, bm25_scores_list)
    reranked = rerank(query, texts, top_n=limit)

    results = []
    for r in reranked:
        idx = r["index"]
        match = pinecone_results.matches[idx]
        meta = match.metadata
        results.append({
            "chunk_id": chunk_ids[idx],
            "content": texts[idx],
            "score": r["score"],
            "highlight": texts[idx][:200],
            "document_title": meta.get("document_title", ""),
            "document_type": meta.get("document_type", ""),
            "project_name": meta.get("project_name", ""),
            "project_reference": meta.get("project_reference", ""),
            "project_type": meta.get("project_type", ""),
            "topic": meta.get("topic"),
            "source_url": meta.get("source_url", ""),
            "page_start": meta.get("page_start"),
            "page_end": meta.get("page_end"),
        })

    return {"results": results, "total_estimate": len(results)}
