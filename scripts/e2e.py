#!/usr/bin/env python3
"""Script E2E hộp đen trên stack đã deploy, chỉ gọi HTTP API của WeKnora.

1. Tạo knowledge base riêng cho lần chạy (cấu hình của scripts/setup.py).
2. Upload tài liệu mẫu trong eval/documents.json, chờ parse xong.
3. Kiểm tra chunk: footnote còn, tiêu đề Điều không bị cắt ngang, breadcrumb
   của chunk con có Chương/Điều, mọi chunk NFC.
4. Chạy Bộ kiểm tra keyword (eval/keyword-set.json) qua hybrid-search ở 3 chế
   độ: keyword (disable_vector_match), vector (disable_keywords_match), hybrid;
   so sánh cả danh sách kết quả (kể cả thứ tự) giữa câu NFC và NFD.
5. Ghi recall@k, MRR, câu trượt và metadata vào results/<thời điểm>-<commit>.json.

Kiểm tra chunk/NFC-NFD fail không làm script thoát lỗi (Fork chưa vá fail là baseline).
Script thoát mã 1 khi tài liệu parse lỗi hoặc API lỗi. Ngoài HTTP API, script đọc
tokenizer BM25 và breadcrumb của chunk bằng psql, vì API không trả hai thông tin này.
    python3 scripts/e2e.py [--keep-kb] [--out results/baseline.json]
"""

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path

from setup import ROOT, APIError, connect, create_knowledge_base, load_env

DOCUMENTS = ROOT / "eval" / "documents.json"
KEYWORD_SET = ROOT / "eval" / "keyword-set.json"
RESULTS = ROOT / "results"

MODES = {
    "keyword": {"disable_vector_match": True},
    "vector": {"disable_keywords_match": True},
    "hybrid": {},
}
KS = (1, 3, 5, 10)
MATCH_COUNT = max(KS)
# finalizing: chunk đã được index, chỉ còn tóm tắt/graph chạy nền.
SEARCHABLE = {"finalizing", "completed"}
FAILED = {"failed", "cancelled", "deleting"}


def norm(text):
    """Dạng so khớp: NFC, bỏ nhấn mạnh Markdown, gộp khoảng trắng.

    Chỉ dùng để so khớp đoạn mong đợi; kiểm tra NFC chạy trên text gốc.
    """
    text = unicodedata.normalize("NFC", text).replace("**", "")
    return " ".join(text.split())


def load_inputs():
    docs = json.loads(DOCUMENTS.read_text(encoding="utf-8"))["documents"]
    questions = json.loads(KEYWORD_SET.read_text(encoding="utf-8"))["questions"]
    doc_ids = {d["id"] for d in docs}
    for doc in docs:
        if doc.get("unicode_form") == "NFD":
            text = (ROOT / doc["file"]).read_text(encoding="utf-8")
            if not unicodedata.is_normalized("NFD", text) or unicodedata.is_normalized("NFC", text):
                sys.exit(f"{doc['file']}: fixture phải là NFD, không đồng thời là NFC")
    seen = set()
    for q in questions:
        problems = []
        if q["id"] in seen:
            problems.append("id trùng")
        seen.add(q["id"])
        if q.get("form", "nfc") not in ("nfc", "nfd"):
            problems.append("form phải là nfc hoặc nfd")
        if q["answerable"] != bool(q.get("expected")):
            problems.append("answerable=true cần expected, answerable=false không có expected")
        if q.get("doc") is not None and q["doc"] not in doc_ids:
            problems.append(f"doc {q['doc']} không có trong {DOCUMENTS.name}")
        if problems:
            sys.exit(f"{KEYWORD_SET.name}: câu {q['id']}: {'; '.join(problems)}")
    return docs, questions


def upload(client, kb_id, path):
    boundary = uuid.uuid4().hex
    head = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
            f"filename=\"{path.name}\"\r\nContent-Type: application/octet-stream\r\n\r\n")
    body = head.encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    resp = client.request("POST", f"/api/v1/knowledge-bases/{kb_id}/knowledge/file", body,
                          timeout=300, content_type=f"multipart/form-data; boundary={boundary}")
    return resp["data"]["id"]


