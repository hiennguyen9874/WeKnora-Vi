#!/usr/bin/env python3
"""Thí nghiệm chọn tokenizer BM25 (#11, ADR 0002) trên stack đã dựng.

Mỗi ứng viên là một cấu hình tokenizer của content trong chỉ mục embeddings_search_idx,
dựng lại bằng eval/bm25-tokenizer.sql trên đúng dữ liệu đã nạp.

    python3 scripts/bm25_tokenizers.py tokenize            # ví dụ token hoá + kiểm tra bộ lọc
    python3 scripts/bm25_tokenizers.py apply icu-fold      # dựng lại chỉ mục với một ứng viên
    python3 scripts/bm25_tokenizers.py apply icu           # trả về chỉ mục của migration 000134
    python3 scripts/bm25_tokenizers.py sweep --reuse-kb results/<lần nạp --keep-kb>.json

sweep: với từng ứng viên, dựng lại chỉ mục rồi chạy scripts/e2e.py --reuse-kb, ghi
results/bm25-<ứng viên>.json; xong thì trả về icu (chỉ mục của Fork) và ghi bảng tổng hợp
results/bm25-tokenizers.json.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from e2e import MODES, psql
from setup import ROOT

SQL = ROOT / "eval" / "bm25-tokenizer.sql"
RESULTS = ROOT / "results"

# Tên ứng viên -> tokenizer của content (dạng text_fields JSON như 000002_embeddings).
CANDIDATES = {
    "chinese_lindera": {"type": "chinese_lindera"},
    "chinese_lindera-fold": {"type": "chinese_lindera", "ascii_folding": True},
    "icu": {"type": "icu"},
    "icu-fold": {"type": "icu", "ascii_folding": True},
    "whitespace": {"type": "whitespace", "lowercase": True},
    "whitespace-fold": {"type": "whitespace", "lowercase": True, "ascii_folding": True},
}
# Chỉ mục Fork tạo ra (migration 000134, #12); sweep trả về đây khi xong.
ORIGINAL = "icu"

SAMPLES = [
    "Điều 11a khoản 1: điều kiện cấp Giấy phép sản xuất vàng miếng theo 117/2026/VBHN-NĐ-NHNN.",
    "dieu kien cap giay phep san xuat vang mieng",
]
# Từ dò trên chỉ mục thật: số chunk chứa đúng token này.
PROBE_TERMS = ["điều", "dieu", "bhxh", "vàng", "vang", " ", "117/2026/vbhn-nđ-nhnn"]


def sql_literal(text):
    return "'" + text.replace("'", "''") + "'"


def tokenize(config, text):
    out = psql(f"SELECT coalesce(json_agg(token ORDER BY position), '[]') FROM paradedb.tokenize("
               f"{sql_literal(json.dumps(config))}::jsonb, {sql_literal(text)})")
    return json.loads(out)


def filter_checks(config):
    """Kiểm tra bộ lọc thật sự có tác dụng; text_fields JSON không báo lỗi khoá lạ."""
    tokens = tokenize(config, "Điều BHXH")
    checks = {"lowercase": "bhxh" in tokens}
    checks["ascii_folding"] = "dieu" in tokens
    wanted = {"lowercase": config.get("lowercase", True), "ascii_folding": config.get("ascii_folding", False)}
    return {"tokens": tokens, "ok": checks == wanted, "observed": checks, "wanted": wanted}


def cmd_tokenize(_args):
    tokenizers = psql("SELECT string_agg(tokenizer, ', ') FROM paradedb.tokenizers()").strip()
    version = psql("SELECT extversion FROM pg_extension WHERE extname = 'pg_search'").strip()
    report = {"pg_search": version, "tokenizers": tokenizers.split(", "), "candidates": {}}
    ok = True
    for name, config in CANDIDATES.items():
        checks = filter_checks(config)
        ok &= checks["ok"]
        report["candidates"][name] = {"config": config, "filters": checks,
                                      "samples": {s: tokenize(config, s) for s in SAMPLES}}
        print(f"== {name} {json.dumps(config, ensure_ascii=False)} bộ lọc: "
              f"{'OK' if checks['ok'] else 'SAI ' + json.dumps(checks['observed'])}")
        for s in SAMPLES:
            print("  " + " | ".join(report["candidates"][name]["samples"][s]))
    out = RESULTS / "bm25-tokenize.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kết quả: {out}")
    if not ok:
        sys.exit("Có ứng viên mà bộ lọc không có tác dụng như khai báo.")


def apply(name):
    config = CANDIDATES[name]
    if not filter_checks(config)["ok"]:
        sys.exit(f"{name}: bộ lọc không có tác dụng như khai báo, không dựng chỉ mục.")
    cmd = [str(ROOT / "scripts" / "compose.sh"), "exec", "-T", "postgres", "sh", "-c",
           'psql -X -q -tA -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v tokenizer="$1" -f -',
           "sh", json.dumps(config)]
    proc = subprocess.run(cmd, input=SQL.read_text(encoding="utf-8"), capture_output=True,
                          text=True, timeout=1800)
    if proc.returncode:
        sys.exit(f"Dựng chỉ mục {name} lỗi:\n{proc.stderr}")
    rows = int(psql("SELECT count(*) FROM embeddings"))
    indexed = int(psql("SELECT count(*) FROM embeddings WHERE id @@@ paradedb.all()"))
    probes = {t: int(psql("SELECT count(*) FROM embeddings WHERE id @@@ "
                          f"paradedb.term('content', {sql_literal(t)})")) for t in PROBE_TERMS}
    print(f"Chỉ mục {name}: {indexed}/{rows} dòng; chunk chứa token: {json.dumps(probes, ensure_ascii=False)}")
    if indexed != rows:
        sys.exit("Chỉ mục không phủ đủ bảng embeddings.")
    return {"rows": rows, "indexed": indexed, "term_probes": probes}


def cmd_apply(args):
    apply(args.candidate)


def cmd_sweep(args):
    summary = {"reuse_kb": str(args.reuse_kb), "candidates": {}}
    try:
        for name in args.only or CANDIDATES:
            index = apply(name)
            out = RESULTS / f"bm25-{name}.json"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "e2e.py"),
                            "--reuse-kb", str(args.reuse_kb), "--out", str(out)], check=True)
            # Tóm tắt/graph chạy nền có thể thêm chunk giữa chừng; mọi ứng viên phải đo cùng dữ liệu.
            rows = int(psql("SELECT count(*) FROM embeddings"))
            first = next(iter(summary["candidates"].values()), {"index": index})["index"]["rows"]
            if not rows == index["rows"] == first:
                sys.exit(f"{name}: bảng embeddings đổi ({first} -> {index['rows']} -> {rows} dòng) "
                         "trong lúc đo; chờ tài liệu xử lý nền xong rồi chạy lại.")
            result = json.loads(out.read_text(encoding="utf-8"))
            assert result["tokenizer"]["config"] == CANDIDATES[name], result["tokenizer"]
            summary["candidates"][name] = {
                "config": CANDIDATES[name], "index": index, "result": out.name,
                "modes": {m: {k: v for k, v in s.items() if k != "failed"} | {
                    "failed": [f["id"] for f in s["failed"]]}
                    for m, s in result["search"]["modes"].items()},
                "unicode_equivalence": result["unicode_equivalence"]["pass"],
            }
    finally:
        apply(ORIGINAL)
    out = RESULTS / "bm25-tokenizers.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print_table(summary)
    print(f"Tổng hợp: {out}")


def print_table(summary):
    print("| Ứng viên | Chế độ | R@1 | R@3 | R@5 | R@10 | MRR | p50 ms | p95 ms |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for name, c in summary["candidates"].items():
        for mode in MODES:
            if mode == "vector":
                continue  # vector không dùng chỉ mục BM25
            s = c["modes"][mode]
            print(f"| {name} | {mode} | " + " | ".join(f"{s[f'recall@{k}']:.4f}" for k in (1, 3, 5, 10))
                  + f" | {s['mrr']:.4f} | {s['latency_ms']['p50']} | {s['latency_ms']['p95']} |")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(required=True)
    sub.add_parser("tokenize", help="ví dụ token hoá và kiểm tra bộ lọc").set_defaults(func=cmd_tokenize)
    p = sub.add_parser("apply", help="dựng lại chỉ mục với một ứng viên")
    p.add_argument("candidate", choices=CANDIDATES)
    p.set_defaults(func=cmd_apply)
    p = sub.add_parser("sweep", help="đo mọi ứng viên trên knowledge base đã giữ")
    p.add_argument("--reuse-kb", type=Path, required=True, metavar="RESULT")
    p.add_argument("--only", nargs="+", choices=CANDIDATES, help="chỉ đo các ứng viên này")
    p.set_defaults(func=cmd_sweep)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
