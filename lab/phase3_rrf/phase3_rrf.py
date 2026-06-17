def rrf(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}

    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)

    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# dense search trả về: A tốt nhất về ngữ nghĩa
dense_results  = ["doc_A", "doc_B", "doc_C", "doc_D"]

# BM25 trả về: B tốt nhất về keyword
bm25_results   = ["doc_B", "doc_D", "doc_A", "doc_C"]

fused = rrf([dense_results, bm25_results])

for rank, (doc_id, score) in enumerate(fused, start=1):
    print(f"rank {rank}  score={score:.6f}  {doc_id}")