def wait_parsed(client, knowledge_ids, timeout):
    """Chờ mọi tài liệu tìm được hoặc lỗi. Trả về {id: (knowledge, số giây từ lúc upload)}."""
    start, done = time.time(), {}
    while True:
        for knowledge_id in knowledge_ids:
            if knowledge_id in done:
                continue
            k = client.request("GET", f"/api/v1/knowledge/{knowledge_id}")["data"]
            if k["parse_status"] in SEARCHABLE | FAILED or time.time() - start > timeout:
                done[knowledge_id] = (k, round(time.time() - start))
        if len(done) == len(knowledge_ids):
            return done
        time.sleep(5)


def list_chunks(client, knowledge_id):
    chunks, page = [], 1
    while True:
        resp = client.request(
            "GET", f"/api/v1/chunks/{knowledge_id}?page={page}&page_size=1000"
                   "&chunk_type=text&chunk_type=parent_text")
        chunks += resp["data"] or []
        if len(chunks) >= resp["total"] or not resp["data"]:
            return chunks
        page += 1


def check_chunks(docs, chunks_by_doc, headers):
    """Kiểm tra footnote, tiêu đề Điều, breadcrumb và NFC. Mỗi kiểm tra báo pass/fail riêng.

    headers: {chunk id: breadcrumb (context_header)}.
    """
    footnotes_missing, headings_missing, breadcrumbs_wrong, non_nfc = [], [], [], []
    for doc in docs:
        chunks = chunks_by_doc.get(doc["id"], [])
        if not chunks:
            non_nfc.append({"doc": doc["id"], "error": "không có chunk để kiểm tra"})
        # Chunk con (text) là thứ được tìm kiếm; chunk cha chỉ dùng để trả lời.
        texts = [norm(c["content"]) for c in chunks if c["chunk_type"] == "text"]
        for snippet in doc.get("footnotes", []):
            if not any(norm(snippet) in t for t in texts):
                footnotes_missing.append({"doc": doc["id"], "text": snippet})
        for heading in doc.get("headings", []):
            if not any(norm(heading) in t for t in texts):
                headings_missing.append({"doc": doc["id"], "text": heading})
        # Breadcrumb lấy ở đầu chunk: chunk con chứa đoạn text phải có đủ các tiêu đề.
        for want in doc.get("breadcrumbs", []):
            got = [headers.get(c["id"], "") for c in chunks
                   if c["chunk_type"] == "text" and norm(want["text"]) in norm(c["content"])]
            if not any(all(norm(h) in norm(g) for h in want["header"]) for g in got):
                breadcrumbs_wrong.append({"doc": doc["id"], "text": want["text"],
                                          "want": want["header"], "got": got})
        for c in chunks:
            if not unicodedata.is_normalized("NFC", c["content"]):
                non_nfc.append({"doc": doc["id"], "chunk_type": c["chunk_type"],
                                "chunk_index": c["chunk_index"]})

    def result(missing, total):
        return {"pass": not missing, "checked": total, "failed": missing}

    return {
        "footnotes": result(footnotes_missing, sum(len(d.get("footnotes", [])) for d in docs)),
        "dieu_headings": result(headings_missing, sum(len(d.get("headings", [])) for d in docs)),
        "breadcrumbs": result(breadcrumbs_wrong, sum(len(d.get("breadcrumbs", [])) for d in docs)),
        "nfc": result(non_nfc, sum(len(v) for v in chunks_by_doc.values())),
    }


def search(client, kb_id, query, mode):
    body = {"query_text": query, "match_count": MATCH_COUNT, "vector_threshold": 0,
            "keyword_threshold": 0, "skip_context_enrichment": True, **MODES[mode]}
    return client.request("POST", f"/api/v1/knowledge-bases/{kb_id}/hybrid-search", body)["data"] or []


def first_hit(results, expected):
    """Hạng (từ 1) của kết quả đầu tiên chứa một đoạn mong đợi, None nếu không có."""
    wanted = [norm(e) for e in expected]
    for rank, r in enumerate(results, 1):
        content = norm(r["content"])
        if any(w in content for w in wanted):
            return rank
    return None


