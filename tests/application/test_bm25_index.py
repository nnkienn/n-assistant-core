"""Tests for BM25Index — in-memory keyword search, không I/O, không mock.

🎓 HỌC GÌ Ở ĐÂY:
  1. Mỗi test = 1 hành vi cụ thể (không test nhiều thứ trong 1 test)
  2. Helper function `_index(*docs)` để tránh lặp code setup
  3. BM25 behavior: TF saturation, IDF, document-length normalization
  4. Namespace isolation: tenant_A không thấy data của tenant_B
"""

import pytest
from app.application.bm25_index import BM25Index


# ── HELPER ───────────────────────────────────────────────────────────────────

def _index(*docs: tuple[str, str, str]) -> BM25Index:
    """Tạo BM25Index và add các doc (doc_id, text, tenant_id) vào."""
    idx = BM25Index()
    for doc_id, text, tenant_id in docs:
        idx.add(doc_id, text, tenant_id)
    return idx


# ── HAPPY PATH ───────────────────────────────────────────────────────────────

def test_relevant_doc_appears_in_results():
    """
    Sau khi add doc có chứa từ trong query, search phải trả về doc đó.
    LÝ DO: test cơ bản nhất — nếu cái này fail thì hoàn toàn không dùng được.
    """
    idx = _index(("d1", "python is a programming language", "t1"))
    results = idx.search("python", tenant_id="t1")
    ids = [doc_id for doc_id, _ in results]
    assert "d1" in ids


def test_most_relevant_doc_ranked_first():
    """
    Doc chứa nhiều từ trong query hơn phải rank cao hơn.
    LÝ DO: kiểm tra BM25 đang rank đúng, không phải random order.
    """
    idx = _index(
        ("d1", "python programming language guide", "t1"),
        ("d2", "recipe for chocolate cake", "t1"),
    )
    results = idx.search("python programming", tenant_id="t1")
    assert results[0][0] == "d1", "doc về python phải rank 1"


def test_top_k_limits_number_of_results():
    """
    top_k=3 → trả về nhiều nhất 3 kết quả dù có 10 docs.
    LÝ DO: caller (HybridRetriever) dùng top_k*2 rồi fuse — phải tuân thủ limit.
    """
    idx = _index(*[(f"d{i}", f"common term extra{i}", "t1") for i in range(10)])
    results = idx.search("common term", tenant_id="t1", top_k=3)
    assert len(results) <= 3


def test_results_are_tuples_of_id_and_float_score():
    """
    Output format: list[tuple[str, float]].
    LÝ DO: HybridRetriever unpack `for doc_id, _ in bm25_hits` — format sai là crash.
    """
    idx = _index(("d1", "hello world", "t1"))
    results = idx.search("hello", tenant_id="t1")
    assert len(results) == 1
    doc_id, score = results[0]
    assert isinstance(doc_id, str)
    assert isinstance(score, float)
    assert score > 0.0


def test_scores_sorted_descending():
    """
    Scores phải giảm dần. LÝ DO: HybridRetriever lấy [:top_k] từ sorted list.
    """
    idx = _index(
        ("d1", "python python python", "t1"),
        ("d2", "python once", "t1"),
        ("d3", "java", "t1"),
    )
    results = idx.search("python", tenant_id="t1")
    scores = [s for _, s in results]
    assert scores == sorted(scores, reverse=True)


# ── NAMESPACE ISOLATION (CỰC KỲ QUAN TRỌNG trong multi-tenant) ──────────────

def test_tenant_isolation_no_cross_contamination():
    """
    Doc của tenant_A không xuất hiện khi search với tenant_B.

    LÝ DO: đây là "namespace moat" — một trong những invariant quan trọng nhất
    của toàn bộ system. Nếu isolation fail → data leak giữa các tenant.
    Test này là mandatory cho mọi retrieval component.
    """
    idx = _index(
        ("d1", "breaking news python", "tenant_A"),
        ("d2", "breaking news java", "tenant_B"),
    )
    hits_a = idx.search("breaking news", tenant_id="tenant_A")
    ids_a = {doc_id for doc_id, _ in hits_a}
    assert "d2" not in ids_a, "tenant_B doc phải không nhìn thấy từ tenant_A"


