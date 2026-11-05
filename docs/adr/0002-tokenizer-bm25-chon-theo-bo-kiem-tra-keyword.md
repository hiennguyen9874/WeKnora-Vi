---
status: accepted
---

# Chọn lại tokenizer BM25 của ParadeDB bằng Bộ kiểm tra keyword

Chỉ mục BM25 trên `embeddings.content` dùng tokenizer `chinese_lindera` (`000002_embeddings`). Chưa ai kiểm tra nó tách tiếng Việt thế nào. Chúng tôi giữ PostgreSQL/ParadeDB làm backend duy nhất, không chuyển sang Elasticsearch/OpenSearch, và chọn tokenizer bằng cách đo recall@k trên Bộ kiểm tra keyword. Các ứng viên là `chinese_lindera`, `icu`, `whitespace` kèm lowercase, và mỗi loại có hoặc không có bỏ dấu (`ascii_folding`). Tokenizer thắng được đưa vào bằng migration trong Fork, kèm migration down để rollback.

**Tokenizer đã chọn: `icu`, không bỏ dấu** (`{"type": "icu"}`). Thí nghiệm #11 trên ParadeDB `pg_search 0.25.11`:

- R@10 keyword 0,8462 so với 0,8077 của `chinese_lindera`; hybrid ngang nhau (R@10 0,9231).
- Không sinh token khoảng trắng và dấu câu. `chinese_lindera` dạng JSON có token `" "` trong 687/693 chunk.
- Bỏ dấu làm keyword mất các câu có dấu (R@10 0,7692), trong khi câu không dấu đã có vector/hybrid xử lý.

Khoảng cách với `chinese_lindera` nhỏ (một câu ở R@10 trên 26 câu). Số liệu và lý do đầy đủ nằm ở `docs/validation/issue-11.md`.

## Consequences

Đổi tokenizer phải dựng lại chỉ mục BM25 trên mọi chunk đã có. Nâng cấp WeKnora gốc mà có migration đụng tới chỉ mục này thì phải đối chiếu lại thủ công. Không bỏ dấu, nên câu hỏi không dấu chỉ khớp từ khoá với chunk không dấu; tìm câu không dấu dựa vào vector và hybrid.
