# #12: Migration tokenizer BM25 trong Fork

## Trạng thái: đạt nghiệm thu #12 trên stack

Đo ngày **2026-11-05** (+07:00) trên stack đang chạy: ParadeDB `pg_search 0.25.11` (`paradedb/paradedb:v0.25.11-pg17`), embedding `Qwen3-VL-Embedding-2B` 1024 chiều, chunk cha/con 4096/384, strategy `auto`, Bộ kiểm tra keyword 30 câu (26 câu có đáp án).

- [x] Integration test PostgreSQL chạy up → down → up sạch, kiểm tokenizer khai báo và cách chỉ mục tách dòng có sẵn sau mỗi bước.
- [x] Nâng image Fork trên stack có dữ liệu: migration chạy khi khởi động (133 → 134), E2E khớp kết quả `icu` của #11.
- [x] Rollback (down) trên stack: E2E trở về mức `chinese_lindera`.
- [x] Kết quả E2E sau migrate được commit làm bản chốt tokenizer: [`issue-12-icu.json`](issue-12-icu.json).

## Bản vá trong Fork

Commit [`d7a09458`](https://github.com/hiennguyen9874/WeKnora/commit/d7a09458) trong `references/WeKnora`. Image đo là `c732b7540c0b` (gồm `d7a09458` và bản vá NFC tiếp theo, không đụng tới BM25).

- `migrations/versioned/000134_embeddings_bm25_icu.up.sql`: xoá rồi dựng lại `embeddings_search_idx` bằng `{"type": "icu"}`. Cột, `key_field` và dạng `text_fields` JSON giữ như `000002`, nên `KeywordsRetrieve` và truy vấn `|||` không đổi (ADR 0002 không bỏ dấu, không cần trường riêng).
- `.down.sql`: dựng lại bằng `{"type": "chinese_lindera"}` như `000002`.
- Cả hai bỏ qua khi không có bảng `embeddings` (deployment không dùng retriever postgres, `app.skip_embedding=true`); đã chạy cả hai trên database không có bảng: chỉ in NOTICE.
- `internal/database/migration_postgres_bm25_tokenizer_test.go`: `TestPostgresBM25TokenizerMigration`, bật bằng `WEKNORA_MIGRATION_TEST_POSTGRES_DSN` như các test migration PostgreSQL hiện có. Chèn một dòng có `Điều 11a … 117/2026/VBHN-NĐ-NHNN`, rồi ở 134, 133, 134 kiểm: `schema_migrations` không dirty, tokenizer trong `text_fields` của chỉ mục, dòng có sẵn được đánh chỉ mục, và `11a` là một token (`icu`) hay bị tách (`chinese_lindera`).

Đỏ → xanh: trước khi có migration, test fail với `expected "icu", actual "chinese_lindera"` ở version 133; sau khi thêm thì pass, cùng `TestMigrationDirectoriesLoad`.

```sh
docker run -d --rm -e POSTGRES_PASSWORD=pg -e POSTGRES_DB=weknora -p 55432:5432 paradedb/paradedb:v0.25.11-pg17
cd references/WeKnora
WEKNORA_MIGRATION_TEST_POSTGRES_DSN='postgres://postgres:pg@localhost:55432/weknora?sslmode=disable' \
  go test ./internal/database -run TestPostgresBM25TokenizerMigration -count=1
```

`TestPostgresMigrationsServeAgentHistory` trong cùng package fail cả khi bỏ `000134` (nó down migration mới nhất và chờ chỉ mục của `000106` biến mất), nên không liên quan tới #12.

## Trên stack

Knowledge base `e2e-20261105-152943` nạp một lần trên image cũ ([`issue-12-load.json`](issue-12-load.json)), chờ tóm tắt xong và số dòng `embeddings` đứng yên ở 692, rồi mọi lần đo dùng lại nó (`--reuse-kb`). Bảng `embeddings` còn 319 dòng của knowledge base khác có từ trước; migration dựng lại chỉ mục trên cả 692 dòng.

| Bước | Thao tác | Kết quả |
| --- | --- | --- |
| 1 | Image cũ `5ce8e8c36d4e-dirty`, version 133 | [`issue-12-before-lindera.json`](issue-12-before-lindera.json) |
| 2 | `./scripts/compose.sh up -d --build --no-deps app` → `c732b7540c0b` | log: `Database migrated from version 133 to 134` (~30 ms); chỉ mục `icu`, 692/692 dòng |
| 3 | E2E sau migrate | `results/issue-12-icu.json` |
| 4 | `migrate … down 1` trong container app | `134/d embeddings_bm25_icu (159ms)`, version 133, chỉ mục `chinese_lindera`, 692/692 dòng |
| 5 | E2E sau rollback | [`issue-12-down-lindera.json`](issue-12-down-lindera.json) |
| 6 | `./scripts/compose.sh restart app` | log: `Database migrated from version 133 to 134` |
| 7 | E2E bản chốt | [`issue-12-icu.json`](issue-12-icu.json), giống hệt bước 3 ở mọi chỉ số |

Ở bước 5, `fork.db_version` trong file kết quả vẫn ghi `134`, vì app đọc version lúc khởi động; database thật là 133 (output `migrate version` và tokenizer `chinese_lindera` cùng file).

| Lần chạy | Keyword R@1 / R@3 / R@5 / R@10 | Keyword MRR | Keyword p50 ms | Hybrid R@1 / R@10 / MRR | Hybrid p50 ms |
| --- | --- | --- | --- | --- | --- |
| Trước nâng cấp (`chinese_lindera`, chỉ mục cũ) | 0,5000 / 0,6923 / 0,7308 / 0,8077 | 0,6032 | 124,0 | 0,6923 / 0,9231 / 0,7619 | 163,4 |
| **Sau migrate (`icu`, bản chốt)** | 0,5385 / 0,6154 / 0,6923 / **0,8462** | **0,6171** | 6,2 | 0,6923 / 0,9231 / 0,7619 | 43,1 |
| Sau rollback (`chinese_lindera`) | 0,5000 / 0,6538 / 0,7308 / 0,8077 | 0,5984 | 7,3 | 0,6923 / 0,9231 / 0,7628 | 47,1 |
| #11 `icu` | 0,5385 / 0,6154 / 0,6923 / 0,8462 | 0,6167 | 6,3 | 0,6923 / 0,9231 / 0,7632 | 44,7 |
| #11 `chinese_lindera` | 0,5000 / 0,6538 / 0,7308 / 0,8077 | 0,5984 | 7,0 | 0,6923 / 0,9231 / 0,7628 | 46,4 |

Vector như nhau ở cả ba lần chạy (R@10 0,9231, MRR 0,7838, trượt q09/q17). Footnote, tiêu đề Điều, breadcrumb, NFC (403/403) và NFC/NFD 90/90 cặp pass ở mọi lần chạy.

### Đối chiếu với #11

- **Sau migrate khớp #11 `icu`:** cùng R@1/R@3/R@5/R@10 keyword và cùng câu trượt (q06, q14, q15, q30). Sai lệch là q21 keyword hạng 9 (so với 10) và q07 hybrid hạng 7 (so với 5), làm MRR lệch dưới 0,002. Nguyên nhân là corpus nạp lại: OCR chia chunk hơi khác (692 dòng, 403 chunk so với 693/404 ở #11), và ngay chế độ vector, không dùng BM25, cũng đổi ở q21 (hạng 10 ở đây, trượt ở #11) và q07 (9 so với 8).
- **Sau rollback khớp #11 `chinese_lindera`:** mọi chỉ số keyword và hybrid trùng tới bốn chữ số.
- **Giữa sau migrate và sau rollback** trên cùng knowledge base, các câu đổi hạng đúng như #11: q21 keyword vào top 10 (hạng 9), q25 lên hạng 1, q12 tụt từ 3 xuống 6, q17 từ 8 lên 6.
- **Trước nâng cấp lệch nhẹ so với sau rollback** dù cùng `chinese_lindera` (q17 hạng 6 so với 8, q23 hạng 3 so với 4, MRR 0,6032 so với 0,5984), và keyword chậm gấp 17 lần (p50 124 ms so với 7,3 ms). Giải thích khả dĩ nhất (chưa kiểm trực tiếp segment): chỉ mục cũ được ghi dần qua mọi lần nạp/xoá knowledge base trước đó và còn giữ dòng đã xoá trong các segment, nên thống kê BM25 (số tài liệu, độ dài trung bình) và số segment phải duyệt khác chỉ mục vừa dựng lại. #11 cũng đo trên chỉ mục dựng lại và cho đúng số của bước 5. Độ trễ của chế độ keyword sau migrate vì thế phần lớn đến từ việc dựng lại, không phải từ `icu`.

## Thay đổi trong Repo triển khai

- `scripts/bm25_tokenizers.py`: `sweep` trả chỉ mục về `icu` (chỉ mục Fork tạo ra) thay vì `chinese_lindera`.
- `eval/bm25-tokenizer.sql`: ghi chú chỉ mục của Fork là `icu`.
- `README.md`: mục Tokenizer BM25 nói về migration `000134`, lệnh rollback và việc app migrate lại khi khởi động.

## Chạy lại

Trên stack đã dựng, `.env` đã điền, Fork chứa `000134`:

```sh
python3 scripts/e2e.py --keep-kb --out results/issue-12-load.json          # nạp; chờ tóm tắt xong
python3 scripts/e2e.py --reuse-kb results/issue-12-load.json --out results/issue-12-icu.json
./scripts/compose.sh exec app sh -c 'migrate -path /app/migrations/versioned -database "postgres://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME?sslmode=disable" down 1'
python3 scripts/e2e.py --reuse-kb results/issue-12-load.json --out results/issue-12-down.json
./scripts/compose.sh restart app                                             # migrate lại lên 134
```

Knowledge base tạm `e2e-20261105-152943` đã được xoá sau khi đo.
