from unittest.mock import patch

from app.domain.ports.retriever import RetrievalHit
from app.infrastructure.adapters.bge_reranker import BGEReranker


def make_hit(doc_id: str, text: str, score: float = 0.5) -> RetrievalHit:
    return RetrievalHit(doc_id=doc_id, text=text, score=score, source="catalog")


@patch("app.infrastructure.adapters.bge_reranker.FlagReranker")
class TestBGEReranker:

    def test_rerank_empty_hits_returns_empty(self, mock_cls):
        reranker = BGEReranker()
        assert reranker.rerank("query", []) == []
        mock_cls.return_value.compute_score.assert_not_called()

    def test_rerank_sorts_by_cross_encoder_score_descending(self, mock_cls):
        # Input: 3 hits với RRF score giống nhau
        # Cross-encoder trả về score [0.2, 0.9, 0.5]
        # Expected: thứ tự sau rerank là hit_B (0.9) > hit_C (0.5) > hit_A (0.2)
        mock_cls.return_value.compute_score.return_value = [0.2, 0.9, 0.5]

        hits = [
            make_hit("hit_A", "kem dưỡng da khô"),
            make_hit("hit_B", "kem chống nắng SPF 50+"),
            make_hit("hit_C", "serum vitamin C"),
        ]
        reranker = BGEReranker()
        result = reranker.rerank("chống nắng da dầu", hits)

        assert result[0].doc_id == "hit_B"
        assert result[1].doc_id == "hit_C"
        assert result[2].doc_id == "hit_A"

    def test_rerank_score_replaced_by_cross_encoder_score(self, mock_cls):
        # RRF score cũ = 0.016, cross-encoder score mới = 0.94
        # Expected: score trong output là 0.94, không phải 0.016
        mock_cls.return_value.compute_score.return_value = [0.94]

        hits = [make_hit("doc_1", "kem chống nắng", score=0.016)]
        reranker = BGEReranker()
        result = reranker.rerank("chống nắng", hits)

        assert abs(result[0].score - 0.94) < 1e-6

    def test_rerank_respects_top_k(self, mock_cls):
        # Input: 4 hits, top_k=2
        # Expected: chỉ trả về 2 hits tốt nhất
        mock_cls.return_value.compute_score.return_value = [0.9, 0.8, 0.7, 0.6]

        hits = [make_hit(f"doc_{i}", f"text {i}") for i in range(4)]
        reranker = BGEReranker()
        result = reranker.rerank("query", hits, top_k=2)

        assert len(result) == 2

    def test_rerank_passes_correct_pairs_to_model(self, mock_cls):
        # Kiểm tra cross-encoder nhận đúng pairs [query, doc_text]
        mock_cls.return_value.compute_score.return_value = [0.8, 0.6]

        hits = [
            make_hit("doc_1", "kem dưỡng da"),
            make_hit("doc_2", "son môi đỏ"),
        ]
        reranker = BGEReranker()
        reranker.rerank("da khô cần kem gì", hits)

        expected_pairs = [
            ["da khô cần kem gì", "kem dưỡng da"],
            ["da khô cần kem gì", "son môi đỏ"],
        ]
        mock_cls.return_value.compute_score.assert_called_once_with(expected_pairs)

    def test_rerank_preserves_doc_fields(self, mock_cls):
        # doc_id, text, source phải giữ nguyên sau rerank
        mock_cls.return_value.compute_score.return_value = [0.75]

        hit = make_hit("prod_003", "Kem chống nắng La Roche-Posay SPF 50+")
        hit.source = "product_catalog"

        reranker = BGEReranker()
        result = reranker.rerank("chống nắng", [hit])

        assert result[0].doc_id == "prod_003"
        assert result[0].text == "Kem chống nắng La Roche-Posay SPF 50+"
        assert result[0].source == "product_catalog"
