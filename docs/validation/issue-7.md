# #7: Chunker nhận diện tiếng Việt và kích thước chunk

Kết quả lịch sử chuyển từ README; không phải lượt nghiệm thu mới. Phép đo dùng bộ seed 9 câu có đáp án, trước khi có Bộ kiểm tra keyword 30 câu (#4), nên không so sánh điểm ở đây với `results/baseline.json`.

## Đo ký tự/token

```sh
python3 scripts/e2e.py --keep-kb --out results/chunker-vi.json
python3 scripts/measure_tokens.py --kb <kb_id trong run của file trên>   # ghi results/chars-per-token.json
```

Kết quả trên ba tài liệu mẫu PDF (291 chunk con từ 100 ký tự), lưu ở `results/chars-per-token.json`:

| Đo | Giá trị |
| --- | --- |
| Ký tự/token, toàn bộ | 3,18 |
| Ký tự/token theo chunk: p5 / p10 / p50 | 2,31 / 2,48 / 3,25 (thấp nhất 1,62, bảng số) |
| Giới hạn input của embedder | 8171 token nội dung |
| Chunk con lớn nhất | 254 token |
| Độ dài Điều: p50 / p90 | 560 / 2600 ký tự; chỉ hai Điều vượt 4096 (5019 và 6342) |

## So sánh cỡ chunk

E2E trên Fork đã vá (`fd7a2586fd58-dirty`), 9 câu có đáp án; mỗi câu đổi hạng là 0,11 điểm recall:

| Cha / con | Vector R@1 / R@10 / MRR | Hybrid R@1 / R@10 / MRR |
| --- | --- | --- |
| Baseline (4096 / 384 mặc định, chưa vá) | 0,56 / 0,78 / 0,60 | 0,44 / 0,78 / 0,52 |
| **4096 / 384 (đã chốt)** | 0,56 / 0,78 / 0,60 | 0,44 / 0,78 / 0,52 |
| 4096 / 512 | 0,44 / 0,89 / 0,56 | 0,33 / 0,78 / 0,50 |
| 3000 / 384 | 0,67 / 0,78 / 0,68 | 0,44 / 0,78 / 0,51 |
| 3000 / 512 | 0,44 / 0,89 / 0,55 | 0,33 / 0,89 / 0,48 |
| 3000 / 768 | 0,44 / 0,78 / 0,58 | 0,33 / 0,67 / 0,46 |

Cần chạy lại baseline và các cỡ chunk trên Bộ kiểm tra keyword 30 câu trước khi kết luận bằng điểm mới.
