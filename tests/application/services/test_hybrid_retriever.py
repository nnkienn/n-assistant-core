"""Tests for HybridRetriever — mock embedder, vector_store, bm25_index.

🎓 HỌC GÌ Ở ĐÂY:
  1. Khi nào mock, khi nào không mock:
     - Mock: external deps (Qdrant, embedder model) — không chạy được trong unit test
     - Không mock: code đang test (HybridRetriever), pure logic (RRF)
  2. MagicMock: auto-mock object Python — `.return_value`, `.assert_called_once_with()`
  3. HybridRetriever orchestrate 3 thứ: embed → search dense → search bm25 → RRF fuse
     Test phải verify từng bước trong pipeline.
  4. Test data flow: text từ dense hit payload → RetrievalHit.text
"""

from unittest.mock import MagicMock

from app.application.services.hybrid_retriever import HybridRetriever
from app.domain.ports.retriever import RetrievalHit
from app.domain.ports.vector_store import SearchHit


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _embedder(vector: list[float] | None = None) -> MagicMock:
    """Mock embedder: .embed(["query"]) → [[...vector...]]"""
    mock = MagicMock()
    mock.embed.return_value = [vector or [0.1, 0.2, 0.3]]
    return mock


def _vector_store(hits: list[SearchHit] | None = None) -> MagicMock:
    """Mock VectorStore: .search(...) → [SearchHit, ...]"""
    mock = MagicMock()
    mock.search.return_value = hits or []
    return mock


def _bm25(hits: list[tuple[str, float]] | None = None) -> MagicMock:
    """Mock BM25Index: .search(...) → [(doc_id, score), ...]"""
    mock = MagicMock()
    mock.search.return_value = hits or []
    return mock


def _hit(doc_id: str, score: float = 0.9, text: str = "test text", source: str = "src") -> SearchHit:
    """Tạo SearchHit (output của vector_store.search) với payload chuẩn."""
    return SearchHit(id=doc_id, score=score, payload={"text": text, "source": source})


def _retriever(
    dense_hits: list[SearchHit] | None = None,
    bm25_hits: list[tuple[str, float]] | None = None,
    vector: list[float] | None = None,
) -> HybridRetriever:
    """Tạo HybridRetriever với full mock setup."""
    return HybridRetriever(
        embedder=_embedder(vector),
        vector_store=_vector_store(dense_hits),
        bm25_index=_bm25(bm25_hits),
    )


# ── OUTPUT CONTRACT ───────────────────────────────────────────────────────────

def test_retrieve_returns_list_of_retrieval_hits():
    """
    Output type phải là list[RetrievalHit].
    LÝ DO: caller (LangGraph agent, API) expect type này — sai type là runtime crash.
    """
    r = _retriever(
        dense_hits=[_hit("d1"), _hit("d2")],
        bm25_hits=[("d1", 1.0), ("d2", 0.5)],
    )
    results = r.retrieve("query", tenant_id="t1", top_k=5)
    assert isinstance(results, list)
    assert all(isinstance(x, RetrievalHit) for x in results)


def test_retrieve_respects_top_k():
    """
    top_k=2 → trả về nhiều nhất 2 kết quả dù dense search cho 10 hits.

    LÝ DO: memory constraint — caller chỉ muốn top_k docs để nhét vào prompt.
    Trả về quá nhiều → prompt overflow.
    """
    hits = [_hit(f"d{i}") for i in range(10)]
    bm25_hits = [(f"d{i}", float(10 - i)) for i in range(10)]
    r = _retriever(dense_hits=hits, bm25_hits=bm25_hits)
    results = r.retrieve("query", tenant_id="t1", top_k=2)
    assert len(results) <= 2


def test_retrieval_hit_fields_populated_correctly():
    """
    RetrievalHit.text và .source phải đến từ dense hit payload.

    LÝ DO: BM25 không lưu text (chỉ trả về doc_id + score).
    Text phải lấy từ vector store payload — verify data flow không bị drop.
    """
    hits = [_hit("d1", text="My important text", source="wiki")]
    r = _retriever(dense_hits=hits, bm25_hits=[("d1", 2.0)])
    results = r.retrieve("q", tenant_id="t1", top_k=1)
    assert results[0].text == "My important text"
    assert results[0].source == "wiki"
    assert results[0].doc_id == "d1"


# ── PIPELINE ORCHESTRATION ────────────────────────────────────────────────────

def test_embedder_called_with_query_text():
    """
    Embedder phải được gọi với đúng query string dạng list: ["my query"].
    LÝ DO: .embed() nhận batch → ["query"], không phải "query" (string).
    Truyền sai → embedder raise TypeError hoặc trả về kết quả sai.
    """
    emb = _embedder()
    r = HybridRetriever(
        embedder=emb,
        vector_store=_vector_store(),
        bm25_index=_bm25(),
    )
    r.retrieve("my query", tenant_id="t1")
    emb.embed.assert_called_once_with(["my query"])


