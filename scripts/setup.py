#!/usr/bin/env python3
"""Cấu hình WeKnora sau khi stack đã chạy. Chạy lại bao nhiêu lần cũng được.

- Đăng nhập tài khoản trong .env (chưa có thì đăng ký).
- Kiểm tra các model built-in từ config/builtin_models.yaml đã được nạp.
- Đặt endpoint PaddleOCR-VL ở tenant parser settings.
- Tạo knowledge base mẫu nếu chưa có knowledge base cùng tên.

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

    def request(self, method, path, body=None, timeout=60):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
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


def knowledge_base_body(name):
    return {
        "name": name,
        "description": "Văn bản pháp luật và hành chính tiếng Việt",
        "type": "document",
        "embedding_model_id": EMBEDDING_ID,
        "summary_model_id": LLM_ID,
        # Kích thước chunk để mặc định; ticket chunker sẽ chốt sau.
        "chunking_config": {
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


def ensure_knowledge_base(client, name):
    for kb in client.request("GET", "/api/v1/knowledge-bases")["data"]:
        if kb["name"] == name:
            print(f"Knowledge base '{name}' đã có: {kb['id']} (không sửa)")
            return
    kb = client.request("POST", "/api/v1/knowledge-bases", knowledge_base_body(name))["data"]
    print(f"Tạo knowledge base '{name}': {kb['id']}")


def main():
    env = load_env(ROOT / ".env")
    required = ["WEKNORA_ADMIN_USERNAME", "WEKNORA_ADMIN_EMAIL", "WEKNORA_ADMIN_PASSWORD",
                "PADDLEOCR_VL_ENDPOINT", "WEKNORA_KB_NAME"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        sys.exit(f"Thiếu biến trong .env: {', '.join(missing)}")

    client = Client(env.get("WEKNORA_URL") or f"http://localhost:{env.get('APP_PORT', '8080')}")
    wait_healthy(client)
    try:
        login(client, env)
        check_builtin_models(client)
        set_paddleocr_endpoint(client, env["PADDLEOCR_VL_ENDPOINT"])
        ensure_knowledge_base(client, env["WEKNORA_KB_NAME"])
    except APIError as err:
        sys.exit(f"Lỗi API: {err}")
    print("Xong.")


if __name__ == "__main__":
    main()
