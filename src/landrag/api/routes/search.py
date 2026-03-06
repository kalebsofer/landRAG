from fastapi import APIRouter

from landrag.models.schemas import SearchRequest

router = APIRouter(prefix="/v1")


def execute_search(request: SearchRequest) -> dict:
    """Execute the full search pipeline. Wired up to real retrieval in integration."""
    from landrag.core.pinecone import build_metadata_filter, get_pinecone_index
    from landrag.ingestion.embedder import embed_query
    from landrag.search.reranker import rerank
    from landrag.search.retrieval import bm25_rescore, combine_scores

    # 1. Embed query
    query_embedding = embed_query(request.query)

    # 2. Pinecone search
    index = get_pinecone_index()
    pinecone_filter = build_metadata_filter(request.filters)
    pinecone_results = index.query(
        vector=query_embedding,
        top_k=20,
        include_metadata=True,
        filter=pinecone_filter if pinecone_filter else None,
    )

    if not pinecone_results.matches:
        return {"results": [], "total_estimate": 0}

    # 3. Extract texts and dense scores
    texts = [m.metadata.get("text", "") for m in pinecone_results.matches]
    dense_scores = [m.score for m in pinecone_results.matches]
    chunk_ids = [m.id for m in pinecone_results.matches]

    # 4. BM25 re-score
    bm25_scores = bm25_rescore(texts, request.query)

    # 5. Combine scores (used for fallback ranking; reranker overrides order)
    combine_scores(dense_scores, bm25_scores)

    # 6. Rerank top candidates
    reranked = rerank(request.query, texts, top_n=request.limit)

    # 7. Build response using reranked order
    results = []
    for r in reranked:
        idx = r["index"]
        match = pinecone_results.matches[idx]
        meta = match.metadata
        results.append(
            {
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
            }
        )

    return {"results": results, "total_estimate": len(results)}


@router.post("/search")
async def search(request: SearchRequest) -> dict:
    return execute_search(request)
