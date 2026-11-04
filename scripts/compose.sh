#!/usr/bin/env bash
# Gọi docker compose với tag image là commit của Fork.
#   ./scripts/compose.sh up -d --build
# Fork có thay đổi chưa commit thì tag thêm hậu tố -dirty.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fork="$root/references/WeKnora"

if [[ ! -f "$fork/VERSION" ]]; then
  echo "Không thấy Fork ở $fork. Chạy: git submodule update --init references/WeKnora" >&2
  exit 1
fi
if [[ ! -f "$root/.env" ]]; then
  echo "Thiếu $root/.env. Copy từ .env.example rồi điền giá trị." >&2
  exit 1
fi

commit="$(git -C "$fork" rev-parse --short=12 HEAD)"
if [[ -n "$(git -C "$fork" status --porcelain)" ]]; then
  commit="$commit-dirty"
fi
export WEKNORA_FORK_COMMIT="$commit"
WEKNORA_FORK_VERSION="$(tr -d '[:space:]' < "$fork/VERSION")"
export WEKNORA_FORK_VERSION

exec docker compose --project-directory "$root" -f "$root/compose.yaml" "$@"
