# #5 — Prompt nhận `Vietnamese`, rewrite dùng ví dụ tiếng Việt

## Kết quả

Đã triển khai phần code/config của [#5](https://github.com/hiennguyen9874/WeKnora-Vi/issues/5), thuộc spec #1. Kiểm chứng trên stack cục bộ ngày 2026-11-05; kết quả có cấu trúc và trích log thực tế nằm trong [`issue-5.json`](issue-5.json).

- Fork nền khi kiểm chứng: `821c91d96dd790916b15cd427ba578d687b2cbea`, cộng bản vá ở `internal/types/context_helpers.go` và `context_helpers_test.go`. Bản vá sau đó được commit và push thành [`45787b40fb1701ec2c91f55924198abdac6a1b89`](https://github.com/hiennguyen9874/WeKnora/commit/45787b40fb1701ec2c91f55924198abdac6a1b89). Image bên dưới được build trước khi commit; giữ nguyên metadata của lần chạy.
- Image app đã build và chạy: `weknora-vi/app:821c91d96dd7-dirty`; image ID được ghi trong JSON. Chỉ recreate app, không thay image của năm service còn lại và không xoá volume.
- `WEKNORA_LANGUAGE=vi-VN`, frontend `DEFAULT_LOCALE=en-US`; mọi request nghiệm thu gửi `Accept-Language: en-US`.
- Overlay được app nạp thật: API prompt templates trả về ví dụ `Xin chào`, không còn chữ Trung trong `default_rewrite.content`.
- API trả tên agent built-in và tên template bằng tiếng Anh. Đã mở Chrome headless với profile tạm, xác nhận trang Agents hiển thị `Quick Answer`, `Smart Reasoning`, `Wiki Questioner`, `Data Analyst`; mở Create Agent → Prompts → Use Template và xác nhận tên template tiếng Anh. Không lưu agent mới từ giao diện. Nội dung DOM quan sát được lưu trong JSON.

## Red → green

Thêm hai ca `vi`/`vi-VN` vào `TestLanguageLocaleName` đang có, cùng `TestVietnamesePromptLanguage` kiểm tra đường context/default/explicit và việc không thêm UI locale. Trước khi sửa hàm ánh xạ, chạy:

```sh
cd references/WeKnora
go test ./internal/types -run 'TestLanguageLocaleName|TestVietnamesePromptLanguage' -count=1
```

Lệnh thoát 1, với lỗi thực tế:

```text
LanguageLocaleName("vi") = "vi", want "Vietnamese"
LanguageLocaleName("vi-VN") = "vi-VN", want "Vietnamese"
LanguageNameFromContext = "vi", want Vietnamese
LanguageNameFromContext = "vi-VN", want Vietnamese
```

Sau bản vá, `go test ./internal/types -count=1` pass; kiểm tra cuối `go test ./internal/config ./internal/types ./internal/middleware -count=1` cũng pass. Các ca ánh xạ locale cũ vẫn được chạy.

## Kiểm tra overlay

Đã parse cả 12 file YAML và so sánh với `references/WeKnora/config/prompt_templates`:

- Cùng danh sách file; 11 file ngoài `rewrite.yaml` giống byte-for-byte.
- Trong `rewrite.yaml`, chỉ `content` của `default_rewrite` khác; metadata, i18n, user prompt và hai template rewrite còn lại giống bản gốc.
- Nội dung rewrite mặc định không có chữ Trung; giữ các placeholder và ví dụ cho `greeting`, `kb_search`, `follow_up`, `image_only`, `doc_only`.
- Compose render thành bind mount read-only tại `/app/config/prompt_templates`.
- Khi stage các file mới, `git diff --cached --check` báo whitespace có sẵn trong bản gốc: dòng trắng có spaces ở `generate_questions.yaml:11` và dòng trắng cuối `intent_prompts.yaml:183`. Giữ nguyên hai bản sao để đáp ứng yêu cầu byte-for-byte; diff check của các file còn lại pass.

Có thể xem lại phần khác biệt mà không cần dịch vụ hay dependency mới:

```sh
diff -rq references/WeKnora/config/prompt_templates config/prompt_templates
# Chỉ rewrite.yaml khác; diff thoát 1 là bình thường.
diff -u references/WeKnora/config/prompt_templates/rewrite.yaml config/prompt_templates/rewrite.yaml
./scripts/compose.sh config --format json  # kiểm tra services.app.volumes; không chia sẻ output chứa secrets
```

## Nghiệm thu API trên stack

### Tài liệu, hội thoại và ảnh

Tạo knowledge base tạm theo `scripts/setup.py:knowledge_base_body`, upload `fixtures/legal/32-2024-tt-bca.pdf` qua API công khai và chờ summary hoàn thành. Summary sinh bằng tiếng Việt, bắt đầu:

> Văn bản là Thông tư của Bộ trưởng Bộ Công an, sửa đổi và bổ sung một số điều của Thông tư số 149/2020/TT-BCA và Thông tư số 08/2018/TT-BCA.

Tạo agent tạm từ cấu hình `builtin-quick-answer`, đặt model `builtin-llm`, rerank `builtin-rerank`, bật image upload với `builtin-vlm`, tắt web search và query expansion để cô lập rewrite. Giữ multi-turn và rewrite bật, chỉ chọn knowledge base tạm. Gửi lần lượt vào **cùng một session**, qua `POST /api/v1/knowledge-chat/<session_id>`:

| Câu hỏi | Rewrite trong log | Intent |
| --- | --- | --- |
| Thông tư 32/2024/TT-BCA có hiệu lực từ ngày nào? | Thông tư 32/2024/TT-BCA có hiệu lực từ ngày nào? | `kb_search` |
| Nó sửa đổi những thông tư nào? | Thông tư 32/2024/TT-BCA sửa đổi những thông tư nào? | `kb_search` |
| Giải thích thêm ý thứ nhất trong câu trả lời vừa rồi. | Giải thích chi tiết nội dung sửa đổi, bổ sung của Thông tư 32/2024/TT-BCA đối với Thông tư số 149/2020/TT-BCA | `follow_up` |

Câu trả lời đầu bằng tiếng Việt, có citation và ngày hiệu lực đúng `24 tháng 8 năm 2024`. Log rewrite lưu trong JSON cho thấy hai câu tiếp nối đã có chủ thể cụ thể, không lẫn tiếng Trung.

Render trang đầu PDF thành PNG bằng `pdftoppm -f 1 -singlefile -scale-to 1000 -png`, gửi `Mô tả ảnh này.` kèm ảnh base64 trong `images[].data` ở lượt tiếp theo. Log có `intent=image_only`, `has_image_desc=true`; caption được lưu vào user message bằng tiếng Việt. Đây là kiểm tra caption của ảnh đính kèm trong chat, không phải kiểm tra riêng caption ảnh trích xuất khi nạp tài liệu.

### Câu hỏi gợi ý

Knowledge base dùng cấu hình setup nguyên trạng trả danh sách gợi ý rỗng: setup không bật sinh câu hỏi cho chunk. Không thay mặc định này để phục vụ kiểm thử.

Tạo knowledge base tạm thứ hai, vẫn theo setup nhưng thêm:

```json
{"question_generation_config": {"enabled": true, "question_count": 2}}
```

Tắt graph để tránh công việc không liên quan. Upload Markdown chứa một đoạn đã parse từ PDF trên (nguyên văn đoạn dùng kiểm tra nằm ở `questions_with_generation_enabled.source_excerpt` trong JSON), chờ `parse_status=completed`, rồi gọi:

```text
GET /api/v1/agents/builtin-quick-answer/suggested-questions?knowledge_base_ids=<kb_id>&limit=3
```

Trả về 3 câu tiếng Việt, ví dụ:

> Cơ quan Công an thực hiện kiểm tra điều kiện bảo đảm an toàn về cứu nạn, cứu hộ theo quy định nào trong Nghị định số 50/2024/NĐ-CP?

Các knowledge base, agent và session được tạo riêng cho kiểm tra đã được xoá bằng API; không xoá tài nguyên có sẵn.

## Chạy lại và giới hạn

1. Chạy Go test và so sánh overlay như trên.
2. `./scripts/compose.sh build app`, rồi `./scripts/compose.sh up -d --no-deps --force-recreate app`; chờ `/health`.
3. Đăng nhập bằng helper trong `scripts/setup.py`. Gửi `Accept-Language: en-US` cho mọi request; thực hiện hai luồng tạm ở trên, dùng helper upload trong `scripts/e2e.py`. Lưu summary, suggestions, messages và log `stage=QueryUnderstand action=output` trước khi xoá tài nguyên thử nghiệm. Kết quả LLM không nhất thiết giống từng chữ.
4. Mở UI tiếng Anh tại `/platform/agents`, kiểm tra tên agent, rồi Create Agent → Prompts → Use Template để kiểm tra tên template (không cần lưu). Lần chạy này dùng Chrome headless + Chrome DevTools Protocol qua WebSocket native của Node, không cài dependency. Profile và token tạm đã được xoá; screenshot cục bộ tại `/tmp/weknora-issue5-agents.png` và `/tmp/weknora-issue5-editor.png`, DOM lưu bền trong JSON. Summary, hội thoại, ảnh và câu hỏi gợi ý được kiểm tra qua API với header tiếng Anh, không lặp lại toàn bộ các tương tác đó trong browser.

Bản ghi chứng minh **ngôn ngữ đầu ra**, không nghiệm thu chất lượng nội dung của LLM. Quan sát thấy câu gợi ý đầu dùng sai số thông tư (`149/2024/TT-BCA`), và đầu ra ảnh có chi tiết không chính xác. Không sửa các vấn đề chất lượng đó trong #5. Các nhãn trạng thái tool tiếng Trung nằm ngoài phạm vi spec #1. Không chạy lại toàn bộ Bộ kiểm tra keyword vì bản vá này không đổi retrieval/tokenizer.
