# #14: Đồng bộ Fork với upstream WeKnora 0.9.0

## Trạng thái: đạt nghiệm thu #14 trên stack

Đo ngày **2026-11-05** (+07:00) trên stack đang chạy, database có dữ liệu từ trước: ParadeDB `pg_search 0.25.11` (`paradedb/paradedb:v0.25.11-pg17`), embedding `Qwen3-VL-Embedding-2B` 1024 chiều, LLM `qwen3.8-27b`, chunk cha/con 4096/384, tokenizer BM25 `icu`, Bộ kiểm tra keyword 30 câu, 4 tài liệu. Image `app`, `docreader`, `frontend`: `f7a167385969`.

- [x] Fork merge `upstream/main`, không force-push; 8 commit tiếng Việt còn nguyên.
- [x] Không trùng số migration; database đang chạy lên 137 mà không bỏ sót `000134_tenant_default_settings` của upstream.
- [x] Ba image dựng từ commit Fork mới, sáu service healthy.
- [x] E2E: mọi kiểm tra chunk và NFC/NFD pass; hybrid bằng lượt đo trên pin cũ `c732b754`.
- [x] `config/prompt_templates/` đồng bộ lại; ví dụ `default_rewrite` tiếng Việt giữ nguyên.

## Commit trong Fork

