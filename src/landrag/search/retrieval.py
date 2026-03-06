from rank_bm25 import BM25Okapi


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

    return [
        dense_weight * d + bm25_weight * b
        for d, b in zip(dense_scores, normalized_bm25)
    ]
