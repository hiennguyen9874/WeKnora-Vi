# WeKnora tiếng Việt

Repo triển khai WeKnora để hỏi đáp trên tài liệu tiếng Việt. Ngôn ngữ xử lý là tiếng Việt, Ngôn ngữ giao diện là tiếng Anh (xem `GLOSSARY.md`). Code WeKnora nằm trong Fork `references/WeKnora`; repo này chỉ chứa cấu hình và script.

| File | Vai trò |
| --- | --- |
| `compose.yaml` | Stack: app, frontend, docreader (build từ Fork), postgres (ParadeDB), redis, neo4j |
| `scripts/compose.sh` | Gọi `docker compose`, tag image theo commit Fork |
| `.env.example` | Mẫu `.env`, có ghi chú cho từng biến |
| `config/builtin_models.yaml` | LLM, VLM, embedding, rerank khai báo sẵn, đọc biến từ `.env` |
| `config/prompt_templates/` | Overlay toàn bộ prompt templates; chỉ ví dụ của rewrite mặc định đổi sang tiếng Việt |
| `scripts/setup.py` | Cấu hình sau khi dựng: endpoint PaddleOCR-VL, knowledge base mẫu |
| `scripts/check-db.sh` | In `lc_ctype`, chỉ mục và EXPLAIN truy vấn vector |
| `scripts/e2e.py` | Script E2E: nạp tài liệu mẫu, kiểm tra chunk, đo recall@k và MRR |
| `eval/documents.json` | Tài liệu mẫu (nguồn, sha256) và các kiểm tra chunk của từng tài liệu |
| `eval/keyword-set.json` | Bộ kiểm tra keyword đã duyệt: 30 câu (26 có đáp án, 4 không có đáp án) |
| `eval/keyword-set-review.md` | Xác nhận duyệt, đáp án, vị trí nguồn và cách chạy baseline riêng |
| `fixtures/legal/` | Tài liệu mẫu: văn bản pháp luật công khai |
| `results/baseline.json` | Baseline đầy đủ 30 câu trên Fork chưa vá (#4) |

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
4. Tạo knowledge base `WEKNORA_KB_NAME` nếu chưa có knowledge base cùng tên. Knowledge base đã có thì chỉ đưa cấu hình chunk (`CHUNKING` trong script: strategy và kích thước) về giá trị đã chốt, cấu hình khác giữ nguyên; tài liệu đã nạp phải nạp lại mới chunk theo cấu hình mới. Muốn tạo lại theo toàn bộ cấu hình mới thì xoá nó trên UI rồi chạy lại.

Knowledge base mẫu dùng cấu hình sau:

- PDF và ảnh (JPG/JPEG/PNG/BMP/TIFF) đi qua `paddleocr_vl`, DOCX/XLSX dùng parser `builtin`.
- Chunking strategy `auto`: chunker cắt theo tiêu đề Chương/Mục/Điều và gắn breadcrumb (xem [Chunker cho văn bản pháp lý](#chunker-cho-văn-bản-pháp-lý)). Bỏ trống strategy là tầng legacy, không cắt theo tiêu đề.
- Bật parent-child: chunk cha 4096 ký tự, chunk con 384 ký tự, token limit 512, ngôn ngữ chunker `vi` (xem [Kích thước chunk](#kích-thước-chunk)).
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

## Prompt và Ngôn ngữ xử lý

Fork ánh xạ `vi` và `vi-VN` thành `Vietnamese` khi đưa Ngôn ngữ xử lý vào prompt, không thêm locale cho UI. Giữ `WEKNORA_LANGUAGE=vi-VN`, `DEFAULT_LOCALE=en-US` và `VITE_DEFAULT_LOCALE=en-US` trong `.env`.

Compose mount read-only **cả thư mục** `config/prompt_templates/` vào `/app/config/prompt_templates`. Overlay là bản sao từ Fork, chỉ thay ví dụ tiếng Trung trong `content` của `default_rewrite` bằng ví dụ tiếng Việt (kể cả ví dụ nằm trong hướng dẫn phân loại intent). Các template khác và nhãn i18n giữ nguyên. Khi nâng Fork, đồng bộ lại toàn bộ thư mục rồi áp lại phần ví dụ tiếng Việt; mount thư mục sẽ che các template mới trong image nếu không đồng bộ.

Sau khi sửa overlay, recreate app để nạp lại (không cần build nếu chỉ sửa YAML):

```sh
./scripts/compose.sh up -d --no-deps --force-recreate app
# Sau khi sửa code ánh xạ trong Fork, build app trước:
# ./scripts/compose.sh build app
```

Kết quả kiểm chứng #5 và cách chạy lại: [`docs/validation/issue-5.md`](docs/validation/issue-5.md). Đã kiểm tra summary, rewrite, caption và câu hỏi gợi ý qua API với `Accept-Language: en-US`, cùng tên agent/template hiển thị tiếng Anh trong Chrome. Câu hỏi gợi ý từ chunk chỉ có khi bật `question_generation_config.enabled` cho knowledge base trước khi nạp; setup mặc định không bật và bản vá này không đổi mặc định đó.

## Footnote khi OCR

Fork không còn bỏ nhãn `footnote` trong request PaddleOCR-VL; header, footer, số trang và aside vẫn nằm trong danh sách bỏ qua. Go test đã chạy đỏ → xanh, nhưng nghiệm thu #6 trên stack **còn bị chặn**: gateway OCR ở chế độ `two-stage` trả nội dung rỗng cho block Footnote. Cả sáu kiểm tra footnote và ba câu hỏi footnote hybrid vẫn fail. Cần sửa nhận dạng Footnote trong gateway rồi nạp lại tài liệu; không thể khôi phục text chỉ bằng đổi danh sách nhãn. Xem [kết quả E2E và probe gateway](docs/validation/issue-6.md).

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

Chạy trên stack đã dựng và đã chạy `scripts/setup.py`. Script chỉ gọi HTTP API của WeKnora, thêm `psql` để đọc tên tokenizer BM25 và breadcrumb của chunk, vì API không trả hai thông tin này:

```sh
python3 scripts/e2e.py                            # ghi results/<thời điểm>-<commit Fork>.json
# Chốt lại baseline: dùng stack Fork chưa vá riêng theo eval/keyword-set-review.md
python3 scripts/e2e.py --keep-kb                  # giữ knowledge base để xem chunk trên UI
```

Mỗi lần chạy:

1. Tạo knowledge base `e2e-<thời điểm>` bằng đúng cấu hình của `scripts/setup.py`.
2. Upload mọi tài liệu trong `eval/documents.json`, chờ tới khi tìm kiếm được (`finalizing`, tức là tóm tắt và knowledge graph có thể vẫn chạy nền). Ba tài liệu mẫu mất khoảng 5 phút qua gateway OCR.
3. Kiểm tra chunk con (`text`), mỗi kiểm tra báo PASS/FAIL riêng:
   - `footnotes`: mỗi đoạn trong `footnotes` của tài liệu nằm trọn trong một chunk;
   - `dieu_headings`: mỗi tiêu đề trong `headings` (ví dụ `Điều 4. Hiệu lực thi hành`) nằm trọn trong một chunk, tức là không bị cắt ngang;
   - `breadcrumbs`: với mỗi mục trong `breadcrumbs` của tài liệu, một chunk con chứa `text` có breadcrumb (`context_header`) chứa mọi chuỗi trong `header`, ví dụ `Chương III` và `Điều 11. ...`. API không trả breadcrumb nên script đọc nó bằng `psql`;
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

`eval/keyword-set.json` là bộ đầy đủ **30 câu đã được người dùng duyệt** cho issue #4: 26 câu có đáp án, 4 câu không có đáp án, mỗi nhóm ca khó có ít nhất 2 câu. Bộ câu gồm seed, đề xuất `q12` của issue #8 và các câu mới; q07 được hỏi lại để đoạn mong đợi chứa đáp án. Xem [xác nhận duyệt, bảng đáp án và nguồn](eval/keyword-set-review.md), kèm lệnh kiểm tra không gọi dịch vụ và hướng dẫn chạy baseline trên stack riêng.

Baseline đầy đủ đã chạy trên stack riêng với Fork chưa vá `fd7a2586fd58`, tokenizer `chinese_lindera`, embedding 1024 chiều; kết quả nằm trong `results/baseline.json`. Recall@10 keyword/vector/hybrid lần lượt là 0,6154 / 0,7692 / 0,8077. NFC pass; footnote, tiêu đề Điều và breadcrumb còn fail như ghi trong [bảng kết quả baseline](eval/keyword-set-review.md#kết-quả-baseline-đầy-đủ-4).

Không so sánh điểm tổng hợp của bộ 30 câu với các kết quả seed cũ. Baseline seed lịch sử vẫn có trong Git tại commit `72f03bd`; các bảng ở phần chunker bên dưới cũng là kết quả seed lịch sử. Các lần so sánh mới phải dùng cùng bộ câu, tài liệu, model và cấu hình chunking.

### Đọc kết quả

Script in tóm tắt, rồi ghi file JSON:

- `fork`, `tokenizer`, `models.embedding` (tên, số chiều), `chunking`: cấu hình đã đo. So sánh hai lần chạy chỉ có nghĩa khi biết phần nào đã đổi.
- `documents`: trạng thái parse, số giây tới khi tìm kiếm được, số chunk con và chunk cha.
- `chunk_checks.<tên>`: `pass`, số mục đã kiểm tra và danh sách mục fail.
- `search.modes.<chế độ>`: `recall@k` (k = 1, 3, 5, 10) là tỉ lệ câu có đáp án mà kết quả trúng đầu tiên nằm trong top k. `mrr` là trung bình 1/hạng của kết quả trúng đầu tiên, câu không trúng trong top 10 tính 0. `failed` là danh sách câu trượt.
- `questions`: từng câu, với hạng trúng (`rank`, `null` là trượt), điểm cao nhất và 3 kết quả đầu ở mỗi chế độ.

`results/` bị gitignore, trừ `results/baseline.json` (Fork chưa vá), `results/chunker-vi.json` (sau vá chunker), `results/chunker-legal.json` (sau vá tiêu đề văn bản pháp lý) và `results/chars-per-token.json`.

## Kích thước chunk

Bản vá chunker của Fork (`internal/infrastructure/chunker`): văn bản có từ 10% chữ cái chỉ tiếng Việt mới có (ă, đ, ơ, ư, ĩ, ũ và nguyên âm U+1EA0..U+1EF9) được nhận là `vi`; `vi` dùng tỉ lệ 2,5 ký tự/token, và khi không khai báo separators thì mặc định là `\n\n`, `\n`, `. `, `; `.

### Đo ký tự/token

```sh
python3 scripts/e2e.py --keep-kb --out results/chunker-vi.json
python3 scripts/measure_tokens.py --kb <kb_id trong run của file trên>   # ghi results/chars-per-token.json
```

Script gửi từng chunk con của tài liệu mẫu tới embeder-gateway (`EMBEDER_GATEWAY_URL`, hoặc `--embedder-url` nếu URL đó chỉ đúng từ container) và lấy `usage.prompt_tokens` trừ 20 token cố định của prompt format, tức là đếm bằng tokenizer thật của `Qwen3-VL-Embedding-2B`. Ký tự đếm bằng code point, như rune của chunker. Script cũng ghép lại toàn văn từ offset chunk để đo độ dài từng Điều, và dò giới hạn input của embedder. Xoá knowledge base `e2e-*` sau khi đo.

Kết quả trên ba tài liệu mẫu (291 chunk con từ 100 ký tự):

| Đo | Giá trị |
| --- | --- |
| Ký tự/token, toàn bộ | 3,18 |
| Ký tự/token theo chunk: p5 / p10 / p50 | 2,31 / 2,48 / 3,25 (thấp nhất 1,62, bảng số) |
| Giới hạn input của embedder | 8171 token nội dung |
| Chunk con lớn nhất | 254 token |
| Độ dài Điều: p50 / p90 | 560 / 2600 ký tự; chỉ hai Điều vượt 4096 (5019 và 6342) |

Tỉ lệ của `vi` trong Fork là 2,5 (khoảng p10), thấp hơn trung bình để bảng và số không bị đếm thiếu token. Chunker còn nhân thêm 0,9, nên token limit 512 cho trần 1152 ký tự.

### Cỡ đã chốt

`scripts/setup.py` (`CHUNKING`): `languages: ["vi"]`, chunk cha 4096, chunk con 384, token limit 512.

- Chunk cha 4096 ký tự chứa trọn một Điều, trừ hai Điều dài nhất. Chunker cắt ở ranh giới Điều rồi gộp các Điều ngắn liền nhau cho tới khi chunk cha đạt khoảng 2048 ký tự (không quá 4096), nên một chunk cha có thể gồm vài Điều ngắn nhưng không bắt đầu giữa một Điều (trừ Điều dài hơn 4096).
- Chunk con 384 ký tự (khoảng 120 token). Cặp 4096 / 384 là cặp duy nhất đã thử không tệ hơn baseline ở chỉ số nào của vector và hybrid. Chunk con lớn hơn tăng R@10 nhưng giảm R@1 và MRR; 3000 / 384 tăng vector nhưng hybrid giảm R@3 (0,56 xuống 0,44) và MRR.
- Token limit 512 chỉ là trần an toàn khi ai đó tăng cỡ chunk con; với 384 ký tự nó không cắt gì.

E2E trên Fork đã vá (`fd7a2586fd58-dirty`), 9 câu có đáp án:

| Cha / con | Vector R@1 / R@10 / MRR | Hybrid R@1 / R@10 / MRR |
| --- | --- | --- |
| Baseline (4096 / 384 mặc định, chưa vá) | 0,56 / 0,78 / 0,60 | 0,44 / 0,78 / 0,52 |
| **4096 / 384 (đã chốt)** | 0,56 / 0,78 / 0,60 | 0,44 / 0,78 / 0,52 |
| 4096 / 512 | 0,44 / 0,89 / 0,56 | 0,33 / 0,78 / 0,50 |
| 3000 / 384 | 0,67 / 0,78 / 0,68 | 0,44 / 0,78 / 0,51 |
| 3000 / 512 | 0,44 / 0,89 / 0,55 | 0,33 / 0,89 / 0,48 |
| 3000 / 768 | 0,44 / 0,78 / 0,58 | 0,33 / 0,67 / 0,46 |

Phép so sánh lịch sử trên chỉ có 9 câu có đáp án, nên mỗi câu đổi hạng là 0,11 điểm recall. Bộ hiện tại đã có 26 câu có đáp án; cần chạy lại cả baseline và các cỡ chunk trên cùng bộ này trước khi kết luận bằng điểm mới.

## Chunker cho văn bản pháp lý

Bản vá chunker của Fork cho văn bản pháp lý tiếng Việt (`internal/infrastructure/chunker`):

- Dòng `Phần`/`Chương`/`Mục` kèm số La Mã hoặc Ả Rập, và `Điều N.` (số La Mã hoặc Ả Rập, cả `Điều 11a.`), là tiêu đề, dù OCR trả về dạng `## ...` hay dòng thường. Cấp của chúng theo cấu trúc luật: Phần > Chương > Mục > Điều, còn Điều trong ngoặc kép (`“Điều 4. ...`, nội dung được sửa đổi) nằm dưới Điều sửa đổi nó. Dòng nhắc tới Điều trong câu (`Điều 37 của Thông tư ...`) không phải tiêu đề.
- Khoản (`1.`, `2.`) không phải tiêu đề với `languages: ["vi"]`; các ngôn ngữ khác giữ mẫu `1. Title` như cũ.
- Dòng tiêu đề Chương/Mục/Điều không bị cắt, kể cả khi dài hơn chunk con (Điều 1 của Thông tư 32/2024 dài khoảng 520 ký tự). Trước đây separator `. ` tách `Điều 1.` khỏi tên Điều.
- Section quá lớn được cắt ở tiêu đề con trước (Chương dài cắt ở từng Điều), chỉ phần còn quá lớn mới cắt theo separator.
- Breadcrumb của chunk con là đường tiêu đề tại đầu chunk con đó, ví dụ `## Chương III ... > #### Điều 11. ...`, kể cả khi chunk cha gộp vài Điều ngắn.
- Tiêu đề viết hoa có dấu tiếng Việt (`NHỮNG QUY ĐỊNH CHUNG`) được đưa vào breadcrumb ngay cả khi không có dấu `#`. Tiêu đề hoa nằm sau dòng chỉ có Phần/Chương/Mục và số được ghép vào tên cấp đó, không làm mất ngữ cảnh khi sang Điều. Breadcrumb chunk con được lấy theo vị trí trong toàn văn, kể cả khi tầng heuristic cắt chunk cha ở giữa Điều.
- Chân trang nhận `Trang N` và `Trang N/M` ở tầng heuristic, cho tài liệu không có tiêu đề Markdown.

Mọi điều trên chỉ chạy khi chunking strategy là `auto` (hoặc `heading`/`heuristic`). `scripts/setup.py` đặt `auto`.

E2E (`results/chunker-legal.json`, Fork `456b05ec45f9-dirty`, 4096 / 384):

| Lần chạy | `dieu_headings` | Keyword R@1 / MRR | Vector R@1 / MRR | Hybrid R@1 / MRR |
| --- | --- | --- | --- | --- |
| Baseline (legacy, chưa vá) | 1/27 fail | 0,44 / 0,50 | 0,56 / 0,60 | 0,44 / 0,52 |
| `chunker-vi` (legacy, vá ngôn ngữ) | 1/27 fail | 0,44 / 0,50 | 0,56 / 0,60 | 0,44 / 0,52 |
| **`chunker-legal` (auto, vá tiêu đề)** | pass | 0,56 / 0,56 | 0,78 / 0,78 | 0,78 / 0,78 |

Trong lần chạy seed lịch sử trên, kiểm tra `breadcrumbs` pass 5/5. R@10 không đổi ở cả ba chế độ: câu đúng chỉ lên hạng 1 (q01, q05, q06, q08). Không câu nào tụt hạng ở chế độ nào. Bộ seed đó chưa có câu dạng "Điều X Khoản Y", nên chưa đo được loại câu này; bộ 30 câu đã duyệt hiện có q12, q13, q20 và q29 thuộc nhóm này. q07 (footnote) và q09 (bảng) trượt trong lần chạy seed đó.

Các sửa lỗi sau review (Điều số La Mã, tiêu đề hoa trong breadcrumb và ngữ cảnh xuyên chunk cha) đã qua Go test, nhưng chưa build/deploy hay chạy lại E2E. Bảng trên là kết quả lịch sử, không phải nghiệm thu các sửa lỗi này.

## Nâng commit Fork

```sh
git -C references/WeKnora fetch
git -C references/WeKnora checkout <commit>
./scripts/compose.sh up -d --build
git add references/WeKnora    # ghi lại commit Fork đang dùng
```

Dữ liệu nằm trong volume Docker của project `weknora-vi`, nên vẫn còn sau khi build lại. App tự chạy migration khi khởi động. Fork có thay đổi chưa commit thì tag image có hậu tố `-dirty`. `./scripts/compose.sh down -v` xoá luôn dữ liệu.
