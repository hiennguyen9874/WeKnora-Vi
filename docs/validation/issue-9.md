# #9 — Chuẩn hoá NFC khi nạp và khi truy vấn

## Trạng thái: đạt nghiệm thu #9 trên stack

Lần chạy cuối ngày **2026-11-05, 14:41:28–14:47:16 (+07:00)**, trên Fork nền `5ce8e8c36d4e65f3c6c736557245e2c71e40a716` cộng bản vá khi đó chưa commit. Runtime báo `5ce8e8c36d4e-dirty`; image ID và SHA-256 từng file thay đổi nằm trong [bằng chứng kiểm chứng](issue-9-checks.json), không dùng riêng tag `-dirty` để phân biệt các lần build. Bản vá sau đó được commit và push thành [`f9acc6c0e912629e9ef03fd49df1a483ca120ece`](https://github.com/hiennguyen9874/WeKnora/commit/f9acc6c0e912629e9ef03fd49df1a483ca120ece); fingerprint code khớp kết quả đã đo, không đổi metadata runtime thành hash mới.

- [x] Có fixture TXT lưu thật ở dạng NFD; Bộ kiểm tra keyword giữ nguyên 30 câu đã duyệt, gồm ba câu `form: "nfd"` (`q05`, `q15`, `q16`).
- [x] Mọi chunk của fixture NFD ở dạng NFC: **4/4** (một chunk cha, ba chunk con). Kiểm tra NFC của toàn bộ corpus: **404/404**.
- [x] Mỗi câu hỏi được gửi ở cả NFC và NFD trong cả ba chế độ; **90/90** cặp có cùng toàn bộ danh sách ID top 10 **theo thứ tự**.
- [x] Test tại cửa vào chat pipeline đã đỏ trước khi vá, xanh sau khi vá; gồm NFC, NFD, ASCII, chuỗi rỗng, với bước đầu là viết lại hoặc tìm kiếm.
- [x] Lưu [E2E đầy đủ sau vá](issue-9-e2e.json), các lần tái hiện lỗi và kiểm chứng bổ sung bên dưới.

## Phạm vi bản vá

Trong `references/WeKnora`:

- `internal/application/service/knowledge_process.go`: chuẩn hoá Markdown sau mọi bước viết lại output parser, ngay trước ánh xạ vị trí nguồn và chunking. Đặt sau chuyển bảng HTML để entity được giải mã cũng phải là NFC. Mọi parser hội tụ tại đây; passages cũng được chuẩn hoá trước khi tính offset.
- `internal/application/service/knowledge_create.go`: nội dung nhập tay được chuẩn hoá sau xử lý bảng, trước chunking.
- `internal/application/service/knowledgebase_search.go` và `knowledgebase_search_rerank.go`: chuẩn hoá câu hỏi ở cửa vào của cả hai nhánh hybrid-search, trước embedding, keyword và rerank.
- `internal/application/service/session_knowledge_qa.go`: chuẩn hoá `Query` và giá trị ban đầu của `RewriteQuery` tại `KnowledgeQAByEvent`, trước mọi plugin.
- `internal/sourceloc/remap.go`: nếu chỉ đổi dạng Unicode, dịch offset theo segment chuẩn hoá, không tìm lại văn bản. Giữ nguyên locator trỏ vào file gốc NFD; không dùng offset chunk NFC để mở file đó. Nếu có thêm thay đổi Markdown, compose text nguồn trước khi đối chiếu.
- `internal/application/service/knowledgebase_search_fusion.go`: khi điểm bằng nhau, so tiếp `ChunkID` để thứ tự và phần tử ở biên top-k không phụ thuộc thứ tự duyệt map. Không thay điểm hay cách xếp các kết quả khác điểm. ID đổi sau mỗi lần nạp, nên chỉ so danh sách ID NFC/NFD trong cùng lần chạy.

Dùng `golang.org/x/text/unicode/norm` đã có trong Fork và `cmp` của thư viện chuẩn; không thêm dependency, migration hay feature flag. Tài liệu cũ phải nạp lại để có chunk và index NFC; bản vá không chuyển đổi dữ liệu đã lưu.

Trong Repo triển khai: thêm `fixtures/legal/hien-phap-2013-dieu-8-nfd.txt` và metadata nguồn/SHA-256 trong `eval/documents.json`. Đây là trích Điều 8 Hiến pháp năm 2013, không phải văn bản đầy đủ. `scripts/e2e.py` kiểm tra fixture thật sự là NFD (không đồng thời NFC), không cho kiểm tra NFC pass khi tài liệu không có chunk, và gửi hai dạng Unicode của từng câu hỏi. Recall/MRR vẫn tính trên dạng `form` đã duyệt; không sửa câu hỏi hoặc đáp án.

## Đỏ → xanh và các lỗi phát hiện khi kiểm chứng

1. **Chat pipeline:** `TestKnowledgeQAByEventNormalizesQueryBeforePlugins` thất bại trước vá vì plugin nhận `Điều 5 Khoản 2 quy định gì?`, thay vì literal NFC mong đợi. Sau vá test pass. Seam này quan sát dữ liệu mà plugin đầu tiên nhận được, không chỉ kiểm tra hàm chuẩn hoá độc lập.
2. **Nạp và truy vấn trên app trước vá NFC:** [artifact đỏ](issue-9-red.json) ghi **4/4** chunk fixture không phải NFC; câu probe NFC/NFD có danh sách khác nhau ở cả ba chế độ. Probe chỉ để chẩn đoán, không thêm vào Bộ kiểm tra keyword đã duyệt.
3. **Thứ tự kết quả:** [E2E sau bước chuẩn hoá ban đầu](issue-9-order-red.json) có NFC **404/404** pass nhưng hai cặp keyword `q17`, `q18` fail. [Probe gửi lại cùng một câu NFC](issue-9-order-probe.json) xác nhận các hit bằng điểm đổi thứ tự, kể cả thay phần tử thứ 10, dù không đổi Unicode. Đã thêm tie-breaker, không nới phép so sánh thành tập hợp hay chỉ so đáp án. Sau vá, cả hai câu được gửi lại năm lần trên chính KB cũ và luôn cho cùng danh sách; kết quả nằm trong `order_probes_after_fix` của [bằng chứng kiểm chứng](issue-9-checks.json).
4. **Vị trí trích dẫn:** đổi NFD sang NFC làm số rune thay đổi. Test nguồn ban đầu bắt được mất locator do dấu tổ hợp bị bỏ khi đối chiếu. Kiểm tra tiếp trên fixture phát hiện cách đối chiếu văn bản vẫn bỏ locator của đoạn đầu khi `Điều 8.` đứng trước `1. ...`. Đã tái hiện đỏ với phiên bản đánh số của `TestBuildSourceIndexPreservesOriginalLocationsAfterNFC`, rồi chuyển trường hợp chỉ đổi NFC sang dịch offset trực tiếp. Test xanh; trên app cuối, **4/4** chunk có locator, mọi quote khớp đoạn tương ứng trong file NFD gốc sau chuẩn hoá để so sánh. `citation_red`, `fixture_final_probe` và `fixture_chunks` trong [bằng chứng kiểm chứng](issue-9-checks.json) giữ cả dữ liệu lỗi và dữ liệu sau vá.

Log đỏ/xanh, fingerprint code, kiểm tra locator và cleanup đều lưu trong `issue-9-checks.json`.

## Kết quả E2E cuối

Tokenizer **`chinese_lindera`**, embedding **`Qwen3-VL-Embedding-2B`**, **1024** chiều, chunk cha/con **4096/384**, strategy **`auto`**. Ba PDF qua gateway OCR, TXT NFD qua parser văn bản; cả bốn tài liệu tới `finalizing` (tìm kiếm được, tóm tắt/graph có thể vẫn chạy nền).

| Kiểm tra | Kết quả |
| --- | --- |
| Footnote | PASS, 6/6 |
| Tiêu đề Điều | PASS, 28/28 |
| Breadcrumb | PASS, 5/5 |
| NFC | PASS, 404/404 chunk |
| Danh sách NFC/NFD | PASS, 90/90 cặp, 30 câu × 3 chế độ |
| Locator của fixture | PASS, 4/4 chunk, offset vẫn trỏ về file NFD |

| Chế độ | Recall@1 | Recall@10 | MRR |
| --- | --- | --- | --- |
| Keyword | 0,5000 | 0,7692 | 0,5968 |
| Vector | 0,7308 | 0,9231 | 0,7838 |
| Hybrid | 0,6923 | 0,9231 | 0,7641 |

Đây là kiểm tra tính tương đương Unicode, không phải chọn tokenizer hay nghiệm thu chất lượng câu trả lời. Hybrid vẫn trượt `q09` và `q17`; keyword còn sáu câu trượt như file kết quả ghi rõ. Corpus có thêm TXT và OCR có thể đổi cách chia chunk giữa các lần nạp, nên không quy thay đổi điểm so với baseline ba PDF cho riêng NFC.

## Chạy lại

Trên stack đã cấu hình `.env`, model và gateway:

```sh
(cd references/WeKnora && go test ./internal/application/service \
  -run '^Test(KnowledgeQAByEventNormalizesQueryBeforePlugins|BuildSourceIndexPreservesOriginalLocationsAfterNFC)$' -count=1)
./scripts/compose.sh build app
./scripts/compose.sh up -d --no-deps --force-recreate app
python3 scripts/e2e.py --out results/issue-9-rerun.json
python3 - <<'PY'
import json
from pathlib import Path
r = json.loads(Path('results/issue-9-rerun.json').read_text())
assert all(c['pass'] for c in r['chunk_checks'].values())
assert r['unicode_equivalence']['pass']
assert r['unicode_equivalence']['checked'] == 90
PY
```

Script vẫn thoát 0 khi chunk hoặc phép so NFC/NFD fail để ghi được baseline; phải kiểm tra nội dung JSON như trên, không dùng riêng exit code làm bằng chứng nghiệm thu.

Lần build kiểm chứng bị kẹt khi tải crate `anydoc 0.2.4` từ mirror `rsproxy.cn`. Đã dừng build đó và dùng Dockerfile/Compose override tạm **ngoài checkout**, đổi riêng URL tải sang fallback `static.crates.io` đã có trong script. Vẫn cùng crate được pin, `WITH_ANYDOC=1`; không đổi file build, dependency hay cấu hình deployment trong repo. Lệnh builder tạm và image ID cuối được ghi trong `issue-9-checks.json`.

## Các kiểm tra khác và giới hạn

- `go test ./internal/application/service ./internal/application/service/chat_pipeline ./internal/sourceloc ./internal/infrastructure/chunker -count=1` thất bại ở test có sẵn `TestUpdateMCPService_AppliesNonScalarUpdateWithoutName`: không resolve được `example.com` cho SSRF validation. Đã chạy lại riêng test, và dùng Go overlay của các file Fork chưa sửa; cả hai cùng thất bại vì DNS. Không sửa test hoặc tắt SSRF để làm xanh.
- Chạy lại bốn package với `-skip '^TestUpdateMCPService_AppliesNonScalarUpdateWithoutName$'`: tất cả pass. Log cuối có trong artifact kiểm chứng. `python3 -m py_compile scripts/e2e.py` và `git diff --check` ở cả hai repo pass.
- E2E phủ ba PDF và TXT NFD qua hai đường parser đang dùng; không phải nghiệm thu riêng từng format/parser khác. Không chấm câu trả lời LLM hoặc thay đổi tokenizer.
- Các lần E2E dùng `--keep-kb` để kiểm tra locator/thứ tự rồi mới dọn. Đã xoá cả năm KB tạm của #9, xác minh GET trả **404**, không xoá KB có sẵn hay volume. `run.kb_kept: true` trong file E2E mô tả lúc script kết thúc, không phải trạng thái sau cleanup; thời điểm dọn nằm trong `issue-9-checks.json`. Cả sáu service healthy sau kiểm chứng.
