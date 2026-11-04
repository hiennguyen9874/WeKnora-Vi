# WeKnora tiếng Việt

Triển khai WeKnora để hỏi đáp trên tài liệu tiếng Việt, với giao diện giữ tiếng Anh.

## Ngôn ngữ

**Ngôn ngữ xử lý** (processing language):
Ngôn ngữ của mọi nội dung hệ thống sinh ra: câu trả lời, tóm tắt, câu hỏi gợi ý, trang wiki, mô tả ảnh. Ở đây luôn là tiếng Việt.
_Avoid_: ngôn ngữ app, locale, ngôn ngữ tài liệu

**Ngôn ngữ giao diện** (UI locale):
Ngôn ngữ của menu và nhãn trên Web UI. Ở đây luôn là tiếng Anh, tách biệt hoàn toàn với Ngôn ngữ xử lý.
_Avoid_: ngôn ngữ app, ngôn ngữ trình duyệt

## Mã nguồn

**Repo triển khai**:
Repo này: chứa cấu hình, overlay và script để dựng và kiểm tra hệ thống, không chứa code WeKnora.
_Avoid_: repo chính, WeKnora-Vi (khi muốn nói code)

**Fork**:
Bản WeKnora của dự án, nơi duy nhất chứa thay đổi code so với WeKnora gốc.
_Avoid_: upstream, submodule

## Kiểm tra

**Bộ kiểm tra keyword**:
Tập câu hỏi tiếng Việt, mỗi câu gắn với chunk đúng, dùng để so sánh các tokenizer của tìm kiếm từ khoá. Không dùng để chấm chất lượng câu trả lời.
_Avoid_: bộ đánh giá, eval set, benchmark
