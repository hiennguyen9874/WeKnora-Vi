# WeKnora tiếng Việt

Repo triển khai WeKnora để hỏi đáp trên tài liệu tiếng Việt. Ngôn ngữ xử lý là tiếng Việt, Ngôn ngữ giao diện là tiếng Anh (xem `GLOSSARY.md`). Code WeKnora nằm trong Fork `references/WeKnora`; repo này chỉ chứa cấu hình và script.

| File | Vai trò |
| --- | --- |
| `compose.yaml` | Stack: app, frontend, docreader (build từ Fork), postgres (ParadeDB), redis, neo4j |
| `scripts/compose.sh` | Gọi `docker compose`, tag image theo commit Fork |
| `.env.example` | Mẫu `.env`, có ghi chú cho từng biến |
| `config/builtin_models.yaml` | LLM, VLM, embedding, rerank khai báo sẵn, đọc biến từ `.env` |
| `scripts/setup.py` | Cấu hình sau khi dựng: endpoint PaddleOCR-VL, knowledge base mẫu |
| `scripts/check-db.sh` | In `lc_ctype`, chỉ mục và EXPLAIN truy vấn vector |
| `scripts/e2e.py` | Script E2E: nạp tài liệu mẫu, kiểm tra chunk, đo recall@k và MRR |
| `eval/documents.json` | Tài liệu mẫu (nguồn, sha256) và các kiểm tra chunk của từng tài liệu |
| `eval/keyword-set.json` | Bộ kiểm tra keyword |
| `fixtures/legal/` | Tài liệu mẫu: văn bản pháp luật công khai |
| `results/baseline.json` | Kết quả E2E trên Fork chưa vá |

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
# Sau khi tài khoản đã được đăng ký, bootstrap quyền system admin:
./scripts/compose.sh up -d --force-recreate app
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

Đặt `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL` trong `.env` trùng với `WEKNORA_ADMIN_EMAIL` trước khi dựng stack. Fork chỉ nâng quyền khi tài khoản đã tồn tại và deployment chưa có system admin, nên cần recreate app **sau** lần setup đăng ký tài khoản. Nếu đã có system admin khác, nhờ người đó cấp quyền cho tài khoản này.

Mở Web UI ở `http://<máy>:${FRONTEND_PORT}` và đăng nhập bằng tài khoản trên. Nếu đã đăng nhập trước khi nâng quyền, đăng xuất rồi đăng nhập lại để cập nhật quyền system admin.

## Model

`config/builtin_models.yaml` khai báo bốn model. App chỉ nạp file này khi khởi động. Sau khi sửa file hoặc `.env`, recreate app để nạp lại cả model và biến môi trường (chỉ `up -d` không khởi động lại app khi chỉ YAML thay đổi):

```sh
./scripts/compose.sh up -d --force-recreate app
```

| id | Loại | Model |
| --- | --- | --- |
| `builtin-llm` | KnowledgeQA | `LLM_MODEL_NAME`, `supports_vision`, `context_window` = `LLM_CONTEXT_WINDOW` |
| `builtin-vlm` | VLLM | Cùng LLM. Knowledge base chỉ nhận model loại VLLM để mô tả ảnh |
| `builtin-embedding` | Embedding | `Qwen3-VL-Embedding-2B`, 1024 chiều với dimension override (ADR 0001), compat `input_type_field: input_type`, `max_batch_size: 64` |
| `builtin-rerank` | Rerank | `Qwen3-VL-Reranker-2B`, `score_scale: probability`, chỉ text |

Dùng tài khoản **system admin** mở từng model và chạy "Test connection" trong Settings → Models. Tài khoản do setup đăng ký chỉ là workspace owner cho tới khi hoàn tất bootstrap ở trên.

## Kiểm tra database

Sau khi upload ít nhất một tài liệu:

```sh
./scripts/check-db.sh | tee docs/db-check.txt
```

Kết quả gồm `SHOW lc_ctype` và EXPLAIN của truy vấn vector 1024 chiều. Bảng nhỏ thì planner chọn seq scan, nên script chạy thêm một lần với `enable_seqscan = off` để xác nhận chỉ mục `embeddings_embedding_idx_1024` dùng được.

## Trạng thái kiểm chứng triển khai

Chưa có kết quả nghiệm thu trên stack thật; cấu hình và script không thay thế bằng chứng chạy thực tế. Trên máy deploy đã điền `.env` và có đủ ba dịch vụ model/OCR, cần chạy và lưu kết quả:

- [ ] Build stack, xác nhận cả sáu service healthy bằng `./scripts/compose.sh ps`.
- [ ] Chạy `python3 scripts/setup.py` hai lần liên tiếp, không lỗi và không tạo knowledge base trùng.
- [ ] Hoàn tất bootstrap system admin, chạy "Test connection" cho từng model.
- [ ] Upload PDF scan tiếng Việt, xác nhận parse qua gateway OCR và text đúng dấu.
- [ ] Hỏi trên tài liệu trong Web UI tiếng Anh, xác nhận câu trả lời tiếng Việt có trích dẫn.
- [ ] Chạy lệnh kiểm tra database ở trên, lưu `docs/db-check.txt`, xác nhận `lc_ctype` và EXPLAIN dùng HNSW 1024.