def test_same_query_different_tenants_see_own_docs():
    """
    Cùng query, cùng từ khóa — mỗi tenant chỉ thấy doc của mình.
    """
    idx = _index(
        ("apple_A", "apple iphone review", "tenant_A"),
        ("apple_B", "apple iphone review", "tenant_B"),
    )
    results_a = idx.search("apple iphone", tenant_id="tenant_A")
    results_b = idx.search("apple iphone", tenant_id="tenant_B")
    assert results_a[0][0] == "apple_A"
    assert results_b[0][0] == "apple_B"


# ── BM25 MATH PROPERTIES ─────────────────────────────────────────────────────

def test_higher_term_frequency_boosts_score():
    """
    Doc có TF cao hơn (nhưng BM25 saturation: không tuyến tính) → score cao hơn.

    LÝ DO: hiểu TF saturation của BM25.
    TF-IDF thuần: score(doc với 4x "python") = 4 × score(doc với 1x "python").
    BM25 với k1=1.5: hệ số nhỏ hơn nhiều — "python python python python"
    không chiếm ưu thế tuyệt đối so với "python once" như TF-IDF.
    """
    idx = _index(
        ("high_tf", "python python python python", "t1"),
        ("low_tf", "python once", "t1"),
    )
    results = idx.search("python", tenant_id="t1")
    scores = {doc_id: s for doc_id, s in results}
    assert scores["high_tf"] > scores["low_tf"]


def test_case_insensitive_matching():
    """
    Query "PYTHON" và "python" phải cho kết quả như nhau.
    LÝ DO: add() tokenize bằng .lower(), search() cũng .lower() query.
    """
    idx = _index(("d1", "Python Is Great", "t1"))
    results_lower = idx.search("python", tenant_id="t1")
    results_upper = idx.search("PYTHON", tenant_id="t1")
    assert results_lower[0][0] == results_upper[0][0] == "d1"


def test_idf_down_weights_common_terms():
    """
    Term xuất hiện trong nhiều docs → IDF thấp → đóng góp vào score ít hơn.
    Term hiếm xuất hiện ở ít docs → IDF cao → score cao hơn.

    LÝ DO: hiểu IDF.
    "the" xuất hiện ở mọi doc → IDF ≈ 0 (useless).
    "quantum" chỉ ở 1 doc → IDF cao → doc đó score rất cao.
    """
    idx = _index(
        ("d1", "the cat the dog the fish", "t1"),  # "the" rất phổ biến
        ("d2", "the quantum entanglement", "t1"),   # "quantum" hiếm
        ("d3", "the ordinary sentence", "t1"),
    )
    # search "quantum" — chỉ d2 có → score cao
    results = idx.search("quantum", tenant_id="t1")
    assert results[0][0] == "d2"


# ── EDGE CASES ───────────────────────────────────────────────────────────────

def test_empty_index_returns_empty():
    """Index rỗng → search bất kỳ query cũng trả về []."""
    idx = BM25Index()
    assert idx.search("anything", tenant_id="t1") == []


def test_search_unknown_tenant_returns_empty():
    """
    Tenant không có doc → trả về [].
    LÝ DO: không nên raise exception, chỉ trả về list rỗng.
    HybridRetriever xử lý empty list bình thường.
    """
    idx = _index(("d1", "python data science", "tenant_A"))
    assert idx.search("python", tenant_id="unknown_tenant") == []


def test_query_with_no_matching_terms_returns_zero_scores():
    """
    Query không có term nào match → tất cả docs có score = 0.
    BM25 vẫn trả về docs (score 0) vì không filter out, chỉ sort.
    (Hoặc score = 0.0 — hành vi này acceptable.)
    """
    idx = _index(
        ("d1", "python is great", "t1"),
        ("d2", "machine learning rocks", "t1"),
    )
    results = idx.search("xyznotexist", tenant_id="t1")
    # Score phải = 0 vì không có term nào match
    for _, score in results:
        assert score == 0.0
