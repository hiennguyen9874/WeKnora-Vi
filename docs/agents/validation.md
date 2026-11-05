# Validation

Acceptance for an issue is a run on the real stack, recorded in `docs/validation/issue-<N>.md`. `README.md` "Script E2E" documents the script's flags and output fields.

## Measuring

- The stack needs a filled `.env` and the three external services (LLM, embeder-gateway, OCR gateway). `./scripts/compose.sh ps` shows six healthy services before any run.
- Compare configurations on the same chunks: load once with `python3 scripts/e2e.py --keep-kb`, then measure each variant with `--reuse-kb`. OCR can split chunks differently between loads.
- Wait for background summaries to finish (the `embeddings` row count stops changing) before measuring; summaries add chunks to the index.
- Scores compare only across runs with the same question set, documents, models and chunking. The baseline is `results/baseline.json`; the 9-question seed tables in README are historical.
- The script exits 0 when chunk or NFC/NFD checks fail. Read `chunk_checks` and `unicode_equivalence` in the result JSON yourself.
- The Bộ kiểm tra keyword (`eval/keyword-set.json`) is user-approved. Propose question or answer changes to the user and wait for approval before editing it.
- Answer quality (Vietnamese, citations, refusing when no answer exists) is a manual check in the Web UI; there is no automated judge.
- Delete every temporary `e2e-*` knowledge base afterwards and confirm deletion (the API returns 404).

## Recording

Done when every item below exists for the issue:

- `docs/validation/issue-<N>.md`, in Vietnamese: status heading, measurement date and stack (image tag, ParadeDB version, models, chunking), acceptance checklist, Fork commit, red → green evidence, rerun commands, and limits of what was verified.
- Result JSON copied to `docs/validation/issue-<N>-*.json`. `results/` is gitignored apart from the baseline and chunker files listed in `.gitignore`.
- README section for the behaviour updated, linking the validation doc. ADR updated when the issue decides one.
- Comment on issue #N with commit links and results, then close it if acceptance passed. Summarise on #1 without closing it.
