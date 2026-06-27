CÂU 1:
BGEEmbedder output vector có dimension bao nhiêu? Tại sao phải L2-normalize sau khi embed?

1024

Qdrant tính cosine distance bằng dot product bên trong — chỉ đúng khi vector đã là unit vector. Normalize để đảm bảo điều đó.



CÂU 2:
QdrantStore dùng UUID5 để generate ID khi upsert. UUID5 nhận input gì? Mục đích là gì — nếu không dùng UUID5 mà dùng uuid4() thì vấn đề gì xảy ra?

→ Ingest document 2 lần → cùng UUID → Qdrant overwrite, không tạo bản duplicate.

Nếu dùng uuid4() → mỗi lần ingest ra ID ngẫu nhiên khác → Qdrant tạo record mới → 1 chunk bị lưu 2, 3, 10 lần → search trả về kết quả trùng, score bị sai.

UUID5 = idempotent upsert (chạy 100 lần vẫn ra 1 record).

câu 3 : ensure_collection(name, dim) — dim là gì? Nếu truyền dim=512 thay vì dim=1024 thì chuyện gì xảy ra khi search?
dim không phải về "thiếu thông tin" — mà về hard error. Qdrant dùng dim để tạo HNSW index. Nếu collection được tạo với dim=512 nhưng bạn upsert vector 1024 chiều → Qdrant từ chối, throw error ngay. Không có chuyện lưu được với "ít thông tin hơn".

câu 4 : search() nhận vector: list[float] (singular) — tại sao không nhận vectors: list[list[float]] (batch) như embed() ?

embed() nhận batch vì ingest 1000 chunks một lúc → GPU xử lý song song → nhanh
search() nhận 1 vector vì user chỉ có 1 câu query tại một thời điểm → không cần batch

