from unittest.mock import MagicMock, patch
import numpy as np

from app.infrastructure.adapters.bge_embedder import BGEEmbedder


# patch("...BGEM3FlagModel") thay thế class thật bằng MagicMock
# → __init__ không load 4.5GB, test chạy trong milliseconds
@patch("app.infrastructure.adapters.bge_embedder.BGEM3FlagModel")
class TestBGEEmbedder:

    # ── dim ──────────────────────────────────────────────────────────────

    def test_dim_returns_1024(self, mock_model_cls):
        # Arrange
        embedder = BGEEmbedder()

        # Act + Assert
        assert embedder.dim == 1024

    # ── embed guard clause ────────────────────────────────────────────────

    def test_embed_empty_list_returns_empty(self, mock_model_cls):
        # Input: []
        # Expected: [] — không gọi model
        embedder = BGEEmbedder()

        result = embedder.embed([])

        assert result == []
        mock_model_cls.return_value.encode.assert_not_called()

    # ── embed output format ───────────────────────────────────────────────

    def test_embed_returns_list_of_lists(self, mock_model_cls):
        # Input: 1 text
        # Expected: 1 vector dạng list[float], không phải numpy array
        fake_vecs = np.array([[0.1] * 1024])
        mock_model_cls.return_value.encode.return_value = {"dense_vecs": fake_vecs}

        embedder = BGEEmbedder()
        result = embedder.embed(["kem dưỡng da"])

        assert isinstance(result, list)
        assert isinstance(result[0], list)   # list, không phải np.ndarray
        assert isinstance(result[0][0], float)

    def test_embed_vector_length_is_1024(self, mock_model_cls):
        # Input: 1 text
        # Expected: vector có đúng 1024 chiều
        fake_vecs = np.array([[0.1] * 1024])
        mock_model_cls.return_value.encode.return_value = {"dense_vecs": fake_vecs}

        embedder = BGEEmbedder()
        result = embedder.embed(["kem dưỡng da"])

        assert len(result[0]) == 1024

    def test_embed_batch_returns_one_vector_per_text(self, mock_model_cls):
        # Input: 3 texts
        # Expected: 3 vectors, thứ tự giữ nguyên
        fake_vecs = np.array([[0.1] * 1024, [0.2] * 1024, [0.3] * 1024])
        mock_model_cls.return_value.encode.return_value = {"dense_vecs": fake_vecs}

        embedder = BGEEmbedder()
        result = embedder.embed(["text A", "text B", "text C"])

        assert len(result) == 3

    # ── embed gọi model đúng cách ─────────────────────────────────────────

    def test_embed_calls_encode_with_return_dense_true(self, mock_model_cls):
        # Kiểm tra BGEEmbedder truyền đúng param vào model
        # Nếu return_dense=False → không có dense_vecs → KeyError
        fake_vecs = np.array([[0.1] * 1024])
        mock_model = mock_model_cls.return_value
        mock_model.encode.return_value = {"dense_vecs": fake_vecs}

        embedder = BGEEmbedder()
        embedder.embed(["test"])

        mock_model.encode.assert_called_once_with(["test"], return_dense=True)
