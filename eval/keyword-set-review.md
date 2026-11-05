# Duyệt Bộ kiểm tra keyword — issue #4, spec #1

**Trạng thái: đã được người dùng duyệt và đưa vào sử dụng.**
[`keyword-set.json`](keyword-set.json) có 30 câu, 26 câu có đáp án và 4 câu không
có đáp án. Người dùng đã xác nhận toàn bộ bộ câu (gồm seed và q07 sửa lại);
[xác nhận duyệt được ghi trong issue #4](https://github.com/hiennguyen9874/WeKnora-Vi/issues/4#issuecomment-6649594799).
SHA-256 của bộ đã duyệt: `cda62006e513fb8d892f11a576d5f21308a57ed56e63cf490e6d2644d4bfa2a9`.
File đề xuất đã được chuyển thành bộ đang dùng, không giữ bản song song.
Baseline đầy đủ đã chạy qua script E2E và được lưu tại `results/baseline.json`.

## Phạm vi đã duyệt

- Đọc `query`, `expected`, `doc`, `form` và `tags` trong JSON; dùng bảng dưới để
  kiểm tra đáp án và vị trí nguồn. Nguồn và SHA-256 của PDF nằm trong
  [`documents.json`](documents.json). Đây là câu hỏi trên tài liệu mẫu, không phải
  khẳng định quy định pháp luật hiện hành.
- `expected` là đoạn nhận diện chunk đúng, **không phải đáp án do LLM sinh**.
  Các câu bảng dùng nhãn hàng duy nhất, không nối nhãn với ô số qua ký tự phân cách
  Markdown. Vì vậy điểm retrieval không chứng minh ô số được OCR đúng; cần đối
  chiếu các giá trị dưới đây khi duyệt. q06 tìm tiêu đề Điều, không chấm toàn bộ
  các điều kiện bên dưới.
- q01–q11 giữ câu seed, trừ q07 được hỏi lại về **khoản sửa đổi** để đoạn mong đợi
  thực sự chứa đáp án; câu cũ hỏi tên Chương nhưng đoạn mong đợi chỉ là chú thích.
  q12 giữ đề xuất của issue #8. q13–q30 là câu mới.
- q04/q16 là cặp NFC/NFD; q14/q15/q30 là ba dạng không dấu/NFD/NFC của cùng câu.
  Đây là chủ ý kiểm tra cách gõ, không phải các ý định độc lập. Tổng recall/MRR
  sẽ tính từng biến thể như một câu, theo script E2E hiện có.
- `form: "nfd"` để script chuyển sang Unicode tổ hợp ngay trước khi gửi; JSON vẫn
  lưu chữ dễ đọc. Không tự bỏ dấu các câu khác.
- BHXH/TNCN không có quy định trả lời trong tài liệu mẫu, nên q27/q28 là ca âm.
  q17/q18 dùng chữ viết tắt thực sự có trong nguồn (QCVN, TCVN, CR), để nhóm
  chữ viết tắt có cả câu tìm được đáp án, không chỉ câu âm.

## Phủ nhóm ca khó

Một câu có thể thuộc nhiều nhóm; chỉ nhóm `nfd` cần `form: "nfd"`.

| Nhóm (`tags`) | Số câu | ID |
| --- | ---: | --- |
| Không dấu (`khong-dau`) | 2 | q06, q14 |
| Unicode tổ hợp (`nfd`) | 3 | q05, q15, q16 |
| Chữ viết tắt (`chu-viet-tat`) | 4 | q17, q18, q27, q28 |
| Điều X khoản Y (`dieu-khoan`) | 4 | q12, q13, q20, q29 |
| Ngày tháng (`ngay-thang`) | 3 | q01, q21, q22 |
| Số tiền (`so-tien`) | 4 | q12, q13, q19, q20 |
| Bảng (`bang`) | 4 | q08, q09, q23, q24 |
| Footnote (`footnote`) | 3 | q07, q25, q26 |
| Không có đáp án (`khong-co-dap-an`) | 4 | q10, q11, q27, q28 |

q19 và q20 viết tiền theo dạng phân nhóm hàng nghìn (`5.000.000 đồng`,
`1.000.000.000.000 đồng`), trong khi nguồn viết `05 triệu đồng` và `1.000 tỷ đồng`.

## Đối chiếu đáp án và nguồn

Ký hiệu tài liệu theo `doc` trong JSON:

- **BCA**: `tt-32-2024-bca` — `fixtures/legal/32-2024-tt-bca.pdf`.
- **Vàng**: `vbhn-117-2026-nd-nhnn` — `fixtures/legal/117-2026-vbhn-nd-nhnn.pdf`.
- **Giấy**: `vbhn-136-2026-tt-bct` — `fixtures/legal/136-2026-vbhn-tt-bct.pdf`.

Trang dưới đây là **số trang in**; với Vàng và Giấy, trang PDF = trang in trừ 1.
BCA có trang PDF trùng trang in. Ba câu BCA đã đối chiếu trực tiếp ảnh scan;
23 đoạn mong đợi còn lại đã đối chiếu text PDF bằng `pdftotext -layout`, mỗi đoạn
xuất hiện đúng một lần trong tài liệu được gắn. Điều này không chứng minh đoạn
nằm trọn trong một chunk sau OCR: baseline ghi nhận các lỗi đó, không sửa
đoạn mong đợi để che lỗi parse/chunk.

| ID | Đáp án để người dùng đối chiếu | Nguồn |
| --- | --- | --- |
| q01 | 24/8/2024 (ngày được điền tay trên scan) | BCA, tr. 7, Điều 4 |
| q02 | Bình chữa cháy các loại; chai chứa khí chữa cháy | BCA, tr. 6, Điều 15 khoản 1 điểm đ được sửa đổi |
| q03 | 15.000 m³ trở lên | BCA, tr. 5, Điều 13 khoản 2 được sửa đổi |
| q04 | Từ 8 Kara, tương đương 33,33% | Vàng, tr. 3, Điều 3 khoản 1 |
| q05 | Vàng dập thành miếng, có đóng chữ/số, ký mã hiệu theo quy định | Vàng, tr. 3, Điều 3 khoản 2 |
| q06 | Điều 11a: Điều kiện cấp Giấy phép sản xuất vàng miếng | Vàng, tr. 6, tiêu đề Điều 11a |
| q07 | Khoản 6 Điều 1 Nghị định 232/2025/NĐ-CP | Vàng, tr. 5, chú thích 15 |
| q08 | Chì (Pb) không lớn hơn 0,003 mg/dm² | Giấy, tr. 9, Bảng 2 hàng 6 |
| q09 | Chọn 2 cuộn, ngẫu nhiên | Giấy, tr. 12, Bảng 6 hàng 6 đến 20 |
| q10 | Không có mức đóng bảo hiểm xã hội trong ba tài liệu mẫu | Không có đáp án |
| q11 | Không có thời hạn sử dụng tối đa của bình chữa cháy trong ba tài liệu mẫu | Không có đáp án (BCA chỉ quy định tem kiểm định, không quy định tuổi thọ bình) |
| q12 | Vốn điều lệ từ 100 tỷ đồng trở lên | Vàng, tr. 6, Điều 11 khoản 1 điểm b |
| q13 | Vốn điều lệ từ 3.000 (ba nghìn) tỷ đồng trở lên | Vàng, tr. 6, Điều 11 khoản 2 điểm a |
| q14 | Vàng dưới dạng khối, thỏi, hạt, miếng và các loại vàng khác | Vàng, tr. 3, Điều 3 khoản 3 |
| q15 | Như q14, câu hỏi gửi ở dạng NFD | Vàng, tr. 3, Điều 3 khoản 3 |
| q16 | Như q04, câu hỏi gửi ở dạng NFD | Vàng, tr. 3, Điều 3 khoản 1 |
| q17 | Dấu CR | Giấy, tr. 10, mục 2.3.2 |
| q18 | Các loại giấy văn phòng phù hợp TCVN 5946:2007 – Giấy loại | Giấy, tr. 8, mục 2.1.1 |
| q19 | Có; từ 05 triệu đồng/ngày/khách hàng phải thanh toán không dùng tiền mặt | Vàng, tr. 5, Điều 4 khoản 10 |
| q20 | Đạt riêng ngưỡng vốn: từ 1.000 tỷ đồng; vẫn phải đáp ứng các điều kiện khác | Vàng, tr. 6, Điều 11a khoản 1 điểm b |
| q21 | 01/01/2017 theo nội dung Điều 2 trong bản hợp nhất | Giấy, tr. 4, Điều 2 (không lấy ngày 01/01/2018 ở lời dẫn tr. 2) |
| q22 | 25/5/2012 | Vàng, tr. 2, đoạn mở đầu về Nghị định 24/2012/NĐ-CP |
| q23 | Độ ẩm không lớn hơn 8,0% | Giấy, tr. 9, Bảng 2 hàng 1 |
| q24 | Cadimi (Cd) không lớn hơn 0,002 mg/dm² | Giấy, tr. 9, Bảng 2 hàng 7 |
| q25 | Khoản 7 Điều 1 Nghị định 232/2025/NĐ-CP | Vàng, tr. 6, chú thích 16 |
| q26 | Điểm 3 khoản 2.1 mục II của Sửa đổi 01:2026 QCVN 09:2015/BCT | Giấy, tr. 9, chú thích 10 |
| q27 | Không có số năm đóng BHXH để hưởng lương hưu trong ba tài liệu mẫu | Không có đáp án |
| q28 | Không có mức giảm trừ gia cảnh thuế TNCN trong ba tài liệu mẫu | Không có đáp án |
| q29 | Thuế xuất khẩu và thuế nhập khẩu, theo quyết định của Thủ tướng Chính phủ | Vàng, tr. 8, Điều 14 khoản 3 |
| q30 | Như q14, câu hỏi gửi ở dạng NFC | Vàng, tr. 3, Điều 3 khoản 3 |

## Kiểm tra bộ câu không gọi dịch vụ

Chạy từ gốc Repo triển khai, cần Python 3 và `pdftotext` (Poppler). Lệnh dùng
validator và cách chuẩn hoá của script E2E; không upload tài liệu, không gọi model,
không thay bộ câu đang dùng. Nguồn scan phải đối chiếu ảnh như bảng trên.

```sh
PYTHONPATH=scripts python3 - <<'PY'
from collections import Counter
from pathlib import Path
import subprocess
import unicodedata
import e2e

e2e.KEYWORD_SET = Path('eval/keyword-set.json')
docs, questions = e2e.load_inputs()
assert [q['id'] for q in questions] == [f'q{i:02}' for i in range(1, 31)]
counts = Counter(t for q in questions for t in q['tags'])
for tag in ('khong-dau', 'nfd', 'chu-viet-tat', 'dieu-khoan', 'ngay-thang',
            'so-tien', 'bang', 'footnote', 'khong-co-dap-an'):
    assert counts[tag] >= 2, (tag, counts[tag])
for q in questions:
    assert ('nfd' in q['tags']) == (q.get('form') == 'nfd'), q['id']
    if 'khong-dau' in q['tags']:
        assert q['query'].isascii(), q['id']
    if q.get('form') == 'nfd':
        assert unicodedata.normalize('NFD', q['query']) != q['query'], q['id']
for doc in docs:
    if 'scan' in doc['kind']:
        continue
    source = e2e.norm(subprocess.check_output(
        ['pdftotext', '-layout', doc['file'], '-'], text=True))
    for q in questions:
        if q.get('doc') == doc['id']:
            for snippet in q['expected']:
                assert source.count(e2e.norm(snippet)) == 1, q['id']
print('PASS: 30 câu, đủ nhóm, đúng dạng Unicode, đoạn nguồn duy nhất.')
PY
```

## Kết quả baseline đầy đủ (#4)

`results/baseline.json`: chạy từ 11:22:44 đến 11:27:38 ngày 05/11/2026 (+07:00),
exit code 0, trên stack baseline riêng. Runtime xác nhận Fork `fd7a2586fd58`,
WeKnora 0.8.3, database version 133, tokenizer `chinese_lindera`, embedding
`Qwen3-VL-Embedding-2B` 1024 chiều; LLM `qwen3.8-27b`.
Cả ba tài liệu đều đạt `finalizing` (tìm kiếm được), và chạy đủ 30 câu × 3 chế độ.

| Chế độ | R@1 | R@3 | R@5 | R@10 | MRR |
| --- | ---: | ---: | ---: | ---: | ---: |
| Keyword | 0,4615 | 0,5385 | 0,5385 | 0,6154 | 0,5110 |
| Vector | 0,6154 | 0,7308 | 0,7692 | 0,7692 | 0,6808 |
| Hybrid | 0,5000 | 0,6923 | 0,7308 | 0,8077 | 0,6087 |

Chunk checks: footnote **fail 6/6**, tiêu đề Điều **fail 1/27**, breadcrumb
**fail 4/5**; NFC **pass 358/358**. Đây là lỗi được ghi nhận ở baseline chưa vá,
không phải lý do loại câu khỏi bộ đã duyệt. Không đánh giá chất lượng câu trả lời LLM.

Đã kiểm tra ID/câu hỏi/form/tags khớp nguyên bộ đã duyệt, đủ 90 kết quả tìm kiếm,
tính lại recall/MRR từ hạng từng câu, và đối chiếu tổng chunk. Knowledge base E2E
đã được xoá sau khi lưu kết quả. Stack triển khai ban đầu giữ nguyên ID container,
image và trạng thái healthy; không thay dữ liệu hay checkout Fork của nó.

## Chạy lại baseline đầy đủ

Dùng stack **riêng**, project `weknora-vi-baseline`, với volume mới, không hạ phiên
bản stack đang có dữ liệu. Các image app/docreader/frontend chưa vá mang tag
`fd7a2586fd58` phải có sẵn (nếu chưa có, build từ một checkout riêng của commit đó).
Không dùng `scripts/compose.sh up` để dựng baseline: wrapper luôn chọn commit
Fork hiện đang checkout, không phải commit baseline.

```sh
WEKNORA_FORK_COMMIT=fd7a2586fd58 APP_PORT=58082 FRONTEND_PORT=127.0.0.1:58083 \
  docker compose -p weknora-vi-baseline -f compose.yaml up -d --no-build --wait
WEKNORA_URL=http://127.0.0.1:58082 COMPOSE_PROJECT_NAME=weknora-vi-baseline \
  python3 scripts/setup.py
WEKNORA_URL=http://127.0.0.1:58082 COMPOSE_PROJECT_NAME=weknora-vi-baseline \
  python3 scripts/e2e.py --out results/baseline.json
```

Cả `WEKNORA_URL` và `COMPOSE_PROJECT_NAME` đều cần thiết: biến đầu chọn API,
biến sau chọn đúng PostgreSQL khi script đọc tokenizer và breadcrumb. Xác nhận
`fork.commit` trong kết quả là `fd7a2586fd58` và tokenizer là `chinese_lindera`.

Cố định model, số chiều, tài liệu, bộ câu và cấu hình chunking khi so sánh với
bản vá/tokenizer khác. Lần chạy đầy đủ dùng cấu hình hiện tại của `setup.py`:
`auto`, `languages: ["vi"]`, cha/con 4096/384, token limit 512. Đây không phải
cấu hình legacy của baseline seed lịch sử. Kết quả `chunker-vi` và `chunker-legal`
cũ chỉ đo 9 câu có đáp án, không được so trực tiếp điểm tổng hợp với bộ 30 câu.
Baseline seed cũ vẫn có trong lịch sử Git tại commit `72f03bd`.

Dừng stack baseline sau khi chạy để trả tài nguyên; không dùng `down -v` cho
stack đang có dữ liệu. Để chạy lại độc lập, dùng tên project và cổng chưa sử dụng.
