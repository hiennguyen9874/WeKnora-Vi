#!/usr/bin/env bash
# In thông tin database cần ghi lại: lc_ctype, phiên bản ParadeDB, chỉ mục BM25
# và HNSW, và EXPLAIN của truy vấn vector 1024 chiều (cùng dạng câu SQL trong
# internal/application/repository/retriever/postgres/repository.go).
#   ./scripts/check-db.sh | tee docs/db-check.txt
# EXPLAIN cần ít nhất một chunk 1024 chiều (upload một tài liệu trước).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

psql() {
  "$root/scripts/compose.sh" exec -T postgres \
    sh -c 'psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

psql <<'SQL'
\echo '== lc_ctype / lc_collate'
SHOW lc_ctype;
SHOW lc_collate;
\echo '== Extensions'
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pg_search', 'vector') ORDER BY 1;
\echo '== Index trên embeddings'
SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'embeddings' ORDER BY 1;
\echo '== Số embedding theo số chiều'
SELECT dimension, count(*) FROM embeddings GROUP BY 1 ORDER BY 1;
\echo '== EXPLAIN truy vấn vector 1024 chiều (planner mặc định)'
\set qvec '(SELECT embedding::halfvec(1024) FROM embeddings WHERE dimension = 1024 LIMIT 1)'
EXPLAIN (ANALYZE, COSTS OFF)
SELECT id, embedding::halfvec(1024) <=> :qvec AS distance
FROM embeddings
WHERE dimension = 1024 AND (is_enabled IS NULL OR is_enabled = true)
ORDER BY embedding::halfvec(1024) <=> :qvec
LIMIT 100;
\echo '== EXPLAIN cùng truy vấn, tắt seq scan (bảng nhỏ thì planner chọn seq scan; kiểm tra index dùng được)'
SET enable_seqscan = off;
EXPLAIN (ANALYZE, COSTS OFF)
SELECT id, embedding::halfvec(1024) <=> :qvec AS distance
FROM embeddings
WHERE dimension = 1024 AND (is_enabled IS NULL OR is_enabled = true)
ORDER BY embedding::halfvec(1024) <=> :qvec
LIMIT 100;
SQL