def test_vector_store_called_with_dense_vector_and_tenant():
    """
    vector_store.search() phải nhận đúng vector và tenant_id.
    LÝ DO: tenant_id là namespace filter — truyền sai tenant → data leak.
    """
    vec = [0.5, 0.6, 0.7]
    vs = _vector_store()
    r = HybridRetriever(
        embedder=_embedder(vec),
        vector_store=vs,
        bm25_index=_bm25(),
    )
    r.retrieve("query", tenant_id="secret_tenant", top_k=3)
    vs.search.assert_called_once_with(
        "chunks", vec, tenant_id="secret_tenant", top_k=6  # top_k * 2
    )


def test_bm25_called_with_query_and_tenant():
    """
    BM25.search() phải nhận đúng query string và tenant_id.
    LÝ DO: tương tự vector_store — tenant isolation phải nhất quán.
    """
    bm = _bm25()
    r = HybridRetriever(
        embedder=_embedder(),
        vector_store=_vector_store(),
        bm25_index=bm,
    )
    r.retrieve("keyword query", tenant_id="t1", top_k=4)
    bm.search.assert_called_once_with(
        "keyword query", tenant_id="t1", top_k=8  # top_k * 2
    )


# ── RRF FUSION BEHAVIOR ───────────────────────────────────────────────────────

def test_doc_in_both_dense_and_bm25_appears_in_results():
    """
    "d1" ở cả dense list lẫn bm25 list → RRF boost → phải có trong kết quả.

    LÝ DO: đây là mục đích của hybrid search — doc được cả 2 retriever đồng thuận
    sẽ được ưu tiên hơn doc chỉ từ 1 nguồn.
    """
    dense_hits = [_hit("d1", score=0.9), _hit("d2", score=0.7)]
    bm25_hits = [("d1", 3.0), ("d3", 1.0)]  # d1 ở cả 2 lists, d3 chỉ ở bm25

    r = _retriever(dense_hits=dense_hits, bm25_hits=bm25_hits)
    results = r.retrieve("query", tenant_id="t1", top_k=5)
    result_ids = [res.doc_id for res in results]
    assert "d1" in result_ids


def test_only_docs_with_dense_hits_have_text():
    """
    Nếu doc từ BM25 không có trong dense hits → không có text → bị drop.

    LÝ DO: HybridRetriever lấy text từ id_to_hit map (dense hits).
    Doc chỉ có ở BM25 không có payload → không đưa vào result.
    Đây là design decision: dense hit = source of truth cho text.
    """
    dense_hits = [_hit("d1")]  # chỉ d1 có dense hit
    bm25_hits = [("d1", 2.0), ("d99", 99.0)]  # d99 chỉ ở bm25, không có dense hit

    r = _retriever(dense_hits=dense_hits, bm25_hits=bm25_hits)
    results = r.retrieve("q", tenant_id="t1", top_k=10)
    result_ids = [res.doc_id for res in results]
    assert "d99" not in result_ids, "d99 không có dense hit nên bị drop"
    assert "d1" in result_ids


# ── EDGE CASES ───────────────────────────────────────────────────────────────

def test_empty_dense_and_bm25_returns_empty_list():
    """
    Cả 2 retriever đều trả về rỗng → kết quả rỗng.
    LÝ DO: không nên raise exception, trả về [] cho caller xử lý.
    """
    r = _retriever(dense_hits=[], bm25_hits=[])
    results = r.retrieve("query", tenant_id="t1")
    assert results == []


def test_top_k_zero_returns_empty():
    """top_k=0 → không lấy gì."""
    r = _retriever(dense_hits=[_hit("d1")], bm25_hits=[("d1", 1.0)])
    results = r.retrieve("q", tenant_id="t1", top_k=0)
    assert results == []


def test_score_in_result_is_rrf_score_not_original():
    """
    RetrievalHit.score phải là RRF score (float nhỏ ~ 1/61),
    không phải cosine similarity (~ 0.9) hay BM25 score (~ 12.3).

    LÝ DO: caller dùng score để rank — phải biết đơn vị.
    RRF score nằm trong khoảng (0, n_lists/k] — không phải similarity.
    """
    dense_hits = [_hit("d1", score=0.95)]
    bm25_hits = [("d1", 15.7)]
    r = _retriever(dense_hits=dense_hits, bm25_hits=bm25_hits)
    results = r.retrieve("q", tenant_id="t1", top_k=1)
    assert len(results) == 1
    rrf_score = results[0].score
    # RRF score với k=60, rank 1 ở cả 2 list: 1/61 + 1/61 ≈ 0.0328
    assert rrf_score < 1.0, f"RRF score phải < 1.0, got {rrf_score}"
    assert rrf_score > 0.0
