# phase2_cosine.py — học cosine similarity từng bước

import numpy as np

# 3 "từ" trong không gian 3 chiều: [tech, sports, food]
python_vec  = [0.9, 0.0, 0.0]
football_vec = [0.0, 0.9, 0.0]
ai_vec      = [0.8, 0.0, 0.1]

print("python_vec :", python_vec)
print("football_vec:", football_vec)
print("ai_vec     :", ai_vec)


def cosine_similarity(a, b):
    va = np.array(a)
    vb = np.array(b)

    dot    = np.dot(va, vb)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)

    return dot / (norm_a * norm_b)

print(cosine_similarity(python_vec, ai_vec))      # kỳ vọng: gần 1
print(cosine_similarity(python_vec, football_vec)) # kỳ vọng: gần 0
query = [0.85, 0.0, 0.05]  # câu hỏi về tech

docs = {
    "Python tutorial": [0.9, 0.0, 0.0],
    "AI research":     [0.8, 0.0, 0.1],
    "Football match":  [0.0, 0.9, 0.0],
    "Cooking recipe":  [0.0, 0.1, 0.9],
}

results = []
for label, vec in docs.items():
    score = cosine_similarity(query, vec)
    results.append((label, score))

results.sort(key=lambda x: x[1], reverse=True)

for rank, (label, score) in enumerate(results, start=1):
    print(f"rank {rank}  score={score:.4f}  {label}")
