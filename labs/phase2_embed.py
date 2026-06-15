# labs/phase2_embed.py

from FlagEmbedding import BGEM3FlagModel
import numpy as np

model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)

sentences = [
    "mèo rất dễ thương",       # VN
    "cats are very cute",       # EN — cùng nghĩa
    "thị trường chứng khoán",   # VN — khác nghĩa
]

vecs = model.encode(sentences, return_dense=True)["dense_vecs"]

print("shape:", vecs.shape)   # kỳ vọng: (3, 1024)
print("vec[0] (20 số đầu):", vecs[0][:20].tolist())


def cosine_similarity(a, b):
    va = np.array(a)
    vb = np.array(b)
    return float(np.dot(va, vb) / (np.linalg.norm(va) * np.linalg.norm(vb)))

# cặp 1: VN vs EN cùng nghĩa
score_same = cosine_similarity(vecs[0], vecs[1])
# cặp 2: VN mèo vs VN chứng khoán — khác nghĩa
score_diff = cosine_similarity(vecs[0], vecs[2])
# cặp 3: EN mèo vs VN chứng khoán — khác nghĩa, khác ngôn ngữ
score_cross_diff = cosine_similarity(vecs[1], vecs[2])

print(f"VN↔EN cùng nghĩa  : {score_same:.4f}")
print(f"VN↔VN khác nghĩa  : {score_diff:.4f}")
print(f"EN↔VN khác nghĩa  : {score_cross_diff:.4f}")
