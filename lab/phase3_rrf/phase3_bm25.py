# phase3_bm25.py — học BM25 từng bước
def tf(term: str, doc: list[str]) -> float:
    return doc.count(term) / len(doc)

# thử với 3 doc
doc_short = ["AI", "agents", "AI", "build"]          # 4 từ, "AI" x2
doc_long  = ["AI", "agents", "python", "code",
             "model", "train", "data", "pipeline"]    # 8 từ, "AI" x1

print(tf("AI", doc_short))   # kỳ vọng: cao hơn
print(tf("AI", doc_long))    # kỳ vọng: thấp hơn

import math

def idf(term: str, corpus: list[list[str]], N: int) -> float:
    df = sum(1 for doc in corpus if term in doc)
    return math.log((N - df + 0.5) / (df + 0.5) + 1)

corpus = [doc_short, doc_long,
          ["football", "match", "goal"],
          ["AI", "neural", "network"]]
N = len(corpus)

print(idf("AI", corpus, N))        # xuất hiện trong 3/4 doc → phổ biến → IDF thấp
print(idf("football", corpus, N))  # xuất hiện trong 1/4 doc → hiếm → IDF cao

def bm25_score(query: list[str], doc: list[str],
               corpus: list[list[str]], k1: float = 1.5, b: float = 0.75) -> float:
    N    = len(corpus)
    avgdl = sum(len(d) for d in corpus) / N
    dl    = len(doc)
    score = 0.0

    for term in query:
        _tf  = doc.count(term)
        _idf = idf(term, corpus, N)
        numerator   = _tf * (k1 + 1)
        denominator = _tf + k1 * (1 - b + b * dl / avgdl)
        score += _idf * (numerator / denominator)

    return score

query = ["AI", "agents"]
for i, doc in enumerate(corpus):
    print(f"doc{i}: {bm25_score(query, doc, corpus):.4f}  {doc}")
