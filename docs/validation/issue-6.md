# #6 — Giữ footnote trong request PaddleOCR-VL

## Trạng thái: đạt nghiệm thu #6 trên stack

Lần chạy lại ngày 2026-11-05, sau khi gateway đã có khả năng nhận dạng Footnote, đạt mọi tiêu chí nghiệm thu #6. Không sửa thêm code Fork, gateway, parsing mode, cấu hình chunk hoặc Bộ kiểm tra keyword. Phần bên dưới giữ nguyên bằng chứng lần chạy ban đầu bị chặn để đối chiếu.

## Nghiệm thu sau khi gateway nhận dạng Footnote

- [x] Go test fake server đã đỏ → xanh ở lần vá ban đầu; chạy lại `go test ./internal/infrastructure/docparser -count=1` pass toàn bộ package (3,738 giây).
- [x] Probe trực tiếp trang 1: **13/13** block `footnote` có text trong chế độ `two-stage`; Markdown chứa chú thích mong đợi, không có các mẫu header/số trang được dò.
- [x] Nạp mới ba tài liệu: footnote **6/6**, tiêu đề Điều **27/27**, breadcrumb **5/5**, NFC **400/400** pass. Không thấy mẫu header Công báo/chữ ký hoặc dòng số trang độc lập trong 400 chunk cha/con.
- [x] Ba câu footnote đều tìm thấy trong hybrid top 10: `q07` hạng **6**, `q25` hạng **1**, `q26` hạng **1**.
- [x] Lưu [E2E đầy đủ](issue-6-rerun-e2e.json), [response probe](issue-6-rerun-ocr-probe.json) và [metadata, log, phép dò nhiễu, cleanup](issue-6-rerun.json). Không ghi đè baseline hoặc artifact lần chạy thất bại.

Lần chạy **13:54:47–14:00:02 (+07:00)** dùng tokenizer `chinese_lindera`, embedding `Qwen3-VL-Embedding-2B` 1024 chiều và chunk cha/con 4096/384, strategy `auto` như trước.

| Chế độ | Recall@1 | Recall@10 | MRR |
| --- | --- | --- | --- |
| Keyword | 0,4615 | 0,7308 | 0,5487 |
| Vector | 0,7308 | 0,9231 | 0,7843 |
| Hybrid | 0,7308 | 0,9231 | 0,7897 |

Hybrid vẫn trượt `q09` (bảng) và `q17` (dấu hợp quy); không thuộc ba câu footnote của #6. Không nới đáp án hoặc kiểm tra. Các phép dò nhiễu chỉ phủ mẫu cụ thể của tài liệu mẫu; Go test kiểm tra footer/aside vẫn nằm trong danh sách bỏ qua.

App không rebuild: image vẫn là `weknora-vi/app:45787b40fb17-dirty`, cùng image ID của lần kiểm chứng ban đầu. SHA-256 hai file bản vá khớp artifact cũ và checkout Fork `5ce8e8c36d4e65f3c6c736557245e2c71e40a716`; không đổi metadata runtime thành hash mới. Checkout gateway đang ở `46464bc750443f541524261b14e568a32e061204`, nhưng **chưa xác minh SHA của tiến trình gateway từ xa**. Kết luận về khả năng nhận dạng dựa trên response thật, không suy ra phiên bản deploy từ checkout.

### Chạy lại nghiệm thu

Chạy probe theo hướng dẫn cuối trang, rồi:

```sh
(cd references/WeKnora && go test ./internal/infrastructure/docparser -count=1)
python3 scripts/e2e.py --out results/issue-6-rerun-e2e.json
```

Đọc `chunk_checks.footnotes` (phải pass 6/6), các chunk check còn lại và `questions` → `modes.hybrid.rank` của `q07`, `q25`, `q26` (không null, ≤ 10). Script không thoát lỗi vì chunk check fail, nên không dùng exit code làm bằng chứng nghiệm thu. Lệnh trên tự xoá knowledge base tạm; lần chạy lưu artifact dùng `--keep-kb` để dò nhiễu trước, rồi đã xoá qua API và xác minh GET trả **404** lúc 14:00:12. Không xoá tài nguyên có sẵn.

## Lần chạy ban đầu: đã vá Fork, gateway còn chặn nghiệm thu

