from __future__ import annotations
from FlagEmbedding import  FlagModel

class BGEEmbedder:
    def __init__(self,model_name : str ="BAAI/bge-m3") -> None :
        self._model = FlagModel(model_name,use_fp16=True)

    async def embed(self,texts : list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return vecs.tolist()
    