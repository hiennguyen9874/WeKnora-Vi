#!/usr/bin/env python3
"""Đo số ký tự/token của văn bản tiếng Việt bằng tokenizer thật của embedder.

Văn bản đo là chunk con của các tài liệu mẫu đã parse trong một knowledge base
(thường là knowledge base giữ lại bởi `scripts/e2e.py --keep-kb`). Số token lấy
từ `usage.prompt_tokens` của embeder-gateway, gửi mỗi chunk một request, rồi
trừ phần token cố định của prompt format. Script còn ghép lại toàn văn từng tài
liệu từ offset của chunk để đo độ dài mỗi Điều (dùng để chốt chunk cha), và dò
giới hạn input của embedder.

Chỉ dùng thư viện chuẩn của Python.
    python3 scripts/e2e.py --keep-kb
    python3 scripts/measure_tokens.py --kb <id knowledge base> [--out results/chars-per-token.json]
"""

import argparse
import json
import re
import statistics
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from e2e import list_chunks
from setup import ROOT, connect, load_env

EMBEDDING_MODEL = "Qwen3-VL-Embedding-2B"
DIEU = re.compile(r"(?m)^[ \t#*“\"]*Điều \d+[a-zđ]?\.")


class Embedder:
    def __init__(self, base_url, api_key):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def prompt_tokens(self, text):
        """Số token của một input, gồm phần prompt format. None khi quá giới hạn."""
        body = {"model": EMBEDDING_MODEL, "input": [text], "input_type": "document", "dimensions": 64}
        req = urllib.request.Request(self.base_url + "/embeddings", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + self.api_key})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.load(resp)["usage"]["prompt_tokens"]
        except urllib.error.HTTPError as err:
            if err.code == 400:
                return None
            raise


def rebuild(chunks):
    """Ghép toàn văn tài liệu từ chunk con theo offset rune (start_at/end_at)."""
    text = []
    for c in sorted(chunks, key=lambda c: c["start_at"]):
        if c["start_at"] > len(text):
            text.extend("\n" * (c["start_at"] - len(text)))
        text.extend(list(c["content"])[len(text) - c["start_at"]:])
    return "".join(text)


def percentiles(values):
    q = statistics.quantiles(values, n=20)
    return {"min": min(values), "p5": q[0], "p10": q[1], "p50": q[9], "p90": q[17], "p95": q[18],
            "max": max(values)}


def round_all(d):
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in d.items()}


def input_limit(embedder):
    """Tìm số token nội dung lớn nhất embedder nhận ("x " là 1 token)."""
    lo, hi = 1, 1
    while embedder.prompt_tokens("x " * hi) is not None:
        lo, hi = hi, hi * 2
        if hi > 1 << 20:
            return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if embedder.prompt_tokens("x " * mid) is not None else (lo, mid)
    return lo + 1  # "x " * n là n + 1 token nội dung (khoảng trắng cuối là 1 token)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kb", required=True, help="id knowledge base có tài liệu mẫu đã parse")
    parser.add_argument("--embedder-url", help="base URL /v1 của embeder-gateway nhìn từ máy chạy "
                                               "script (mặc định EMBEDER_GATEWAY_URL)")
    parser.add_argument("--out", type=Path, default=ROOT / "results" / "chars-per-token.json")
    args = parser.parse_args()

    env = load_env(ROOT / ".env")
    client = connect(env)
    embedder = Embedder(args.embedder_url or env["EMBEDER_GATEWAY_URL"], env["EMBEDER_GATEWAY_API_KEY"])
    # Phần cố định của prompt format: input "a" là đúng 1 token nội dung.
    overhead = embedder.prompt_tokens("a") - 1

    knowledge = client.request("GET", f"/api/v1/knowledge-bases/{args.kb}/knowledge?page=1&page_size=100")["data"]
    docs, all_chars, all_tokens, ratios, dieu_chars, max_tokens = [], 0, 0, [], [], 0
    for k in knowledge:
        chunks = [c for c in list_chunks(client, k["id"]) if c["chunk_type"] == "text"]
        chars = tokens = 0
        for c in chunks:
            n_chars = len(c["content"])
            n_tokens = embedder.prompt_tokens(c["content"]) - overhead
            chars, tokens = chars + n_chars, tokens + n_tokens
            max_tokens = max(max_tokens, n_tokens)
            if n_chars >= 100:  # chunk quá ngắn làm tỉ lệ dao động mạnh
                ratios.append(n_chars / n_tokens)
        text = rebuild(chunks)
        starts = [m.start() for m in DIEU.finditer(text)] + [len(text)]
        sizes = [b - a for a, b in zip(starts, starts[1:])]
        dieu_chars += sizes
        docs.append({"file": k["file_name"], "text_chunks": len(chunks), "chars": chars, "tokens": tokens,
                     "chars_per_token": round(chars / tokens, 3), "dieu": len(sizes)})
        all_chars, all_tokens = all_chars + chars, all_tokens + tokens
        print(f"{k['file_name']}: {chars} ký tự / {tokens} token = {chars / tokens:.2f}, {len(sizes)} Điều")

    limit = input_limit(embedder)
    result = {
        "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "method": ("Chunk con của tài liệu mẫu, đếm ký tự bằng số code point (như rune của Go), "
                   "đếm token bằng usage.prompt_tokens của embeder-gateway trừ phần prompt format."),
        "embedding_model": EMBEDDING_MODEL,
        "kb_id": args.kb,
        "prompt_format_overhead_tokens": overhead,
        "embedder_input_limit_tokens": limit,
        "max_text_chunk_tokens": max_tokens,
        "documents": docs,
        "chars_per_token": {"overall": round(all_chars / all_tokens, 3),
                            "per_chunk_min_100_chars": round_all(percentiles(ratios)),
                            "chunks": len(ratios)},
        "dieu_chars": round_all(percentiles(dieu_chars)) | {"count": len(dieu_chars)},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("embedder_input_limit_tokens", "max_text_chunk_tokens",
                                             "chars_per_token", "dieu_chars")},
                     ensure_ascii=False, indent=1))
    print(f"Kết quả: {args.out}")


if __name__ == "__main__":
    sys.exit(main())
