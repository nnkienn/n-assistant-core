from __future__ import annotations

import structlog
from FlagEmbedding import BGEM3FlagModel

logger = structlog.get_logger(__name__)


class BGEEmbedder:
    DIM = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3", *, use_fp16: bool = False) -> None:
        logger.info("loading_embedder", model=model_name)
        self._model = BGEM3FlagModel(model_name, use_fp16=use_fp16)

    @property
    def dim(self) -> int:
        return self.DIM

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        dense = self._model.encode(texts, return_dense=True)["dense_vecs"]
        return dense.tolist()
        