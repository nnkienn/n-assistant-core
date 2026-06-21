from unittest.mock import MagicMock, call, patch

from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.infrastructure.adapters.qdrant_store import QdrantStore


# patch QdrantClient → không cần Qdrant server chạy
@patch("app.infrastructure.adapters.qdrant_store.QdrantClient")
class TestQdrantStore:

    # ── ensure_collection ─────────────────────────────────────────────────

    def test_ensure_collection_creates_when_not_exists(self, mock_client_cls):
        # Input: collection chưa tồn tại
        # Expected: create_collection được gọi 1 lần
        mock_client = mock_client_cls.return_value
        mock_client.collection_exists.return_value = False

        store = QdrantStore("http://fake:6333")
        store.ensure_collection("chunks", 1024)

        mock_client.create_collection.assert_called_once()

    def test_ensure_collection_skips_when_already_exists(self, mock_client_cls):
        # Input: collection đã tồn tại
        # Expected: create_collection KHÔNG được gọi
        mock_client = mock_client_cls.return_value
        mock_client.collection_exists.return_value = True

        store = QdrantStore("http://fake:6333")
        store.ensure_collection("chunks", 1024)

        mock_client.create_collection.assert_not_called()

    # ── upsert ───────────────────────────────────────────────────────────

    def test_upsert_returns_number_of_points(self, mock_client_cls):
        # Input: 2 vectors + 2 payloads
        # Expected: return 2
        store = QdrantStore("http://fake:6333")
        vectors = [[0.1] * 1024, [0.2] * 1024]
        payloads = [
            {"tenant_id": "shop_a", "text": "kem dưỡng da"},
            {"tenant_id": "shop_a", "text": "son môi đỏ"},
        ]

        result = store.upsert("chunks", vectors, payloads)

        assert result == 2

    def test_upsert_same_text_produces_same_point_id(self, mock_client_cls):
        # Input: upsert cùng 1 text 2 lần
        # Expected: point_id giống nhau → Qdrant overwrite thay vì duplicate
        store = QdrantStore("http://fake:6333")
        payload = {"tenant_id": "shop_a", "text": "kem dưỡng da"}

        store.upsert("chunks", [[0.1] * 1024], [payload])
        first_call_points = mock_client_cls.return_value.upsert.call_args[1]["points"]

        store.upsert("chunks", [[0.2] * 1024], [payload])
        second_call_points = mock_client_cls.return_value.upsert.call_args[1]["points"]

        assert first_call_points[0].id == second_call_points[0].id

    def test_upsert_different_texts_produce_different_ids(self, mock_client_cls):
        # Input: 2 texts khác nhau
        # Expected: 2 point_id khác nhau
        store = QdrantStore("http://fake:6333")
        payloads = [
            {"tenant_id": "shop_a", "text": "kem dưỡng da"},
            {"tenant_id": "shop_a", "text": "son môi đỏ"},
        ]

        store.upsert("chunks", [[0.1] * 1024, [0.2] * 1024], payloads)
        points = mock_client_cls.return_value.upsert.call_args[1]["points"]

        assert points[0].id != points[1].id

    # ── search ───────────────────────────────────────────────────────────

    def test_search_applies_tenant_filter(self, mock_client_cls):
        # Input: search với tenant_id="shop_a"
        # Expected: query_filter chứa tenant_id == "shop_a"
        mock_client = mock_client_cls.return_value
        mock_client.query_points.return_value.points = []

        store = QdrantStore("http://fake:6333")
        store.search("chunks", [0.1] * 1024, tenant_id="shop_a")

        call_kwargs = mock_client.query_points.call_args[1]
        query_filter = call_kwargs["query_filter"]
        condition = query_filter.must[0]

        assert condition.key == "tenant_id"
        assert condition.match.value == "shop_a"

    def test_search_returns_search_hits(self, mock_client_cls):
        # Input: Qdrant trả về 2 points
        # Expected: 2 SearchHit với đúng id, score, payload
        mock_point_1 = MagicMock()
        mock_point_1.id = "doc-1"
        mock_point_1.score = 0.95
        mock_point_1.payload = {"text": "kem dưỡng da", "tenant_id": "shop_a"}

        mock_point_2 = MagicMock()
        mock_point_2.id = "doc-2"
        mock_point_2.score = 0.87
        mock_point_2.payload = {"text": "son môi đỏ", "tenant_id": "shop_a"}

        mock_client_cls.return_value.query_points.return_value.points = [
            mock_point_1, mock_point_2
        ]

        store = QdrantStore("http://fake:6333")
        results = store.search("chunks", [0.1] * 1024, tenant_id="shop_a")

        assert len(results) == 2
        assert results[0].id == "doc-1"
        assert results[0].score == 0.95
        assert results[1].id == "doc-2"

    def test_search_none_payload_becomes_empty_dict(self, mock_client_cls):
        # Input: point có payload=None
        # Expected: SearchHit.payload == {} thay vì None
        mock_point = MagicMock()
        mock_point.id = "doc-1"
        mock_point.score = 0.9
        mock_point.payload = None

        mock_client_cls.return_value.query_points.return_value.points = [mock_point]

        store = QdrantStore("http://fake:6333")
        results = store.search("chunks", [0.1] * 1024, tenant_id="shop_a")

        assert results[0].payload == {}

    def test_search_respects_top_k(self, mock_client_cls):
        # Input: top_k=3
        # Expected: query_points được gọi với limit=3
        mock_client_cls.return_value.query_points.return_value.points = []

        store = QdrantStore("http://fake:6333")
        store.search("chunks", [0.1] * 1024, tenant_id="shop_a", top_k=3)

        call_kwargs = mock_client_cls.return_value.query_points.call_args[1]
        assert call_kwargs["limit"] == 3