## Script E2E

Chạy trên stack đã dựng và đã chạy `scripts/setup.py`. Script chỉ gọi HTTP API của WeKnora (thêm một lệnh `psql` để đọc tên tokenizer BM25, vì API không trả thông tin này):

```sh
python3 scripts/e2e.py                            # ghi results/<thời điểm>-<commit Fork>.json
python3 scripts/e2e.py --out results/baseline.json  # chỉ khi chốt lại baseline
python3 scripts/e2e.py --keep-kb                  # giữ knowledge base để xem chunk trên UI
```

Mỗi lần chạy:

1. Tạo knowledge base `e2e-<thời điểm>` bằng đúng cấu hình của `scripts/setup.py`.
2. Upload mọi tài liệu trong `eval/documents.json`, chờ tới khi tìm kiếm được (`finalizing`, tức là tóm tắt và knowledge graph có thể vẫn chạy nền). Ba tài liệu mẫu mất khoảng 5 phút qua gateway OCR.
3. Kiểm tra chunk con (`text`), mỗi kiểm tra báo PASS/FAIL riêng:
   - `footnotes`: mỗi đoạn trong `footnotes` của tài liệu nằm trọn trong một chunk;
   - `dieu_headings`: mỗi tiêu đề trong `headings` (ví dụ `Điều 4. Hiệu lực thi hành`) nằm trọn trong một chunk, tức là không bị cắt ngang;
   - `nfc`: mọi chunk (cả chunk cha) ở dạng Unicode NFC.
4. Gửi từng câu của Bộ kiểm tra keyword tới `hybrid-search` với `match_count` 10, `skip_context_enrichment` và ngưỡng 0, ở 3 chế độ: `keyword` (`disable_vector_match`), `vector` (`disable_keywords_match`), `hybrid`.
5. Xoá knowledge base, trừ khi có `--keep-kb`.

Kiểm tra chunk fail không làm script thoát lỗi: trên Fork chưa vá, kết quả fail là baseline. Script thoát mã 1 khi tài liệu parse lỗi hoặc API lỗi.

### Bộ kiểm tra keyword

`eval/keyword-set.json` có dạng:

```json
{"questions": [
  {"id": "q05", "query": "Vàng miếng là gì?", "form": "nfd", "answerable": true,
   "expected": ["Vàng miếng là sản phẩm vàng được dập thành miếng"],
   "doc": "vbhn-117-2026-nd-nhnn", "tags": ["nfd", "dinh-nghia"]},
  {"id": "q10", "query": "...", "answerable": false, "tags": ["khong-co-dap-an"]}
]}
```

- `expected`: các đoạn văn bản, kết quả nào chứa một trong các đoạn này là trúng. Không dùng chunk ID, vì ID đổi mỗi lần nạp. Khi so khớp, cả hai phía được chuẩn hoá NFC, bỏ `**` và gộp khoảng trắng. Chọn đoạn ngắn, chỉ xuất hiện ở chỗ đúng, không vắt qua ô bảng hay ranh giới chunk.
- `answerable: false`: câu không có đáp án trong tài liệu mẫu, không có `expected` và không tính vào điểm. File kết quả vẫn ghi điểm cao nhất của nó ở từng chế độ.
- `form`: `nfc` (mặc định) hoặc `nfd`; script đổi câu hỏi sang dạng này trước khi gửi. Câu không dấu thì viết thẳng không dấu trong `query`.
- `doc` (id trong `eval/documents.json`) và `tags` chỉ để đọc kết quả.

### Đọc kết quả

Script in tóm tắt, rồi ghi file JSON:

- `fork`, `tokenizer`, `models.embedding` (tên, số chiều), `chunking`: cấu hình đã đo. So sánh hai lần chạy chỉ có nghĩa khi biết phần nào đã đổi.
- `documents`: trạng thái parse, số giây tới khi tìm kiếm được, số chunk con và chunk cha.
- `chunk_checks.<tên>`: `pass`, số mục đã kiểm tra và danh sách mục fail.
- `search.modes.<chế độ>`: `recall@k` (k = 1, 3, 5, 10) là tỉ lệ câu có đáp án mà kết quả trúng đầu tiên nằm trong top k. `mrr` là trung bình 1/hạng của kết quả trúng đầu tiên, câu không trúng trong top 10 tính 0. `failed` là danh sách câu trượt.
- `questions`: từng câu, với hạng trúng (`rank`, `null` là trượt), điểm cao nhất và 3 kết quả đầu ở mỗi chế độ.

`results/` bị gitignore, trừ `results/baseline.json`.

## Nâng commit Fork

```sh
git -C references/WeKnora fetch
git -C references/WeKnora checkout <commit>
./scripts/compose.sh up -d --build
git add references/WeKnora    # ghi lại commit Fork đang dùng
```

Dữ liệu nằm trong volume Docker của project `weknora-vi`, nên vẫn còn sau khi build lại. App tự chạy migration khi khởi động. Fork có thay đổi chưa commit thì tag image có hậu tố `-dirty`. `./scripts/compose.sh down -v` xoá luôn dữ liệu.
