"""
Demo: Xem pipeline RAG Phase 3 chạy với data thật.

Mục tiêu: thấy BM25, Dense Search, và RRF hoạt động thế nào với sản phẩm mỹ phẩm thật.
Chạy: docker compose run --rm -v ./tests:/app/tests core-api python demo_pipeline.py
"""

from app.application.bm25_index import BM25Index
from app.application.services.rrf import reciprocal_rank_fusion

TENANT = "shop_myPham"

# ── 6 sản phẩm mỹ phẩm thật ─────────────────────────────────────────────────
DOCS = [
    ("prod_001", "Kem dưỡng ẩm Neutrogena dành cho da khô, chứa hyaluronic acid và vitamin E, dưỡng ẩm 24 giờ"),
    ("prod_002", "Son môi lì Maybelline màu đỏ cherry, không trôi 16 giờ, chứa vitamin C, SPF 15"),
    ("prod_003", "Kem chống nắng La Roche-Posay SPF 50+ PA++++ cho da nhạy cảm, chống tia UVA UVB"),
    ("prod_004", "Serum vitamin C 20% L'Oreal dưỡng trắng mờ thâm nám, dùng buổi sáng trước kem chống nắng"),
    ("prod_005", "Tẩy trang Bioderma Sensibio H2O cho da nhạy cảm, làm sạch sâu không cần rửa lại, không cồn"),
    ("prod_006", "Kem dưỡng da ban đêm Olay Regenerist chứa niacinamide và retinol, tái tạo da khi ngủ"),
]

SEP = "─" * 60


def print_ranked(title: str, ranked: list, docs: dict, top: int = 6):
    print(f"\n  {title}")
    for i, (doc_id, score) in enumerate(ranked[:top], 1):
        text = docs.get(doc_id, "???")[:55]
        print(f"  {i}. [{doc_id}] score={score:.4f} | {text}...")


def run_demo(query: str, fake_dense_ranked: list[str]):
    docs = {doc_id: text for doc_id, text in DOCS}

    print(f"\n{'=' * 60}")
    print(f"  QUERY: \"{query}\"")
    print("=" * 60)

    # ── BƯỚC 1: BM25 Search ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("  BƯỚC 1 — BM25 (Sparse / Keyword Search)")
    print("  Tìm kiếm theo từ khóa chính xác trong text sản phẩm.")
    print(SEP)

    bm25 = BM25Index()
    for doc_id, text in DOCS:
        bm25.add(doc_id, text, TENANT)

    bm25_results = bm25.search(query, tenant_id=TENANT, top_k=6)
    bm25_ranked  = [doc_id for doc_id, _ in bm25_results]

    print_ranked("Kết quả BM25:", bm25_results, docs)

    # ── BƯỚC 2: Dense Search (Fake) ──────────────────────────────────
    print(f"\n{SEP}")
    print("  BƯỚC 2 — Dense Search (Semantic / bge-m3)")
    print("  Tìm kiếm theo ngữ nghĩa — hiểu ý nghĩa câu, không cần khớp từ khóa.")
    print("  (Fake để demo — production dùng bge-m3 + Qdrant thật)")
    print(SEP)

    # Gán score giảm dần cho fake dense results
    dense_scores = [(doc_id, round(1.0 - i * 0.08, 2)) for i, doc_id in enumerate(fake_dense_ranked)]
    print_ranked("Kết quả Dense:", dense_scores, docs)

    # ── BƯỚC 3: RRF Fusion ───────────────────────────────────────────
    print(f"\n{SEP}")
    print("  BƯỚC 3 — RRF Fusion (Kết hợp 2 nguồn)")
    print("  Gộp BM25 + Dense theo thứ hạng. Doc xuất hiện cao trong cả 2 → thắng.")
    print(SEP)

    fused = reciprocal_rank_fusion([bm25_ranked, fake_dense_ranked])
    fused_with_label = [(doc_id, score) for doc_id, score in fused]
    print_ranked("Kết quả RRF:", fused_with_label, docs)

    # ── SO SÁNH ──────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  SO SÁNH — Thứ hạng của từng doc qua 3 bước")
    print(SEP)
    print(f"  {'Doc':<12} {'BM25':>8} {'Dense':>8} {'RRF':>8}  Text")

    bm25_rank  = {doc_id: i+1 for i, (doc_id, _) in enumerate(bm25_results)}
    dense_rank = {doc_id: i+1 for i, doc_id in enumerate(fake_dense_ranked)}
    rrf_rank   = {doc_id: i+1 for i, (doc_id, _) in enumerate(fused)}

    for doc_id, text in DOCS:
        b = bm25_rank.get(doc_id, "-")
        d = dense_rank.get(doc_id, "-")
        r = rrf_rank.get(doc_id, "-")
        print(f"  {doc_id:<12} {str(b):>8} {str(d):>8} {str(r):>8}  {text[:40]}...")


