# Embedding 1024 chiều qua MRL thay vì 2048 chiều gốc

`Qwen3-VL-Embedding-2B` sinh vector 2048 chiều, nhưng WeKnora chỉ tạo chỉ mục HNSW cho 798, 1024 và 3584 chiều (`000002_embeddings`, `000059_embeddings_hnsw_1024`). Kiểu `vector` của pgvector cũng không đánh chỉ mục HNSW được quá 2000 chiều. Chúng tôi lưu 1024 chiều: bật Custom Output Dimension để embeder-gateway cắt vector theo MRL rồi chuẩn hoá lại. Nhờ vậy dùng được chỉ mục có sẵn mà không phải viết migration.

## Considered Options

- 2048 chiều kèm migration chỉ mục `halfvec` mới: giữ đủ độ phân giải nhưng phải vá Fork và tự bảo trì chỉ mục. Chỉ xem xét lại nếu số đo cho thấy 1024 chiều làm giảm recall rõ rệt.

## Consequences

Muốn đổi số chiều, model, mức lượng tử hoá hoặc Document Instruction thì phải embed lại toàn bộ knowledge base.
