# Bản vá chỉ dành cho Fork: chỉ PostgreSQL, không feature flag

Thay đổi code cho tiếng Việt (ánh xạ ngôn ngữ, chunker, mở rộng câu hỏi, NFC, footnote, tokenizer BM25) được sửa thẳng trong Fork. Chúng chỉ chạy trên PostgreSQL, không có feature flag và không giữ tương đương với SQLite hay các backend tìm kiếm khác. Lý do: dự án chỉ chạy một cấu hình duy nhất, nên thêm flag và giữ tương đương sẽ tốn công mà không ai dùng tới. Đổi lại, muốn gửi các bản vá này lên WeKnora gốc thì phải làm lại phần flag và phần tương đương, và mỗi lần nâng phiên bản gốc phải rebase các bản vá.
