# WeKnora tiếng Việt

Triển khai [WeKnora](https://github.com/Tencent/WeKnora) để hỏi đáp trên tài liệu tiếng Việt, chủ yếu là văn bản pháp luật và hành chính. Câu trả lời, tóm tắt và mô tả ảnh bằng tiếng Việt; Web UI giữ tiếng Anh (xem `GLOSSARY.md`).

Repo này chỉ chứa cấu hình, script và bộ kiểm tra. Code WeKnora nằm trong Fork `references/WeKnora` (submodule).

## Cần có trước

- Docker với Compose v2, `git`, `python3`. Build lần đầu tốn nhiều thời gian và dung lượng đĩa.
- Ba dịch vụ đang chạy, container gọi tới được:
  - LLM OpenAI-compatible có hỗ trợ ảnh;
  - [embeder-gateway](references/embeder-gateway) phục vụ `Qwen3-VL-Embedding-2B` và `Qwen3-VL-Reranker-2B`;
  - [gateway OCR](references/MonkeyOCRv2-B-Parsing-Gateway) phục vụ `/layout-parsing`.

  Container gọi chúng qua `host.docker.internal`. Nếu chúng chạy cùng máy, cho chúng listen trên `0.0.0.0` (hai gateway mặc định chỉ listen `127.0.0.1`).

## Dựng stack

```sh
git submodule update --init references/WeKnora
cp .env.example .env              # điền mọi giá trị <...>, xem ghi chú trong file
./scripts/compose.sh up -d --build
./scripts/compose.sh ps           # chờ cả 6 service "healthy"
python3 scripts/setup.py          # tạo tài khoản admin, cấu hình OCR, tạo knowledge base mẫu
./scripts/compose.sh up -d --force-recreate app   # cấp quyền system admin cho tài khoản vừa tạo
```

- Đặt `WEKNORA_BOOTSTRAP_SYSTEM_ADMIN_EMAIL` trùng `WEKNORA_ADMIN_EMAIL` trước khi dựng. Quyền system admin chỉ được cấp khi tài khoản đã tồn tại và deployment chưa có system admin, nên phải recreate app **sau** lần chạy `setup.py` đầu tiên.
- `scripts/setup.py` chạy lại bao nhiêu lần cũng được. Knowledge base `WEKNORA_KB_NAME` đã có thì chỉ đưa cấu hình chunk về giá trị chuẩn; tài liệu đã nạp phải nạp lại mới chunk theo cấu hình mới.

## Sử dụng

1. Mở `http://<máy>:${FRONTEND_PORT}`, đăng nhập bằng `WEKNORA_ADMIN_EMAIL`. Nếu đã đăng nhập trước khi được cấp quyền system admin, đăng xuất rồi đăng nhập lại.
2. Vào Settings → Models, chạy "Test connection" cho từng model: `builtin-llm`, `builtin-vlm`, `builtin-embedding`, `builtin-rerank`.
3. Upload tài liệu vào knowledge base mẫu rồi đặt câu hỏi. PDF và ảnh được OCR qua gateway OCR; DOCX/XLSX dùng parser có sẵn.

## Đổi cấu hình

| Sửa | Áp dụng |
| --- | --- |
| `.env`, `config/builtin_models.yaml`, `config/prompt_templates/` | `./scripts/compose.sh up -d --force-recreate app` |
| Commit Fork | `./scripts/compose.sh up -d --build` |

Dữ liệu nằm trong volume Docker của project `weknora-vi`, vẫn còn sau khi build lại. **`./scripts/compose.sh down -v` xoá toàn bộ dữ liệu.**

## Nâng commit Fork

```sh
git -C references/WeKnora fetch
git -C references/WeKnora checkout <commit>
./scripts/compose.sh up -d --build   # app tự chạy migration khi khởi động
git add references/WeKnora           # ghi lại commit Fork đang dùng
```

Image được tag theo commit Fork; Fork có thay đổi chưa commit thì tag thêm hậu tố `-dirty`.

## Rollback tokenizer BM25

Fork dùng tokenizer `icu` (migration `137`, ADR 0002). Sao lưu database, rồi trả về `chinese_lindera` bằng:

```sh
./scripts/compose.sh exec app sh -c 'migrate -path /app/migrations/versioned -database "postgres://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=disable" goto 136'
```

App migrate lại lên `icu` mỗi khi khởi động; muốn giữ `chinese_lindera` phải dùng image Fork không có migration `137`. Chi tiết: [`docs/validation/issue-12.md`](docs/validation/issue-12.md).

## Kiểm tra

```sh
python3 scripts/e2e.py           # nạp tài liệu mẫu, kiểm tra chunk, đo recall@k/MRR; ghi results/*.json
./scripts/check-db.sh            # lc_ctype và chỉ mục vector của PostgreSQL (cần đã có tài liệu)
```

## Tài liệu

- `GLOSSARY.md`: thuật ngữ của dự án.
- `docs/adr/`: các quyết định kiến trúc.
- `docs/validation/`: kết quả nghiệm thu từng issue.
- `AGENTS.md` và `docs/agents/`: hướng dẫn cho coding agent (vá Fork, đồng bộ upstream, chạy E2E và ghi nghiệm thu).
