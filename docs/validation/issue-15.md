# #15: Đồng bộ Fork với upstream sau WeKnora 0.9.0

## Trạng thái: đạt kiểm tra merge mã nguồn; chưa nghiệm thu trên stack

Ngày kiểm tra **2026-11-17**. Phạm vi yêu cầu là kéo và merge mã nguồn,
không dựng lại image, khởi động stack hay thay đổi database của deployment.

Commit merge trong Fork: [`818f53a46`](https://github.com/hiennguyen9874/WeKnora/commit/818f53a46830d4de8272146e2202ffb8e1248b9d).

## Nguồn và cách hợp nhất

- Pin cũ: `f7a167385969`; upstream: `https://github.com/Tencent/WeKnora.git`,
  nhánh `main`, commit `7d064bc3a259f87634840199f565ec4dd644ba1e` (180 commit mới).
- Giữ `origin` trỏ về Fork; thêm remote `upstream` trỏ về Tencent.
- Đưa nhánh local `main` đang cũ lên đúng pin bằng fast-forward rồi merge,
  không rebase hay force-push.
- Một xung đột text ở `internal/infrastructure/chunker/strategy.go`:
  giữ `breadcrumbAtOffset` của Fork (ngữ cảnh Chương/Mục/Điều từ toàn tài liệu),
  đồng thời áp `enforceChunkBudget` của upstream **sau** khi gắn breadcrumb.
- Trùng số migration không hiện thành Git conflict: upstream thêm
  `000137_im_session_mode_indexes`, Fork đã dùng `000137_embeddings_bm25_icu`.
  Giữ nguyên file ICU đã áp; đổi hai file IM sang `000138`, cập nhật test tên file.
  Database Fork ở 137 sẽ chạy IM ở 138, không cần hạ/ép version hay dựng lại BM25.
  Không dùng hướng dẫn này để chuyển database Tencent thuần đã áp IM ở 137.
- `config/prompt_templates/` không đổi ở upstream so với pin cũ. Overlay đủ file,
  chỉ `rewrite.yaml` khác Fork như chủ đích (ví dụ tiếng Việt); không cần sao chép lại.

## Bằng chứng đỏ → xanh

### Chunker

Thêm `TestSplitParentChild_VietnameseBreadcrumbBudget` trên fixture luật hiện có,
kiểm tra `auto`, `heading`, `legacy`, cả nội dung embedding và offset nguồn.

- Đỏ: thử giải quyết conflict bằng cách chỉ giữ nhánh breadcrumb của Fork,
  bỏ bước giới hạn token mới. Cả ba strategy fail: ví dụ
  `chunk[5] embedding content: got 575 runes, want <= 270`.
- Xanh: giữ cả breadcrumb lẫn giới hạn token; test này và toàn package chunker pass.
  Đây là trần ký tự ước lượng theo token, không phải tokenization chính xác của model.

### Migration source

- Đỏ: `TestMigrationDirectoriesLoad` trên cây merge trước đổi số fail:
  `duplicate migration file: 000137_im_session_mode_indexes.down.sql`.
  Chạy riêng file test với helper trả về repo root trong thư mục tạm để tránh
  chờ biên dịch các dependency service; không sửa test để bỏ kiểm tra.
- Xanh: sau đổi số, test trên cùng source loader pass. Thêm
  `TestPostgresForkMigration137UpgradePath`: version 137 vẫn là ICU,
  `Next(137)` là 138 chứa migration IM; pass.
- Các kiểm tra này xác nhận danh sách và đường đi migration, **không** chứng minh
  SQL đã chạy trên PostgreSQL thật. Test SQL IM và nâng/hạ ICU cần DSN riêng.

## Kết quả kiểm tra

- `go build -p 2 ./...`: pass (Go 1.26.0, không build tag `anydoc`).
- Toàn package chunker, docparser Go, sourceloc, types, retriever/postgres,
  chat_pipeline và database: pass. Test database cần PostgreSQL bỏ qua vì thiếu DSN;
  pass package không đồng nghĩa migration SQL đã được chạy.
- `scripts/docker-entrypoint_test.sh`: pass.
- Ba file frontend Node nêu dưới: **24/24 pass**. Không thay thế full frontend suite.
- Lượt service đầy đủ: fail hai test phụ thuộc DNS/SSRF đã gặp ở #14:
  `TestDataSourceReplacementCommitsBeforeEnqueueAndCleanup/{url,file_url}`
  (`invalid URL`) và `TestUpdateMCPService_AppliesNonScalarUpdateWithoutName`
  (`DNS resolution failed for hostname example.com`). Không sửa code bảo vệ SSRF
  để làm test xanh.
- Chạy lại đúng hai test trên worktree **upstream thuần `7d064bc3a`**: cùng lỗi
  `invalid URL` và `DNS resolution failed`; xác nhận không phải hồi quy của merge.
- Chạy lại toàn service với `-skip` đúng hai test trên: pass, không còn failure.
- Tóm tắt máy đọc được: [`issue-15-checks.json`](issue-15-checks.json).

## Chạy lại (trong `references/WeKnora`)

```sh
GOMAXPROCS=2 go test -p 2 ./internal/infrastructure/chunker ./internal/infrastructure/docparser ./internal/sourceloc ./internal/types ./internal/application/repository/retriever/postgres ./internal/application/service ./internal/application/service/chat_pipeline ./internal/database -count=1
GOMAXPROCS=2 go test -p 2 ./internal/application/service -skip "^(TestDataSourceReplacementCommitsBeforeEnqueueAndCleanup|TestUpdateMCPService_AppliesNonScalarUpdateWithoutName)$" -count=1
GOMAXPROCS=2 go build -p 2 ./...
bash scripts/docker-entrypoint_test.sh
node --test frontend/src/utils/citationMarkdownMath.test.mjs frontend/src/utils/agent-tool-display.test.mjs frontend/src/components/css/chat-hljs.test.mjs
```

Go tự chọn toolchain `go1.26.0` theo `go.mod`; Node `v24.16.0`.

## Giới hạn / kiểm tra còn chờ

- Docker có sẵn, nhưng `docker ps` chỉ có `chatgpt-next-web` và `cli-proxy-api`,
  không có sáu service WeKnora. Không bật stack vì ngoài phạm vi merge mã nguồn.
- Chưa chạy migration SQL trên ParadeDB/PostgreSQL thật (không cấp
  `WEKNORA_MIGRATION_TEST_POSTGRES_DSN`); chưa kiểm chứng nâng 137 → 138 trên dữ liệu thật.
- Chưa build image, chạy E2E, so retrieval/chunk NFC/NFD hay kiểm tra tay Web UI.
  Chưa có image tag/model/ParadeDB cho lượt đo này; không dùng kết quả #14 làm bằng chứng pin mới.
- Chưa chạy toàn bộ `make test`, build frontend hoặc test Python docreader.
- Rollback 138 có thể fail khi nhiều thread của cùng người dùng không còn thoả unique
  index cũ; upstream cố ý không xoá mapping để ép thành công.
