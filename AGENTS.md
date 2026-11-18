# WeKnora tiếng Việt

Repo triển khai: deploys WeKnora for Q&A over Vietnamese documents, mostly legal/administrative. This repo holds config, overlays, scripts and evaluation only. Every WeKnora code change lives in the Fork `references/WeKnora`: PostgreSQL only, no feature flags (ADR 0003). `README.md` is the operator guide: build, use, upgrade; keep it short and put agent material in `docs/agents/`.

## Work

- Spec #1 is the map; its child issues are the work units. Delivering a child closes that child only: #1 stays open until every child is delivered.
- Code is the source of truth. When README, `.env.example` or a doc disagrees with Fork source, trust the source and fix the doc.
- Every acceptance claim carries evidence from a real run. When the stack or a service is unavailable, record the check as pending with the reason.
- Write README, `docs/` (except `docs/agents/`), issue comments and ADRs in Vietnamese; `AGENTS.md` and `docs/agents/` stay English. Write commit messages in English Conventional Commits, ending with `(#N)`.

## References

- `references/WeKnora`: the Fork. Remotes `origin` (Fork) and `upstream` (Tencent).
- `references/llm-wiki-rag`: `outputs/trien-khai-weknora-tieng-viet.md` is the deployment plan; `wiki/weknora-*.md` maps WeKnora internals. Read the relevant wiki page before exploring Fork source.
- `references/MonkeyOCRv2-B-Parsing-Gateway`: OCR gateway exposing the PaddleOCR-VL `/layout-parsing` API.
- `references/embeder-gateway`: serves the embedding and reranker models.

Each gateway has its own `AGENTS.md`; follow it when working inside that gateway.

## Agent docs

- **Fork patches**: changing WeKnora code, syncing upstream, pinning the Fork commit, rebuilding images. See `docs/agents/fork-patches.md`.
- **Fork behaviour**: what the Vietnamese patches and chosen settings do (models, prompts, OCR footnotes, NFC, BM25 tokenizer, chunker, chunk size) and why. See `docs/agents/fork-behaviour.md`.
- **Validation**: comparing retrieval or chunking configs, recording acceptance for an issue. See `docs/agents/validation.md`.
- **E2E script**: running `scripts/e2e.py`, reading its result JSON, editing the Bộ kiểm tra keyword. See `docs/agents/e2e.md`.
- **Issue tracker**: GitHub Issues via `gh`. See `docs/agents/issue-tracker.md`.
- **Triage labels**: default labels. See `docs/agents/triage-labels.md`.
- **Domain docs**: single-context layout, `GLOSSARY.md` and `docs/adr/`. See `docs/agents/domain.md`.
