def reciprocal_rank_fusion(
    rank_lists: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """RRF algorithm: https://arxiv.org/pdf/1602.07182.pdf

    Args:
        rank_lists: list of ranked lists, each is a list of document ids in ranked order
        k: hyperparameter to control how much to favor higher ranks

    Returns:
        list of (doc_id, score) sorted by score desc
    """
    rrf_scores: dict[str, float] = {}
        for rank_list in rank_lists:
        for rank, doc_id in enumerate(rank_list, start=1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1 / (k + rank)
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)