| Commit | Nội dung |
| --- | --- |
| [`b664d737`](https://github.com/hiennguyen9874/WeKnora/commit/b664d737f) | Merge 253 commit của `upstream/main` (0.9.0) vào `main` (`c732b754`). Một xung đột ở `knowledgebase_search_fusion.go`: upstream #4869 sửa giống Fork (xếp hạng hoà điểm theo `ChunkID`), giữ code upstream kèm comment của Fork. |
| [`c134a1c5`](https://github.com/hiennguyen9874/WeKnora/commit/c134a1c5b) | Đổi `000134_embeddings_bm25_icu` thành `000137_embeddings_bm25_icu`; upstream đã dùng `000134` (`tenant_default_settings`), `000135`, `000136`. golang-migrate từ chối hai migration cùng số, app không khởi động được. |
| [`f7a16738`](https://github.com/hiennguyen9874/WeKnora/commit/f7a167385) | Cherry-pick PR upstream [#4908](https://github.com/Tencent/WeKnora/pull/4908) (chưa merge) sửa issue upstream [#4899](https://github.com/Tencent/WeKnora/issues/4899). |

### Lỗi keyword search của upstream 0.9.0 (#4899)

Upstream #4096 thêm điều kiện loại câu hỏi sinh tự động cho knowledge base tắt `question_generation_config` (mặc định của setup). Điều kiện có so sánh cột với cột (`source_id <> chunk_id`, `substr(source_id, …) = chunk_id || '-'`). ParadeDB không lập được kế hoạch cho `ORDER BY paradedb.score(id)` khi filter có so sánh cột với cột: mọi truy vấn keyword trả HTTP 500 `Unsupported query shape`; hybrid trong chat âm thầm chỉ còn vector.

Đỏ → xanh:

- E2E trên `c134a1c5b18e`: kiểm tra chunk pass, rồi `hybrid-search` keyword trả `HTTP 500 … Unsupported query shape (SQLSTATE XX000)`, log app `[Postgres] Keywords retrieval failed`.
- Tái hiện bằng psql trên bảng `embeddings` thật: điều kiện gốc lỗi; chỉ `source_type = 0` thì chạy; De Morgan, `COALESCE`, `CASE` vẫn lỗi; `starts_with(source_id, chunk_id || '-')` chạy.
- `TestGeneratedQuestionRowPredicateParadeDBAvoidsColumnComparison` (`internal/types`): trước cherry-pick không build (`undefined: GeneratedQuestionRowPredicateParadeDB`), sau cherry-pick pass.

`starts_with(source_id, chunk_id || '-')` đã bao hàm `source_id <> chunk_id`, nên tập dòng bị loại không đổi. Bỏ commit này khi upstream merge #4908.

## Database đang chạy

`schema_migrations` chỉ lưu một version. Database ở `134` (BM25 `icu` cũ của Fork) sẽ khiến app bỏ qua `000134_tenant_default_settings` của upstream. Đã làm:

1. Sao lưu `pg_dump -Fc` (ngoài repo, `~/weknora-backups/pre-upstream-sync-20261105-160952.dump`, 3,8 MB).
2. Dừng app, `UPDATE schema_migrations SET version=133 WHERE version=134 AND NOT dirty;`
3. Khởi động image mới. Log: `Current migration version: 133, dirty: false` → `Database migrated from version 133 to 137`. Sau đó `137|f`, có cột `tenants.default_settings`, `embeddings_search_idx` vẫn dùng `{"type": "icu"}`.

`000134_tenant_default_settings` dùng `ADD COLUMN IF NOT EXISTS`; `000137` xoá rồi dựng lại chỉ mục, cho cùng kết quả.

## Test

- `go build ./...`, `go vet` các package đụng tới: pass.
- `TestPostgresBM25TokenizerMigration` (up → 137 → down 136 → up, trên ParadeDB trống `v0.25.11-pg17`) và `TestMigrationDirectoriesLoad`: pass.
- `go test` các package service, chunker, docparser, sourceloc, types, database, retriever/postgres: pass trừ các test cần DNS, fail cả trên `upstream/main` thuần: `TestUpdateMCPService_AppliesNonScalarUpdateWithoutName` (đã biết), `TestNewOSSClient/custom_endpoint` (phân giải `example.com`), `TestDataSourceReplacementCommitsBeforeEnqueueAndCleanup` (`invalid URL`, kiểm tra SSRF cần DNS).

## E2E

Nạp mới (không `--reuse-kb`) trên `f7a167385969`: [`issue-14-e2e.json`](issue-14-e2e.json). Footnotes 0/6, tiêu đề Điều 0/28, breadcrumb 0/5, NFC 0/404 lỗi, NFC/NFD 0/90 lỗi.

So với [`issue-12-icu.json`](issue-12-icu.json) (pin cũ `c732b7540c0b`, cùng tokenizer, tài liệu, câu hỏi):

| Chế độ | R@1 | R@3 | R@5 | R@10 | MRR | Trượt |
| --- | --- | --- | --- | --- | --- | --- |
| keyword cũ | 0,54 | 0,62 | 0,69 | 0,85 | 0,62 | 4 |
| keyword mới | 0,54 | 0,62 | 0,69 | 0,81 | 0,61 | 5 (+`q21`) |
| vector cũ | 0,73 | 0,85 | 0,85 | 0,92 | 0,78 | 2 |
| vector mới | 0,73 | 0,85 | 0,85 | 0,88 | 0,78 | 3 (+`q21`) |
| hybrid cũ | 0,69 | 0,85 | 0,85 | 0,92 | 0,76 | 2 |
| hybrid mới | 0,69 | 0,85 | 0,88 | 0,92 | 0,76 | 2 |

`q21` (hiệu lực, Điều 2 VBHN 136/2026) ở lượt cũ nằm hạng 9 keyword; lượt mới cùng các kết quả đầu, điểm gần như bằng nhau, đáp án rơi ra ngoài top 10 ở cả keyword và vector (hai nhánh độc lập), hybrid vẫn tìm thấy. Lượt cũ dùng lại knowledge base nạp từ `issue-12-load.json`, lượt mới nạp lại qua OCR, nên chênh này nằm trong dao động giữa các lần nạp (`validation.md`), không quy cho upstream.

Đã xoá ba knowledge base tạm `e2e-20261105-162339`, `e2e-20261105-162959`, `e2e-20261105-163901` (API trả 404). Lượt `162959` bị loại vì app được thay image giữa lúc chạy.

## Giới hạn

- Chưa kiểm tra tay câu trả lời trong Web UI (để cho #13).
- Không chạy toàn bộ `make test`; chỉ các package nêu trên.
- Tính năng mới của upstream 0.9.0 (sandbox, credential vault, assistant, …) không được kiểm chứng.

## Chạy lại

```sh
git -C references/WeKnora fetch upstream
git -C references/WeKnora log --oneline f7a167385..upstream/main   # commit upstream mới
./scripts/compose.sh up -d --build --no-deps app docreader frontend
python3 scripts/e2e.py --out results/<tên>.json
```
