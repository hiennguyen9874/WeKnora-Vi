-- Thí nghiệm #11: dựng lại chỉ mục BM25 embeddings_search_idx với tokenizer khác,
-- trên đúng dữ liệu đang có trong bảng embeddings. Chỉ đổi tokenizer của content;
-- cột, key_field và dạng khai báo text_fields giữ như 000002_embeddings.
--
--   psql -v tokenizer='{"type": "icu", "ascii_folding": true}' -f eval/bm25-tokenizer.sql
--
-- Trả về chỉ mục gốc: tokenizer='{"type": "chinese_lindera"}'.
-- Dạng text_fields JSON không báo lỗi khi gặp khoá lạ, nên scripts/bm25_tokenizers.py
-- kiểm tra từng bộ lọc bằng paradedb.tokenize trước khi dựng chỉ mục.
\set ON_ERROR_STOP on

SELECT format('{"content": {"tokenizer": %s}}', (:'tokenizer')::jsonb) AS text_fields \gset

BEGIN;
DROP INDEX IF EXISTS embeddings_search_idx;
CREATE INDEX embeddings_search_idx ON embeddings
USING bm25 (id, knowledge_base_id, content, knowledge_id, chunk_id)
WITH (key_field = 'id', text_fields = :'text_fields');
COMMIT;

SELECT indexdef FROM pg_indexes WHERE indexname = 'embeddings_search_idx';
