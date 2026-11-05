# #11 — Thí nghiệm chọn tokenizer BM25

## Kết quả: chọn `icu` (không bỏ dấu)

Đo ngày **2026-11-05**: nạp lúc 15:07–15:12, sweep dùng cho bảng lúc 15:18–15:19 (+07:00), trên stack đang chạy: app `5ce8e8c36d4e-dirty` (mã NFC của #9), ParadeDB `pg_search 0.25.11` (`paradedb/paradedb:v0.25.11-pg17`), embedding `Qwen3-VL-Embedding-2B` 1024 chiều, chunk cha/con 4096/384, strategy `auto`. Bộ kiểm tra keyword gồm 30 câu đã duyệt (26 câu có đáp án).

- [x] SQL thí nghiệm [`eval/bm25-tokenizer.sql`](../../eval/bm25-tokenizer.sql) dựng lại chỉ mục cho từng ứng viên; chạy với `{"type": "chinese_lindera"}` thì trả về đúng chỉ mục gốc. Sweep kết thúc bằng bước trả về đó, và chỉ mục hiện tại là `chinese_lindera`.
- [x] Tokenizer và bộ lọc khả dụng được kiểm tra trên chính image (bên dưới). Bỏ dấu dùng được qua `ascii_folding`.
- [x] Có bảng recall@k, MRR và độ trễ cho chế độ keyword và hybrid, cùng file E2E cho từng ứng viên.
- [x] Có ví dụ token hoá câu tiếng Việt có dấu với từng ứng viên.
- [x] Chọn `icu` và ghi lý do bên dưới. ADR 0002 đã ghi tên tokenizer và đổi status sang `accepted`.

Chỉ mục trong Fork **chưa** đổi tokenizer. Việc đó thuộc #12 (migration có rollback).

## Đã kiểm tra trên ParadeDB của image

Mọi kiểm tra dưới đây chạy trên postgres của stack, không dựa vào docs (docs `paradedb/main` mới hơn image):

- `paradedb.tokenizers()` liệt kê: `default, keyword, raw, literal_normalized, white_space, regex_tokenizer, chinese_compatible, source_code, ngram, edge_ngram, chinese_lindera, japanese_lindera, korean_lindera, icu, jieba, lindera, unicode_words` (cùng các bản `*_deprecated`).
- `pdb.*` dạng cast (`content::pdb.icu('ascii_folding=true')`) có trong image và báo lỗi khi gặp tuỳ chọn lạ. Các tuỳ chọn được chấp nhận là `alias, alpha_num_only, ascii_folding, b, columnar, fieldnorms, k1, lowercase, normalizer, remove_long, remove_short, stemmer, stopwords, stopwords_language, trim`.
- Chỉ mục hiện tại khai báo bằng `text_fields` JSON (`000002_embeddings`). Dạng này **không báo lỗi khoá lạ**: `{"type": "chinese_lindera", "bogus_filter": true}` vẫn tạo được chỉ mục. Vì vậy script kiểm tra tác dụng của từng bộ lọc bằng `paradedb.tokenize` (`Điều BHXH` → có `bhxh` khi lowercase, có `dieu` khi bỏ dấu) trước khi dựng chỉ mục. Sau khi dựng, script đếm số chunk chứa từng token ngay trên chỉ mục thật.
- `ascii_folding` bỏ cả dấu thanh lẫn `đ` → `d` (`điều` → `dieu`, `nđ` → `nd`). Query `|||` dùng tokenizer của trường, nên bỏ dấu trên cùng trường `content` không cần thêm trường hay sửa câu truy vấn trong Fork. Đã thử trên bảng tạm: query `dieu` khớp `Điều`.
- Thí nghiệm giữ dạng `text_fields` JSON và chỉ đổi tokenizer của `content`; các cột khác, `key_field` và mặc định của chúng giữ nguyên như chỉ mục gốc.
- **`chinese_lindera` dạng JSON (đang dùng) sinh token khoảng trắng `" "`**. Trên chỉ mục thật, 687/693 chunk chứa token này, và câu hỏi nhiều từ cũng sinh ra nó. Ngoài ra dấu câu (`.`, `/`, `-`, `:`) cũng thành token riêng. `pdb.lindera(chinese)` mới thì bỏ khoảng trắng; dạng JSON cũ thì không.

## Bảng so sánh

Số liệu lấy từ [`issue-11-tokenizers.json`](issue-11-tokenizers.json). 26 câu có đáp án, nên mỗi câu tương ứng 0,0385 recall. Độ trễ là thời gian request HTTP `hybrid-search` (p50/p95 trên 30 câu), đo từ máy chạy stack.

| Ứng viên | Keyword R@1 / R@3 / R@5 / R@10 | Keyword MRR | Keyword p50 / p95 ms | Hybrid R@1 / R@3 / R@5 / R@10 | Hybrid MRR | Hybrid p50 / p95 ms |
| --- | --- | --- | --- | --- | --- | --- |
| `chinese_lindera` (hiện tại) | 0,5000 / 0,6538 / 0,7308 / 0,8077 | 0,5984 | 7,0 / 11,1 | 0,6923 / 0,8462 / 0,8462 / 0,9231 | 0,7628 | 46,4 / 55,3 |
| `chinese_lindera` + bỏ dấu | 0,5769 / 0,6923 / 0,7692 / 0,7692 | **0,6519** | 7,1 / 8,5 | 0,6923 / 0,8462 / 0,8462 / 0,9231 | 0,7676 | 45,9 / 54,5 |
| **`icu`** | 0,5385 / 0,6154 / 0,6923 / **0,8462** | 0,6167 | 6,3 / 8,5 | 0,6923 / 0,8462 / 0,8846 / 0,9231 | 0,7632 | 44,7 / 53,7 |
| `icu` + bỏ dấu | 0,5769 / 0,6923 / 0,7692 / 0,7692 | 0,6455 | 6,2 / 7,5 | 0,6923 / 0,8462 / 0,8846 / 0,9231 | **0,7696** | 43,5 / 47,8 |
| `whitespace` + lowercase | 0,5385 / 0,6538 / 0,6923 / 0,8077 | 0,6160 | 5,8 / 7,6 | 0,6923 / 0,8846 / 0,8846 / 0,9231 | 0,7676 | 43,0 / 51,9 |
| `whitespace` + lowercase + bỏ dấu | 0,5385 / 0,6154 / 0,7308 / 0,7692 | 0,6103 | 5,7 / 7,3 | 0,6923 / 0,8462 / 0,8846 / 0,9231 | 0,7684 | 43,2 / 47,6 |

Vector không dùng chỉ mục BM25: R@10 0,8846, MRR 0,7804, trượt q09/q17/q21, như nhau ở cả sáu lần chạy. NFC/NFD 90/90 cặp pass ở mọi ứng viên. Footnote, tiêu đề Điều, breadcrumb và NFC pass.

Những câu đổi hạng giữa các ứng viên (`null` = trượt top 10), theo thứ tự cột như bảng trên:

| Câu | Nhóm | Keyword | Hybrid |
| --- | --- | --- | --- |
| q06 `dieu kien cap giay phep san xuat vang mieng` | không dấu | null / 1 / null / 1 / null / 1 | 3 / 2 / 3 / 2 / 3 / 2 |
| q09 lấy mẫu giấy cuộn | bảng | 10 / null / 10 / null / 10 / null | không đổi |
| q12 Điều 11 khoản 1 | điều khoản | 3 / 1 / 6 / 4 / 6 / 4 | không đổi |
| q14 `vang nguyen lieu la gi?` | không dấu | không đổi | 2 / 1 / 2 / 1 / 2 / 1 |
| q17 dấu hợp quy viết tắt | chữ viết tắt | 8 / null / 6 / null / 2 / null | không đổi |
| q21 Điều 2, 136/2026/VBHN-TT-BCT | ngày tháng | null / null / 10 / null / null / null | 6 / 8 / 7 / 7 / 8 / 9 |
| q25 chú thích 16 | footnote | 2 / 2 / 1 / 1 / 3 / 5 | 1 / 1 / 1 / 1 / 1 / 2 |

Các câu q07, q22, q23 chỉ lệch 1–2 hạng.

## Ví dụ token hoá

Lấy từ [`issue-11-tokenize.json`](issue-11-tokenize.json), đúng cấu hình JSON của từng chỉ mục, câu `Điều 11a khoản 1: điều kiện cấp Giấy phép sản xuất vàng miếng theo 117/2026/VBHN-NĐ-NHNN.` (`␣` là token khoảng trắng):

| Ứng viên | Token |
| --- | --- |
| `chinese_lindera` | `điều ␣ 11 a ␣ khoản ␣ 1 : ␣ điều ␣ kiện ␣ cấp ␣ giấy ␣ phép ␣ sản ␣ xuất ␣ vàng ␣ miếng ␣ theo ␣ 117 / 2026 / vbhn - nđ - nhnn .` |
| `chinese_lindera` + bỏ dấu | `dieu ␣ 11 a ␣ khoan ␣ 1 : ␣ dieu ␣ kien ␣ cap ␣ giay ␣ phep ␣ san ␣ xuat ␣ vang ␣ mieng ␣ theo ␣ 117 / 2026 / vbhn - nd - nhnn .` |
| `icu` | `điều 11a khoản 1 điều kiện cấp giấy phép sản xuất vàng miếng theo 117 2026 vbhn nđ nhnn` |
| `icu` + bỏ dấu | `dieu 11a khoan 1 dieu kien cap giay phep san xuat vang mieng theo 117 2026 vbhn nd nhnn` |
| `whitespace` + lowercase | `điều 11a khoản 1: điều kiện cấp giấy phép sản xuất vàng miếng theo 117/2026/vbhn-nđ-nhnn.` |
| `whitespace` + lowercase + bỏ dấu | `dieu 11a khoan 1: dieu kien cap giay phep san xuat vang mieng theo 117/2026/vbhn-nd-nhnn.` |

Cả sáu ứng viên tách theo âm tiết, không ứng viên nào ghép từ tiếng Việt (`giấy phép` vẫn là hai token). `icu` giữ `11a` thành một token và bỏ dấu câu; `chinese_lindera` tách `11` và `a`; `whitespace` dính dấu câu vào token (`1:`, `miếng.`, cả số hiệu văn bản thành một token).

## Lý do chọn `icu`

1. **Keyword tốt nhất trong nhóm giữ dấu.** So với `chinese_lindera`: R@10 0,8462 so với 0,8077 (thêm q21), R@1 0,5385 so với 0,5000, MRR 0,6167 so với 0,5984. Nó cũng có R@10 keyword cao nhất trong cả sáu ứng viên.
2. **Hybrid không kém.** R@10 0,9231 như mọi ứng viên, R@5 0,8846 so với 0,8462, MRR 0,7632 so với 0,7628. Cả sáu ứng viên chênh nhau chưa tới 0,007 MRR hybrid, tức là chưa tới một bậc hạng trên một câu.
3. **Bỏ token rác.** `icu` không sinh token khoảng trắng hay dấu câu (`chinese_lindera` có `" "` trong 687/693 chunk) và không dùng từ điển CC-CEDICT tiếng Trung. Nó tách số hiệu `117/2026/VBHN-NĐ-NHNN` thành các phần tìm riêng được, trong khi `whitespace` giữ cả chuỗi lẫn dấu câu dính vào.
4. **Không bỏ dấu.** Bỏ dấu giúp câu không dấu ở keyword (q06 lên hạng 1), nhưng làm trượt q09 và q17 và hạ R@10 keyword xuống 0,7692 ở cả ba tokenizer. Nguyên nhân là các âm tiết khác dấu bị gộp làm một (`dấu`/`dầu`/`đầu`). Câu không dấu đã được vector và hybrid xử lý (q06 hạng 3, q14 hạng 2 trong hybrid với `icu`), đúng như user story 14 của #1. Lợi ích hybrid của bỏ dấu chỉ là +0,0064 MRR.
5. **Độ trễ không là yếu tố quyết định.** Keyword p50 nằm trong khoảng 5,7–7,1 ms, hybrid trong khoảng 43–46 ms, chênh lệch nằm trong mức dao động giữa các lần chạy.

Giới hạn: khoảng cách giữa `icu` và `chinese_lindera` ở keyword chỉ là một câu ở R@10 (q21 ở đúng hạng 10). Có câu đi ngược chiều: q12 tụt từ hạng 3 xuống 6, q17 và q25 thì lên hạng. Bộ có 26 câu nên chưa đủ để coi đây là khác biệt có ý nghĩa thống kê. `icu` thắng ở số đo nhưng sát nút; lý do 3 (bỏ token khoảng trắng/dấu câu) là điểm phân định.

### Không làm: trường bỏ dấu riêng

Thêm trường bỏ dấu song song (giữ cả `content` có dấu) cần sửa Fork:

- migration chuyển chỉ mục sang dạng `pdb.*` với `alias`, hoặc khai báo thêm trường;
- `KeywordsRetrieve` trong `internal/application/repository/retriever/postgres/repository.go` phải truy vấn cả hai trường (`content ||| ? OR content::pdb.alias('content_fold') ||| ?`) và xác định lại điểm `paradedb.score`;
- test của truy vấn và kiểm tra lại các trường filter khi đổi sang cú pháp mới.

Ước lượng: khoảng một ngày công cho code, test và migration, chưa tính E2E. Theo yêu cầu của issue, việc này chỉ được báo, chưa làm. Số đo trên không cho thấy cần: bỏ dấu thay trường không giúp hybrid, và chế độ keyword mất câu có dấu.

## Lần chạy bị loại

Lần sweep đầu (`issue-11-tokenizers-confounded.json`) bị nhiễu: tóm tắt chạy nền của `136-2026-vbhn-tt-bct.pdf` thêm một chunk summary lúc 15:13:53, giữa lần đo `icu-fold`. Từ `icu-fold` trở đi, vector R@10 giảm từ 0,9231 xuống 0,8846 (q21). Script nay kiểm tra số dòng `embeddings` trước và sau mỗi ứng viên, và dừng nếu số dòng thay đổi. Lần sweep dùng cho bảng trên chạy khi mọi tài liệu đã xong tóm tắt, và cả sáu ứng viên cùng 693 dòng. Điểm keyword của hai lần chạy giống hệt nhau.

## Artifact

| File | Nội dung |
| --- | --- |
| [`issue-11-load.json`](issue-11-load.json) | E2E nạp tài liệu (`--keep-kb`, chỉ mục `chinese_lindera`), knowledge base dùng chung cho sweep |
| `issue-11-<ứng viên>.json` | E2E đầy đủ của từng ứng viên trên cùng knowledge base: `chinese_lindera`, `chinese_lindera-fold`, `icu`, `icu-fold`, `whitespace`, `whitespace-fold` |
| [`issue-11-tokenizers.json`](issue-11-tokenizers.json) | Tổng hợp: cấu hình, số dòng chỉ mục, số chunk chứa token dò, điểm và độ trễ theo chế độ |
| [`issue-11-tokenize.json`](issue-11-tokenize.json) | Danh sách tokenizer của image, kiểm tra bộ lọc, ví dụ token hoá |
| [`issue-11-sweep.log`](issue-11-sweep.log) | Log của sweep dùng cho bảng |
| [`issue-11-tokenizers-confounded.json`](issue-11-tokenizers-confounded.json) | Tổng hợp của lần chạy bị loại |

Knowledge base tạm `e2e-20261105-150711` đã được xoá sau khi đo.

## Chạy lại

Trên stack đã dựng, `.env` đã điền:

```sh
python3 scripts/bm25_tokenizers.py tokenize                       # results/bm25-tokenize.json
python3 scripts/e2e.py --keep-kb --out results/bm25-load.json     # nạp một lần
# chờ mọi tài liệu xong tóm tắt (summary_status completed), rồi:
python3 scripts/bm25_tokenizers.py sweep --reuse-kb results/bm25-load.json
# results/bm25-<ứng viên>.json, results/bm25-tokenizers.json; chỉ mục được trả về chinese_lindera
```

Dựng lại chỉ mục cho một ứng viên, hoặc trả về chỉ mục gốc:

```sh
python3 scripts/bm25_tokenizers.py apply icu
python3 scripts/bm25_tokenizers.py apply chinese_lindera
```

`apply` khoá bảng `embeddings` trong lúc dựng lại; với 693 dòng, cả lệnh (dựng lại và kiểm tra) mất khoảng 2 giây. Xoá knowledge base `e2e-*` trên UI hoặc qua API sau khi đo.
