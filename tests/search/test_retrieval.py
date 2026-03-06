from landrag.search.retrieval import bm25_rescore, combine_scores


def test_bm25_rescore():
    texts = [
        "Noise conditions on wind farms near dwellings",
        "Ecology survey of bat populations",
        "Traffic management during construction",
    ]
    query = "noise conditions wind farms"
    scores = bm25_rescore(texts, query)
    assert len(scores) == 3
    # The noise-related text should score highest
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_combine_scores():
    dense_scores = [0.9, 0.7, 0.5]
    bm25_scores = [0.3, 0.8, 0.1]
    combined = combine_scores(dense_scores, bm25_scores, dense_weight=0.7, bm25_weight=0.3)
    assert len(combined) == 3
    # First: 0.9*0.7 + 0.3*0.3 = 0.72 (BM25 normalized: 0.3/0.8=0.375 -> 0.7*0.9 + 0.3*0.375 = 0.7425)
    # Second: 0.7*0.7 + 0.8*0.3 = 0.73 (BM25 normalized: 0.8/0.8=1.0 -> 0.7*0.7 + 0.3*1.0 = 0.79)
    assert combined[1] > combined[0]  # BM25 boost pushes second higher
