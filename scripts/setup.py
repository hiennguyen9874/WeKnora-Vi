#!/usr/bin/env python3
"""Cấu hình WeKnora sau khi stack đã chạy. Chạy lại bao nhiêu lần cũng được.

- Đăng nhập tài khoản trong .env (chưa có thì đăng ký).
- Kiểm tra các model built-in từ config/builtin_models.yaml đã được nạp.
- Đặt endpoint PaddleOCR-VL ở tenant parser settings.
- Tạo knowledge base mẫu nếu chưa có knowledge base cùng tên; đã có thì chỉ đưa
  cấu hình chunk (CHUNKING) về giá trị đã chốt.

Chỉ dùng thư viện chuẩn của Python. Biến môi trường thắng giá trị trong .env.
    python3 scripts/setup.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# id trong config/builtin_models.yaml
LLM_ID = "builtin-llm"
VLM_ID = "builtin-vlm"
EMBEDDING_ID = "builtin-embedding"
RERANK_ID = "builtin-rerank"


def load_env(path):
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key.strip()] = value
    values.update(os.environ)
    return values


class APIError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body}")
        self.status = status


class Client:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.token = None

    def request(self, method, path, body=None, timeout=60, content_type="application/json"):
        # body đã là bytes (ví dụ multipart) thì gửi nguyên, còn lại encode JSON.
        data = body if body is None or isinstance(body, bytes) else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", content_type)
        if self.token:
            req.add_header("Authorization", "Bearer " + self.token)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as err:
            raise APIError(err.code, err.read().decode("utf-8", "replace")) from None
        return json.loads(raw) if raw else {}


def wait_healthy(client, seconds=300):
    deadline = time.time() + seconds
    while True:
        try:
            client.request("GET", "/health", timeout=5)
            return
        except (OSError, APIError):
            if time.time() > deadline:
                sys.exit(f"App chưa sẵn sàng sau {seconds}s ở {client.base_url}/health")
            time.sleep(5)


def login(client, env):
    creds = {"email": env["WEKNORA_ADMIN_EMAIL"], "password": env["WEKNORA_ADMIN_PASSWORD"]}
    try:
        resp = client.request("POST", "/api/v1/auth/login", creds)
    except APIError as err:
        if err.status != 401:
            raise
        print(f"Đăng ký tài khoản {creds['email']}")
        client.request("POST", "/api/v1/auth/register",
                       {"username": env["WEKNORA_ADMIN_USERNAME"], **creds})
        resp = client.request("POST", "/api/v1/auth/login", creds)
    client.token = resp["token"]
    tenant = resp.get("active_tenant") or {}
    print(f"Đăng nhập {creds['email']}, tenant {tenant.get('id')}")


def check_builtin_models(client):
    models = client.request("GET", "/api/v1/models")["data"]
    found = {m["id"]: m for m in models}
    missing = [i for i in (LLM_ID, VLM_ID, EMBEDDING_ID, RERANK_ID) if i not in found]
    if missing:
        sys.exit(f"Thiếu model built-in {missing}. Xem log '[builtin-models]' của container app.")
    for model_id in (LLM_ID, VLM_ID, EMBEDDING_ID, RERANK_ID):
        m = found[model_id]
        print(f"Model {model_id}: {m['type']} {m['name']}")


def set_paddleocr_endpoint(client, endpoint):
    path = "/api/v1/tenants/kv/parser-engine-config"
    cfg = client.request("GET", path)["data"] or {}
    if cfg.get("paddleocr_vl_endpoint") == endpoint:
        print(f"Endpoint PaddleOCR-VL đã là {endpoint}")
        return
    # PUT thay cả object; gửi lại cấu hình hiện có để không mất trường khác.
    cfg["paddleocr_vl_endpoint"] = endpoint
    client.request("PUT", path, cfg)
    print(f"Đặt endpoint PaddleOCR-VL = {endpoint}")


# Ví dụ mẫu cho bước trích thực thể/quan hệ của knowledge graph.
# Tags là danh sách loại quan hệ được phép.
GRAPH_EXAMPLE = {
    "enabled": True,
    "text": (
        "Luật Bảo hiểm xã hội số 41/2024/QH15 do Quốc hội ban hành, có hiệu lực từ ngày "
        "01 tháng 7 năm 2025 và thay thế Luật Bảo hiểm xã hội số 58/2014/QH13. Bảo hiểm xã hội "
        "(BHXH) là sự bảo đảm thay thế hoặc bù đắp một phần thu nhập của người lao động."
    ),
    "tags": ["Ban hành", "Thay thế", "Viết tắt"],
    "nodes": [
        {"name": "Luật Bảo hiểm xã hội số 41/2024/QH15",
         "attributes": ["Có hiệu lực từ ngày 01 tháng 7 năm 2025"]},
        {"name": "Quốc hội", "attributes": ["Cơ quan ban hành luật"]},
        {"name": "Luật Bảo hiểm xã hội số 58/2014/QH13", "attributes": ["Văn bản bị thay thế"]},
        {"name": "Bảo hiểm xã hội",
         "attributes": ["Bảo đảm thay thế hoặc bù đắp một phần thu nhập của người lao động"]},
        {"name": "BHXH", "attributes": ["Chữ viết tắt"]},
    ],
    "relations": [
        {"node1": "Quốc hội", "node2": "Luật Bảo hiểm xã hội số 41/2024/QH15", "type": "Ban hành"},
        {"node1": "Luật Bảo hiểm xã hội số 41/2024/QH15",
         "node2": "Luật Bảo hiểm xã hội số 58/2014/QH13", "type": "Thay thế"},
        {"node1": "BHXH", "node2": "Bảo hiểm xã hội", "type": "Viết tắt"},
    ],
}


# Cấu hình chunk đã chốt, xem docs/agents/fork-behaviour.md và docs/validation/issue-7.md.
# - strategy auto: chunker chọn tầng theo cấu trúc tài liệu, nên cắt theo tiêu đề
#   Chương/Mục/Điều và gắn breadcrumb. Bỏ trống là tầng legacy, không cắt theo tiêu đề.
# - languages vi: token limit dùng tỉ lệ 2,5 ký tự/token đo trên Qwen3-VL-Embedding-2B.
# - parent_chunk_size (ký tự): chứa trọn một Điều, trừ hai Điều dài nhất của tài liệu mẫu.
# - child_chunk_size (ký tự): khoảng 120 token; cùng chunk cha 4096 là cặp duy nhất đã thử
#   bằng E2E không tệ hơn baseline ở vector và hybrid.
# - token_limit: trần cho chunk con (1152 ký tự với tỉ lệ vi), xa dưới giới hạn
#   input 8171 token của embedder.
CHUNKING = {
    "strategy": "auto",
    "languages": ["vi"],
    "parent_chunk_size": 4096,
    "child_chunk_size": 384,
    "token_limit": 512,
}


def knowledge_base_body(name):
    return {
        "name": name,
        "description": "Văn bản pháp luật và hành chính tiếng Việt",
        "type": "document",
        "embedding_model_id": EMBEDDING_ID,
        "summary_model_id": LLM_ID,
        "chunking_config": {
            **CHUNKING,
            "separators": ["\n\n", "\n", ". ", "; "],
            "enable_parent_child": True,
            "parser_engine_rules": [
                {"file_types": ["pdf", "jpg", "jpeg", "png", "bmp", "tiff"], "engine": "paddleocr_vl"},
                {"file_types": ["docx", "xlsx"], "engine": "builtin"},
            ],
        },
        "vlm_config": {"enabled": True, "model_id": VLM_ID, "description_language": "Vietnamese"},
        "image_processing_config": {"image_vector_enabled": False},
        "indexing_strategy": {
            "vector_enabled": True,
            "keyword_enabled": True,
            "wiki_enabled": False,
            "graph_enabled": True,
        },
        "extract_config": GRAPH_EXAMPLE,
    }


def create_knowledge_base(client, name):
    kb = client.request("POST", "/api/v1/knowledge-bases", knowledge_base_body(name))["data"]
    print(f"Tạo knowledge base '{name}': {kb['id']}")
    return kb["id"]


def ensure_knowledge_base(client, name):
    for kb in client.request("GET", "/api/v1/knowledge-bases")["data"]:
        if kb["name"] == name:
            print(f"Knowledge base '{name}' đã có: {kb['id']}")
            sync_chunking(client, kb["id"])
            return kb["id"]
    return create_knowledge_base(client, name)


def sync_chunking(client, kb_id):
    """Đưa cấu hình chunk của knowledge base đã có về CHUNKING, giữ nguyên cấu hình khác.

    Chỉ áp cho tài liệu nạp sau; tài liệu đã có phải nạp lại để chunk theo cấu hình mới.
    """
    kb = client.request("GET", f"/api/v1/knowledge-bases/{kb_id}")["data"]
    chunking = kb.get("chunking_config") or {}
    if all(chunking.get(k) == v for k, v in CHUNKING.items()):
        print("Cấu hình chunk đã đúng")
        return
    # PUT thay cả chunking_config; gửi lại cấu hình hiện có để không mất trường khác.
    client.request("PUT", f"/api/v1/knowledge-bases/{kb_id}", {
        "name": kb["name"], "description": kb.get("description", ""),
        "config": {"chunking_config": {**chunking, **CHUNKING}},
    })
    print(f"Đặt cấu hình chunk: {CHUNKING}")


def connect(env):
    """Đợi app sẵn sàng rồi trả về Client đã đăng nhập."""
    client = Client(env.get("WEKNORA_URL") or f"http://localhost:{env.get('APP_PORT', '8080')}")
    wait_healthy(client)
    login(client, env)
    return client


def main():
    env = load_env(ROOT / ".env")
    required = ["WEKNORA_ADMIN_USERNAME", "WEKNORA_ADMIN_EMAIL", "WEKNORA_ADMIN_PASSWORD",
                "PADDLEOCR_VL_ENDPOINT", "WEKNORA_KB_NAME"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        sys.exit(f"Thiếu biến trong .env: {', '.join(missing)}")

    try:
        client = connect(env)
        check_builtin_models(client)
        set_paddleocr_endpoint(client, env["PADDLEOCR_VL_ENDPOINT"])
        ensure_knowledge_base(client, env["WEKNORA_KB_NAME"])
    except APIError as err:
        sys.exit(f"Lỗi API: {err}")
    print("Xong.")


if __name__ == "__main__":
    main()