# ════════════════════════════════════════════════════════════════════
# DEMO 1: Query có từ khóa chính xác → BM25 thắng
# ════════════════════════════════════════════════════════════════════
#
# Tình huống: khách hỏi "SPF 50 chống nắng"
# → BM25 tìm thấy prod_003 ngay vì text chứa chính xác "SPF 50+"
# → Dense search cũng tìm thấy prod_003 nhưng xếp hạng có thể khác
# → RRF kết hợp → prod_003 luôn đứng đầu

run_demo(
    query="SPF 50 chống nắng",
    fake_dense_ranked=[
        "prod_003",  # dense hiểu "chống nắng" ≈ "chống tia UVA UVB"
        "prod_004",  # serum dùng buổi sáng trước kem chống nắng
        "prod_002",  # son môi có SPF 15
        "prod_001",  # kem dưỡng ẩm — ít liên quan
        "prod_006",  # kem ban đêm — ít liên quan
        "prod_005",  # tẩy trang — không liên quan
    ],
)

# ════════════════════════════════════════════════════════════════════
# DEMO 2: Query ngữ nghĩa → Dense thắng, BM25 trượt
# ════════════════════════════════════════════════════════════════════
#
# Tình huống: khách hỏi "bảo vệ da khỏi ánh nắng mặt trời"
# → BM25 TRƯỢT: text sản phẩm không có chữ "bảo vệ" hay "ánh nắng mặt trời"
# → Dense search TÌM ĐƯỢC: bge-m3 hiểu "ánh nắng" ≈ "UVA UVB" ≈ "chống nắng"
# → Đây là lý do cần Hybrid — BM25 một mình sẽ thất bại ở query này

run_demo(
    query="bảo vệ da khỏi ánh nắng mặt trời",
    fake_dense_ranked=[
        "prod_003",  # dense hiểu "ánh nắng" ≈ "UVA UVB chống nắng"
        "prod_004",  # serum dùng trước kem chống nắng — ngữ nghĩa liên quan
        "prod_001",  # kem dưỡng ẩm — bảo vệ da nói chung
        "prod_002",  # son SPF 15 — ít liên quan
        "prod_006",  # ban đêm — không liên quan
        "prod_005",  # tẩy trang — không liên quan
    ],
)

# ════════════════════════════════════════════════════════════════════
# DEMO 3: Tenant Isolation
# ════════════════════════════════════════════════════════════════════
#
# Tình huống: 2 shop khác nhau, cùng query "kem dưỡng da"
# → shop_A chỉ thấy sản phẩm của shop_A, shop_B chỉ thấy của shop_B
# → Đây là tenant isolation — bảo đảm kiến trúc, không phải convention

print(f"\n\n{'=' * 60}")
print("  DEMO 3 — Tenant Isolation")
print("  2 shop khác nhau, cùng BM25Index, query giống nhau.")
print("=" * 60)

bm25 = BM25Index()
bm25.add("shopA_001", "Kem dưỡng da cao cấp dành riêng cho shop A", "shop_A")
bm25.add("shopA_002", "Son môi đỏ shop A", "shop_A")
bm25.add("shopB_001", "Kem dưỡng da giá rẻ shop B bán chạy nhất", "shop_B")
bm25.add("shopB_002", "Serum trắng da shop B", "shop_B")

query = "kem dưỡng da"
results_A = bm25.search(query, tenant_id="shop_A", top_k=5)
results_B = bm25.search(query, tenant_id="shop_B", top_k=5)

print(f"\n  Query: \"{query}\"")
print(f"\n  Shop A thấy:")
for doc_id, score in results_A:
    print(f"    [{doc_id}] score={score:.4f}")

print(f"\n  Shop B thấy:")
for doc_id, score in results_B:
    print(f"    [{doc_id}] score={score:.4f}")

print(f"\n  → Shop A không thấy sản phẩm của shop B và ngược lại.")
print(f"  → Đây là tenant isolation — filter bằng tenant_id ở mọi search operation.")
print()