Bản vá của [#6](https://github.com/hiennguyen9874/WeKnora-Vi/issues/6), thuộc spec #1, chỉ bỏ `footnote` khỏi `markdownIgnoreLabels`. `header`, `header_image`, `footer`, `footer_image`, `number`, `aside_text` và mọi tham số khác giữ nguyên. Hàm tạo tham số dùng chung cho reader self-hosted và cloud nên cả hai cùng giữ footnote; lần kiểm chứng này chỉ gọi self-hosted `/layout-parsing`.

Kiểm chứng ngày 2026-11-05 trên Fork nền `45787b40fb1701ec2c91f55924198abdac6a1b89` cộng bản vá trong hai file: `internal/infrastructure/docparser/paddleocr_vl_converter.go` và `paddleocr_vl_converter_test.go`. Bản vá sau đó được commit và push thành [`5ce8e8c36d4e65f3c6c736557245e2c71e40a716`](https://github.com/hiennguyen9874/WeKnora/commit/5ce8e8c36d4e65f3c6c736557245e2c71e40a716). SHA-256 của hai file, image ID, log red/green và kết quả kiểm tra bổ sung nằm trong [`issue-6.json`](issue-6.json). App đã build và recreate bằng image `weknora-vi/app:45787b40fb17-dirty`; giữ nguyên metadata của lần chạy trước khi commit. Không thay năm service còn lại, không xoá volume.

- [x] Go test fake server đỏ trước khi vá, xanh sau khi vá; kiểm tra body request không bỏ footnote nhưng vẫn bỏ sáu nhãn nhiễu còn lại, và Markdown trả về giữ nội dung chú thích.
- [ ] Kiểm tra footnote trên stack pass: **0/6**, còn thiếu cả sáu đoạn mong đợi.
- [ ] Câu hỏi footnote tìm thấy bằng hybrid: **0/3** (`q07`, `q25`, `q26` đều trượt top 10).
- [x] Lưu đầy đủ kết quả E2E sau vá và bằng chứng chẩn đoán, không thay baseline.

## Red → green

Trong `references/WeKnora`:

```sh
go test ./internal/infrastructure/docparser -run '^TestPaddleOCRVLReadPreservesFootnotes$' -count=1
# Trước bản vá: exit 1, markdownIgnoreLabels must not discard footnote.
go test ./internal/infrastructure/docparser -count=1
# Sau bản vá: pass toàn bộ package, gồm test mới và các test timeout cũ.
```

Test gọi `PaddleOCRVLReader.Read` qua HTTP fake server, không gọi trực tiếp hàm tạo map tham số. Bản vá production chỉ thay một dòng danh sách nhãn.

## E2E trên stack — lần chạy ban đầu

```sh
./scripts/compose.sh build app
./scripts/compose.sh up -d --no-deps --force-recreate app
python3 scripts/e2e.py --keep-kb --out docs/validation/issue-6-e2e.json
```

Lần chạy 12:21:22–12:26:10 (+07:00) nạp mới cả ba PDF, dùng Bộ kiểm tra keyword 30 câu đã duyệt, tokenizer `chinese_lindera`, embedding `Qwen3-VL-Embedding-2B` 1024 chiều, chunk cha/con 4096/384 và strategy `auto`. Dữ liệu gốc của lần chạy nằm trong [`issue-6-e2e.json`](issue-6-e2e.json).

| Kiểm tra | Kết quả |
| --- | --- |
| Parse/index | Cả ba tài liệu tới `finalizing` |
| Footnote | FAIL, thiếu 6/6 đoạn |
| Tiêu đề Điều | PASS, 27/27 |
| Breadcrumb | PASS, 5/5 |
| NFC | PASS, 352/352 chunk |
| Header/số trang | Không thấy mẫu header Công báo/chữ ký hoặc dòng số trang độc lập trong 352 chunk cha/con |

Phép dò nhiễu dùng NFC, bỏ `**`, giữ xuống dòng; các regex và số chunk từng tài liệu được lưu trong `issue-6.json.chunk_noise_checks`. Đây là kiểm tra các mẫu cụ thể của tài liệu mẫu, không chứng minh mọi loại footer/aside đều vắng mặt. Việc giữ các nhãn footer/aside trong danh sách bỏ qua được kiểm tra bằng Go test.

| Chế độ | Recall@1 | Recall@10 | MRR |
| --- | --- | --- | --- |
| Keyword | 0,5000 | 0,6538 | 0,5356 |
| Vector | 0,6538 | 0,8077 | 0,7019 |
| Hybrid | 0,6154 | 0,8462 | 0,6843 |

Không quy mức tăng so với `results/baseline.json` cho bản vá footnote: Fork hiện tại còn có các bản vá chunker/ngôn ngữ so với Fork baseline. Script E2E không thoát lỗi chỉ vì chunk check fail; phải đọc `chunk_checks` và hạng từng câu, không dùng exit code để tuyên bố nghiệm thu.

Knowledge base tạm được giữ để đọc chunk, rồi đã xoá qua API; GET sau xoá trả 404. `run.kb_kept: true` trong kết quả gốc mô tả thời điểm script kết thúc; thời điểm dọn sau đó nằm trong `issue-6.json.cleanup`. Không xoá knowledge base có sẵn.

## Blocker lịch sử: gateway không nhận dạng nội dung Footnote ở chế độ two-stage

Đã tạo issue [MonkeyOCRv2-B-Parsing-Gateway #19](https://github.com/hiennguyen9874/MonkeyOCRv2-B-Parsing-Gateway/issues/19), liên kết ngược tới WeKnora-Vi #6, để xử lý nhận dạng Footnote và chốt ràng buộc tương đương Upstream.

Tách trang 1 của `117-2026-vbhn-nd-nhnn.pdf` và gọi trực tiếp cùng endpoint `/layout-parsing` với bộ tham số sau vá. Response thực tế được lưu nguyên trong [`issue-6-ocr-probe.json`](issue-6-ocr-probe.json):

- `model_settings.markdown_ignore_labels` đúng sáu nhãn còn lại, **không có `footnote`**: gateway thực sự tôn trọng danh sách client gửi.
- `model_settings.parsing_mode` là `two-stage`.
- Có **13 block `footnote`**, nhưng cả 13 có `block_content: ""`; vì vậy không có nội dung để đưa vào Markdown hay chunk.
- Header Công báo và số trang `2` vẫn có trong kết quả layout để đối chiếu, nhưng không có trong Markdown.

Code gateway trong checkout phù hợp với quan sát này: `src/monkeyocr_gateway/upstream.py:20–25` không bật prompt `Footnote`; `src/monkeyocr_gateway/page_parser.py:87–113` trả chuỗi rỗng cho block không cần inference. Không sửa gateway hoặc đổi parsing mode trong #6, vì yêu cầu chốt chỉ đổi danh sách nhãn của Fork và giữ nguyên các tham số khác.

### Chạy lại probe

Sau khi stack đã có `.env` và tenant parser settings, chạy từ Repo triển khai (response chỉ ghi vào thư mục kết quả bị ignore):

```sh
pdfseparate -f 1 -l 1 fixtures/legal/117-2026-vbhn-nd-nhnn.pdf /tmp/weknora-issue6-page%d.pdf
python3 - <<'PY'
import base64, json, sys, urllib.request
from pathlib import Path
sys.path.insert(0, 'scripts')
from setup import ROOT, connect, load_env
client = connect(load_env(ROOT / '.env'))
endpoint = client.request('GET', '/api/v1/tenants/kv/parser-engine-config')['data']['paddleocr_vl_endpoint']
body = json.loads((ROOT / 'docs/validation/issue-6.json').read_text())['ocr_probe']['request']
body = {k: v for k, v in body.items() if k not in ('method', 'path')}
body['file'] = base64.b64encode(Path('/tmp/weknora-issue6-page1.pdf').read_bytes()).decode()
req = urllib.request.Request(endpoint.rstrip('/') + '/layout-parsing',
    data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=300) as response:
    result = json.load(response)
(ROOT / 'results/issue-6-ocr-probe-rerun.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
PY
```

Ở thời điểm lần chạy ban đầu, cần bật nhận dạng Footnote trong gateway OCR, deploy bản sửa đó rồi nạp lại tài liệu và chạy lại E2E. Chỉ sửa Markdown filtering trong Fork không thể khôi phục text mà gateway chưa nhận dạng. Blocker này đã được giải quyết về hành vi trên stack trong lần nghiệm thu đầu trang; artifact cũ vẫn giữ kết quả thất bại thực tế.
