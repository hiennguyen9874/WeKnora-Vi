# #8: Chunker cho tiêu đề và chân trang văn bản pháp lý

Kết quả lịch sử chuyển từ README; không phải lượt nghiệm thu mới. Phép đo dùng bộ seed 9 câu có đáp án, trước khi có Bộ kiểm tra keyword 30 câu (#4).

## E2E

`results/chunker-legal.json`, Fork `456b05ec45f9-dirty`, chunk cha/con 4096 / 384:

| Lần chạy | `dieu_headings` | Keyword R@1 / MRR | Vector R@1 / MRR | Hybrid R@1 / MRR |
| --- | --- | --- | --- | --- |
| Baseline (legacy, chưa vá) | 1/27 fail | 0,44 / 0,50 | 0,56 / 0,60 | 0,44 / 0,52 |
| `chunker-vi` (legacy, vá ngôn ngữ) | 1/27 fail | 0,44 / 0,50 | 0,56 / 0,60 | 0,44 / 0,52 |
| **`chunker-legal` (auto, vá tiêu đề)** | pass | 0,56 / 0,56 | 0,78 / 0,78 | 0,78 / 0,78 |

- Kiểm tra `breadcrumbs` pass 5/5.
- R@10 không đổi ở cả ba chế độ: câu đúng chỉ lên hạng 1 (q01, q05, q06, q08). Không câu nào tụt hạng ở chế độ nào.
- q07 (footnote) và q09 (bảng) trượt.
- Bộ seed chưa có câu dạng "Điều X Khoản Y"; bộ 30 câu hiện có q12, q13, q20 và q29 thuộc nhóm này.

## Giới hạn

Các sửa lỗi sau review (Điều số La Mã, tiêu đề viết hoa trong breadcrumb, ngữ cảnh xuyên chunk cha) đã qua Go test nhưng chưa build/deploy hay chạy lại E2E. Bảng trên không nghiệm thu các sửa lỗi này.