def run_questions(client, kb_id, questions):
    per_question = []
    for q in questions:
        query = unicodedata.normalize("NFD" if q.get("form") == "nfd" else "NFC", q["query"])
        entry = {"id": q["id"], "query": q["query"], "form": q.get("form", "nfc"),
                 "answerable": q["answerable"], "tags": q.get("tags", []), "modes": {}}
        for mode in MODES:
            results = search(client, kb_id, query, mode)
            other_form = "NFC" if q.get("form") == "nfd" else "NFD"
            paired = search(client, kb_id, unicodedata.normalize(other_form, q["query"]), mode)
            ids = [r["id"] for r in results]
            paired_ids = [r["id"] for r in paired]
            nfc_ids, nfd_ids = (paired_ids, ids) if other_form == "NFC" else (ids, paired_ids)
            entry["modes"][mode] = {
                "unicode_equivalence": {"pass": nfc_ids == nfd_ids,
                                        "nfc_ids": nfc_ids, "nfd_ids": nfd_ids},
                "rank": first_hit(results, q["expected"]) if q["answerable"] else None,
                "top_score": results[0]["score"] if results else None,
                "top": [{"score": r["score"], "match_type": r.get("match_type"),
                         "content": norm(r["content"])[:160]} for r in results[:3]],
            }
        per_question.append(entry)
    return per_question


def score(per_question):
    answerable = [q for q in per_question if q["answerable"]]
    modes = {}
    for mode in MODES:
        ranks = [q["modes"][mode]["rank"] for q in answerable]
        n = len(ranks) or 1
        modes[mode] = {
            **{f"recall@{k}": round(sum(1 for r in ranks if r and r <= k) / n, 4) for k in KS},
            "mrr": round(sum(1 / r for r in ranks if r) / n, 4),
            "failed": [{"id": q["id"], "query": q["query"]}
                       for q in answerable if q["modes"][mode]["rank"] is None],
        }
    return {"match_count": MATCH_COUNT, "answerable": len(answerable),
            "unanswerable": len(per_question) - len(answerable), "modes": modes}


def psql(sql):
    """Chạy một câu SQL trong container postgres, trả về stdout dạng -tA."""
    cmd = [str(ROOT / "scripts" / "compose.sh"), "exec", "-T", "postgres", "sh", "-c",
           'psql -X -tA -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f -']
    return subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=60,
                          check=True).stdout


def context_headers(knowledge_ids):
    """Breadcrumb (context_header) của mọi chunk, đọc từ postgres (API không trả trường này)."""
    if not knowledge_ids:
        return {}
    ids = ", ".join(f"'{k}'" for k in knowledge_ids)
    try:
        out = psql("SELECT json_object_agg(id, coalesce(context_header, '')) FROM chunks "
                   f"WHERE knowledge_id IN ({ids})")
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Không đọc được breadcrumb: {err}", file=sys.stderr)
        return {}
    return json.loads(out.strip() or "null") or {}


def bm25_tokenizer():
    """Tokenizer của chỉ mục BM25, đọc từ postgres (API không công bố thông tin này)."""
    try:
        out = psql("SELECT indexdef FROM pg_indexes WHERE tablename = 'embeddings' "
                   "AND indexdef ILIKE '%USING bm25%'")
    except (OSError, subprocess.SubprocessError) as err:
        print(f"Không đọc được tokenizer BM25: {err}", file=sys.stderr)
        return {"name": "unknown", "indexdef": None}
    names = re.findall(r'"tokenizer"\s*:\s*\{\s*"type"\s*:\s*"([^"]+)"', out)
    return {"name": ",".join(sorted(set(names))) or "unknown", "indexdef": out.strip()}


