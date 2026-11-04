# WeKnora tiếng Việt

Repo triển khai WeKnora để hỏi đáp trên tài liệu tiếng Việt. Ngôn ngữ xử lý là tiếng Việt, Ngôn ngữ giao diện là tiếng Anh (xem `GLOSSARY.md`). Code WeKnora nằm trong submodule Fork `references/WeKnora`; repo này chỉ chứa cấu hình và script.

| File | Vai trò |
| --- | --- |
| `compose.yaml` | Stack: app, frontend, docreader (build từ Fork), postgres (ParadeDB), redis, neo4j |
| `scripts/compose.sh` | Gọi `docker compose`, tag image theo commit Fork |
| `.env.example` | Mẫu `.env`, có ghi chú cho từng biến |
| `config/builtin_models.yaml` | LLM, VLM, embedding, rerank khai báo sẵn, đọc biến từ `.env` |
| `scripts/setup.py` | Cấu hình sau khi dựng: endpoint PaddleOCR-VL, knowledge base mẫu |
| `scripts/check-db.sh` | In `lc_ctype`, chỉ mục và EXPLAIN truy vấn vector |

## Cần có trước

- Docker với Compose v2, `git`, `python3`. Build ba image lần đầu tốn nhiều thời gian và dung lượng đĩa (app cần Go và Rust toolchain, docreader cần Playwright).
- Ba dịch vụ đang chạy và container gọi tới được:
  - LLM OpenAI-compatible có hỗ trợ ảnh;
  - [embeder-gateway](references/embeder-gateway) phục vụ `Qwen3-VL-Embedding-2B` và `Qwen3-VL-Reranker-2B`;
  - [gateway OCR](references/MonkeyOCRv2-B-Parsing-Gateway) phục vụ `/layout-parsing`.

  Nếu chúng chạy trên cùng máy, chúng phải listen trên `0.0.0.0` (embeder-gateway và gateway OCR mặc định chỉ `127.0.0.1`). Container gọi chúng qua `host.docker.internal`.

## Dựng stack

```sh
git submodule update --init references/WeKnora
cp .env.example .env    # điền mọi giá trị <...>
./scripts/compose.sh up -d --build
./scripts/compose.sh ps # chờ cả 6 service "healthy"
python3 scripts/setup.py
```

`scripts/setup.py` chạy lại bao nhiêu lần cũng được:

1. Đăng nhập bằng `WEKNORA_ADMIN_EMAIL`, chưa có tài khoản thì đăng ký.
2. Kiểm tra bốn model built-in đã được nạp.
3. Ghi `PADDLEOCR_VL_ENDPOINT` vào tenant parser settings.
4. Tạo knowledge base `WEKNORA_KB_NAME` nếu chưa có knowledge base cùng tên. Knowledge base đã có thì không bị sửa; muốn tạo lại theo cấu hình mới thì xoá nó trên UI rồi chạy lại.

Knowledge base mẫu dùng cấu hình sau:

- PDF và ảnh (JPG/JPEG/PNG/BMP/TIFF) đi qua `paddleocr_vl`, DOCX/XLSX dùng parser `builtin`.
- Bật parent-child. Kích thước chunk tạm để mặc định.
- Separators: `\n\n`, `\n`, `. `, `; `.
- Mô tả ảnh bằng tiếng Việt qua model `builtin-vlm`.
- Bật knowledge graph, với ví dụ trích thực thể từ văn bản luật.
- Tắt image vector retrieval.

Mở Web UI ở `http://<máy>:${FRONTEND_PORT}` và đăng nhập bằng tài khoản trên.

## Model

`config/builtin_models.yaml` khai báo bốn model. App nạp lại file này mỗi lần khởi động, nên sửa file hoặc `.env` rồi chạy `./scripts/compose.sh up -d` là đủ.

| id | Loại | Model |
| --- | --- | --- |
| `builtin-llm` | KnowledgeQA | `LLM_MODEL_NAME`, `supports_vision`, `context_window` = `LLM_CONTEXT_WINDOW` |
| `builtin-vlm` | VLLM | Cùng LLM. Knowledge base chỉ nhận model loại VLLM để mô tả ảnh |
| `builtin-embedding` | Embedding | `Qwen3-VL-Embedding-2B`, 1024 chiều với dimension override (ADR 0001), compat `input_type_field: input_type`, `max_batch_size: 64` |
| `builtin-rerank` | Rerank | `Qwen3-VL-Reranker-2B`, `score_scale: probability`, chỉ text |

Kiểm tra từng model bằng "Test connection" trong Settings → Models.

## Kiểm tra database

Sau khi upload ít nhất một tài liệu:

```sh
./scripts/check-db.sh | tee docs/db-check.txt
```

Kết quả gồm `SHOW lc_ctype` và EXPLAIN của truy vấn vector 1024 chiều. Bảng nhỏ thì planner chọn seq scan, nên script chạy thêm một lần với `enable_seqscan = off` để xác nhận chỉ mục `embeddings_embedding_idx_1024` dùng được.

## Nâng commit Fork

```sh
git -C references/WeKnora fetch
git -C references/WeKnora checkout <commit>
./scripts/compose.sh up -d --build
git add references/WeKnora    # ghi lại commit Fork đang dùng
```

Dữ liệu nằm trong volume Docker của project `weknora-vi`, nên vẫn còn sau khi build lại. App tự chạy migration khi khởi động. Fork có thay đổi chưa commit thì tag image có hậu tố `-dirty`. `./scripts/compose.sh down -v` xoá luôn dữ liệu.
