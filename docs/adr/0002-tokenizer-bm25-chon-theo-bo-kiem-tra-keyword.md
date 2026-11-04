---
status: proposed
---

# Chọn lại tokenizer BM25 của ParadeDB bằng Bộ kiểm tra keyword

Chỉ mục BM25 trên `embeddings.content` dùng tokenizer `chinese_lindera` (`000002_embeddings`). Chưa ai kiểm tra nó tách tiếng Việt thế nào. Chúng tôi giữ PostgreSQL/ParadeDB làm backend duy nhất, không chuyển sang Elasticsearch/OpenSearch, và chọn tokenizer bằng cách đo recall@k trên Bộ kiểm tra keyword. Các ứng viên là `chinese_lindera`, `icu`, `whitespace` kèm lowercase, và mỗi loại có hoặc không có trường bỏ dấu. Tokenizer thắng được đưa vào bằng migration trong Fork, kèm migration down để rollback. Khi đã chốt tokenizer, ghi tên nó vào ADR này và đổi status thành `accepted`.

## Consequences

Đổi tokenizer phải dựng lại chỉ mục BM25 trên mọi chunk đã có. Nâng cấp WeKnora gốc mà có migration đụng tới chỉ mục này thì phải đối chiếu lại thủ công.
