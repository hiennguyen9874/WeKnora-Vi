# Validation

Acceptance for an issue is a run on the real stack, recorded in `docs/validation/issue-<N>.md`. Script internals, the keyword set format and result fields: `e2e.md`.

## Measuring

- The stack needs a filled `.env` and the three external services (LLM, embeder-gateway, OCR gateway). `./scripts/compose.sh ps` shows six healthy services before any run.
- Compare configurations on the same chunks: load once with `python3 scripts/e2e.py --keep-kb`, then measure each variant with `--reuse-kb`. OCR can split chunks differently between loads.
- Wait for background summaries to finish (the `embeddings` row count stops changing) before measuring; summaries add chunks to the index.
- Scores compare only across runs with the same question set, documents, models and chunking. The baseline is `results/baseline.json`.
- The script exits 0 when chunk or NFC/NFD checks fail. Read `chunk_checks` and `unicode_equivalence` in the result JSON yourself.
- The Bộ kiểm tra keyword (`eval/keyword-set.json`) is user-approved. Propose question or answer changes to the user and wait for approval before editing it.
- Database checks: after at least one upload, `./scripts/check-db.sh` prints `SHOW lc_ctype` and EXPLAIN of a 1024-dim vector query, rerun with `enable_seqscan = off` because the planner seq-scans small tables; the second plan must use `embeddings_embedding_idx_1024`.
- Answer quality (Vietnamese, citations, refusing when no answer exists) is a manual check in the Web UI; there is no automated judge.
- Delete every temporary `e2e-*` knowledge base afterwards and confirm deletion (the API returns 404).

## Deployment checks

No consolidated record yet; #13 records them alongside its own acceptance criteria, each with evidence from the deploy machine:

- [ ] Build the stack; six services healthy in `./scripts/compose.sh ps`.
- [ ] `python3 scripts/setup.py` twice in a row: no error, no duplicate knowledge base.
- [ ] System admin bootstrap done; "Test connection" passes for every model.
- [ ] Upload a scanned Vietnamese PDF: parsed through the OCR gateway with correct diacritics.
- [ ] Ask in the English Web UI: Vietnamese answer with citations.
- [ ] `./scripts/check-db.sh | tee docs/db-check.txt`: `lc_ctype` and EXPLAIN using HNSW 1024.

## Recording

Done when every item below exists for the issue:

- `docs/validation/issue-<N>.md`, in Vietnamese: status heading, measurement date and stack (image tag, ParadeDB version, models, chunking), acceptance checklist, Fork commit, red → green evidence, rerun commands, and limits of what was verified.
- Result JSON copied to `docs/validation/issue-<N>-*.json`. `results/` is gitignored apart from the baseline and chunker files listed in `.gitignore`.
- `docs/agents/fork-behaviour.md` updated for the behaviour, linking the validation doc; README only when an operator command or prerequisite changes. ADR updated when the issue decides one.
- Comment on issue #N with commit links and results, then close it if acceptance passed. Summarise on #1 without closing it.
