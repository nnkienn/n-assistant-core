"""Tests for Reciprocal Rank Fusion — pure math, không I/O, không mock.

🎓 HỌC GÌ Ở ĐÂY:
  1. AAA pattern (Arrange / Act / Assert) — cấu trúc chuẩn mỗi test
  2. Test behavior, không test implementation: ta không test "dict có key nào"
     mà test "kết quả đúng không, thứ tự đúng không"
  3. Pure function dễ test nhất: input → output, không side effect
  4. Verify công thức toán bằng assertion số học (abs(x - expected) < 1e-9)
"""

from app.application.services.rrf import reciprocal_rank_fusion


# ── HAPPY PATH ───────────────────────────────────────────────────────────────

def test_single_list_preserves_original_ranking():
    """
    Chỉ 1 ranked list → thứ tự output phải giống input.
    LÝ DO: đây là sanity check cơ bản nhất — nếu pass qua 1 list thôi
    mà thứ hạng bị đảo, công thức chắc chắn sai.
    """
    # Arrange
    ranked = [["a", "b", "c"]]
    # Act
    result = reciprocal_rank_fusion(ranked)
    # Assert
    ids = [doc_id for doc_id, _ in result]
    assert ids == ["a", "b", "c"]


def test_doc_in_both_lists_scores_higher_than_single_list_doc():
    """
    "x" xuất hiện ở cả list 1 lẫn list 2 → điểm RRF = 2 contributions.
    "y" chỉ ở list 1, "z" chỉ ở list 2 → điểm RRF = 1 contribution.

    LÝ DO: đây là GIÁ TRỊ CỐT LÕI của RRF — doc được nhiều retriever đồng thuận
    sẽ nổi lên trên. Test này xác nhận tính chất đó.
    """
    result = reciprocal_rank_fusion([["x", "y"], ["x", "z"]])
    scores = dict(result)
    assert scores["x"] > scores["y"], "x ở cả 2 list phải score cao hơn y chỉ ở 1 list"
    assert scores["x"] > scores["z"], "x ở cả 2 list phải score cao hơn z chỉ ở 1 list"


def test_rrf_formula_correctness():
    """
    Kiểm tra công thức: score = 1/(k + rank), k=60, rank bắt đầu từ 1.
    Doc duy nhất ở rank 1 trong 1 list với k=60 → score = 1/61.

    LÝ DO: học bằng cách tính tay rồi so với code.
    1/61 ≈ 0.016393 — đây là giá trị reference trong paper gốc (Cormack 2009).
    """
    result = reciprocal_rank_fusion([["only_doc"]], k=60)
    _, score = result[0]
    assert abs(score - 1 / 61) < 1e-9


def test_two_docs_same_rank_different_lists_have_equal_scores():
    """
    "a" ở rank 1 list 1, "b" ở rank 1 list 2 → cùng score.
    LÝ DO: đối xứng — không list nào ưu tiên hơn list nào.
    """
    result = reciprocal_rank_fusion([["a"], ["b"]])
    scores = dict(result)
    assert abs(scores["a"] - scores["b"]) < 1e-9


def test_output_sorted_descending_by_score():
    """
    Output luôn được sort giảm dần. Test với list phức tạp hơn.
    LÝ DO: caller (HybridRetriever) dựa vào thứ tự này để lấy top_k.
    """
    result = reciprocal_rank_fusion([["a", "b", "c"], ["c", "b", "a"]])
    scores = [s for _, s in result]
    assert scores == sorted(scores, reverse=True)


# ── TOÁN HỌC / EDGE CASES ────────────────────────────────────────────────────

def test_larger_k_reduces_rank_gap():
    """
    k lớn → khoảng cách điểm giữa rank 1 và rank 2 nhỏ hơn (damping mạnh hơn).

    LÝ DO: hiểu tham số k.
    - k=1:  1/2 vs 1/3 → gap = 0.167
    - k=60: 1/61 vs 1/62 → gap ≈ 0.0003
    k=60 là default vì nó "công bằng" cho các retriever khác nhau.
    """
    result_small_k = reciprocal_rank_fusion([["a", "b"]], k=1)
    scores_small = dict(result_small_k)

    result_large_k = reciprocal_rank_fusion([["a", "b"]], k=1000)
    scores_large = dict(result_large_k)

    gap_small = scores_small["a"] - scores_small["b"]
    gap_large = scores_large["a"] - scores_large["b"]

    assert gap_small > gap_large


def test_multiple_lists_accumulate_scores():
    """
    "a" xuất hiện ở rank 1 trong 3 list khác nhau → score gấp 3.
    LÝ DO: verify tính additive — mỗi list đóng góp độc lập.
    """
    result_1_list = reciprocal_rank_fusion([["a"]], k=60)
    result_3_list = reciprocal_rank_fusion([["a"], ["a"], ["a"]], k=60)

    score_1 = dict(result_1_list)["a"]
    score_3 = dict(result_3_list)["a"]

    assert abs(score_3 - 3 * score_1) < 1e-9


# ── EDGE CASES ───────────────────────────────────────────────────────────────

def test_empty_input_returns_empty():
    """Không có list → không có kết quả."""
    assert reciprocal_rank_fusion([]) == []


def test_all_empty_inner_lists_returns_empty():
    """Các list rỗng → không có doc nào được score."""
    assert reciprocal_rank_fusion([[], [], []]) == []


def test_single_doc_single_list_returns_it():
    """1 doc, 1 list → trả về đúng doc đó."""
    result = reciprocal_rank_fusion([["only"]])
    assert len(result) == 1
    assert result[0][0] == "only"