def model_info(client, kb):
    models = {m["id"]: m for m in client.request("GET", "/api/v1/models")["data"]}
    emb = models.get(kb.get("embedding_model_id"), {})
    params = emb.get("parameters", {})
    return {
        "embedding": {"id": emb.get("id"), "name": emb.get("name"),
                      "dimension": (params.get("embedding_parameters") or {}).get("dimension")},
        "summary": {"id": kb.get("summary_model_id"),
                    "name": models.get(kb.get("summary_model_id"), {}).get("name")},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--keep-kb", action="store_true", help="giữ knowledge base sau khi chạy")
    parser.add_argument("--out", type=Path, help="file kết quả (mặc định results/<thời điểm>-<commit>.json)")
    parser.add_argument("--parse-timeout", type=int, default=3600, help="giây chờ parse mọi tài liệu")
    args = parser.parse_args()

    docs, questions = load_inputs()
    env = load_env(ROOT / ".env")
    started = datetime.now().astimezone()
    client = connect(env)
    system = client.request("GET", "/api/v1/system/info")["data"]
    kb_name = f"e2e-{started:%Y%m%d-%H%M%S}"
    kb_id = create_knowledge_base(client, kb_name)
    kb = client.request("GET", f"/api/v1/knowledge-bases/{kb_id}")["data"]

    ok = True
    doc_results, chunks_by_doc = [], {}
    try:
        uploaded = []
        for doc in docs:
            uploaded.append((doc, upload(client, kb_id, ROOT / doc["file"])))
            print(f"Upload {doc['file']}")
        parsed = wait_parsed(client, [kid for _, kid in uploaded], args.parse_timeout)
        for doc, knowledge_id in uploaded:
            k, seconds = parsed[knowledge_id]
            status = k["parse_status"]
            # Tài liệu parse song song nên thời gian gồm cả lúc xếp hàng.
            entry = {"id": doc["id"], "file": doc["file"], "knowledge_id": knowledge_id,
                     "parse_status": status, "error": k.get("error_message") or None,
                     "seconds_to_searchable": seconds}
            if status in SEARCHABLE:
                chunks_by_doc[doc["id"]] = list_chunks(client, knowledge_id)
                kinds = [c["chunk_type"] for c in chunks_by_doc[doc["id"]]]
                entry.update(text_chunks=kinds.count("text"), parent_chunks=kinds.count("parent_text"))
            else:
                ok = False
            doc_results.append(entry)
            print(f"Parse {doc['file']}: {status}")

        headers = context_headers([e["knowledge_id"] for e in doc_results
                                   if e["id"] in chunks_by_doc])
        chunk_checks = check_chunks(docs, chunks_by_doc, headers)
        for name, check in chunk_checks.items():
            print(f"Kiểm tra chunk {name}: {'PASS' if check['pass'] else 'FAIL'} "
                  f"({len(check['failed'])}/{check['checked']} lỗi)")

        per_question = run_questions(client, kb_id, questions)
        search_scores = score(per_question)
        unicode_failed = [{"id": q["id"], "mode": mode}
                          for q in per_question for mode in MODES
                          if not q["modes"][mode]["unicode_equivalence"]["pass"]]
        unicode_check = {"pass": not unicode_failed, "checked": len(per_question) * len(MODES),
                         "failed": unicode_failed}
        print(f"NFC/NFD cùng danh sách kết quả: {'PASS' if unicode_check['pass'] else 'FAIL'} "
              f"({len(unicode_failed)}/{unicode_check['checked']} lỗi)")
        for mode, s in search_scores["modes"].items():
            recalls = " ".join(f"R@{k}={s[f'recall@{k}']:.2f}" for k in KS)
            print(f"{mode:8} {recalls} MRR={s['mrr']:.2f} trượt={len(s['failed'])}")

        result = {
            "run": {"started_at": started.isoformat(timespec="seconds"),
                    "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                    "kb_id": kb_id, "kb_name": kb_name, "kb_kept": args.keep_kb},
            "fork": {"commit": system.get("commit_id"), "version": system.get("version"),
                     "db_version": system.get("db_version")},
            "tokenizer": bm25_tokenizer(),
            "models": model_info(client, kb),
            "chunking": kb.get("chunking_config"),
            "documents": doc_results,
            "chunk_checks": chunk_checks,
            "search": search_scores,
            "unicode_equivalence": unicode_check,
            "questions": per_question,
        }
        out = args.out or RESULTS / f"{started:%Y%m%d-%H%M%S}-{system.get('commit_id')}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Kết quả: {out}")
    except APIError as err:
        sys.exit(f"Lỗi API: {err}")
    finally:
        if not args.keep_kb:
            client.request("DELETE", f"/api/v1/knowledge-bases/{kb_id}")
            print(f"Xoá knowledge base {kb_name}")
    if not ok:
        sys.exit("Có tài liệu parse lỗi, xem 'documents' trong file kết quả.")


if __name__ == "__main__":
    main()
