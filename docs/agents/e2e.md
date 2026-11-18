# E2E script

Reference for `scripts/e2e.py`: what a run does, the Bộ kiểm tra keyword format and the result JSON. `--help` lists the flags.

## Runs

Needs the stack up and `scripts/setup.py` run. The script talks to the WeKnora HTTP API, plus `psql` for the BM25 tokenizer name and chunk breadcrumbs, which the API does not return.

```sh
python3 scripts/e2e.py                    # writes results/<timestamp>-<Fork commit>.json
python3 scripts/e2e.py --keep-kb          # keeps the knowledge base for the UI or a later --reuse-kb
python3 scripts/e2e.py --reuse-kb results/<--keep-kb run>.json --out results/<name>.json
```

`--reuse-kb` skips create and upload, runs the chunk checks and keyword set on the kept knowledge base, and never deletes it.

A run:

1. Creates knowledge base `e2e-<timestamp>` with the exact config of `scripts/setup.py`.
2. Uploads every document in `eval/documents.json` (three PDFs and one NFD TXT, with source and sha256) and waits until searchable (`finalizing`: summary and knowledge graph may still run in the background). The PDFs take about 5 minutes through the OCR gateway.
3. Checks child chunks, PASS/FAIL each:
   - `footnotes`: each paragraph in a document's `footnotes` sits whole in one chunk;
   - `dieu_headings`: each heading in `headings` (e.g. `Điều 4. Hiệu lực thi hành`) sits whole in one chunk;
   - `breadcrumbs`: for each `breadcrumbs` entry, a child chunk containing `text` has a `context_header` containing every string in `header`;
   - `nfc`: every chunk, parents included, is NFC.
4. Sends every keyword-set question to `hybrid-search` with `match_count` 10, `skip_context_enrichment` and threshold 0, in three modes: `keyword` (`disable_vector_match`), `vector` (`disable_keywords_match`), `hybrid`. Each question is also sent in its other Unicode form to compare the ordered top-10 IDs (90 pairs). Recall and MRR use the approved `form` only.
5. Deletes the knowledge base unless `--keep-kb`.

A non-zero exit means invalid inputs (NFD fixture turned NFC, malformed keyword set), an API error or a failed parse. Failed chunk or NFC/NFD checks still exit 0, so an unpatched Fork can record a baseline.

## Bộ kiểm tra keyword

`eval/keyword-set.json` holds 30 user-approved questions for #4 (26 answerable, 4 not, at least 2 per hard-case group). `eval/keyword-set-review.md` holds the approval, answers, source positions, an offline check and how to rerun the baseline on a separate unpatched stack. Changing a question or answer needs the user's approval first.

```json
{"questions": [
  {"id": "q05", "query": "Vàng miếng là gì?", "form": "nfd", "answerable": true,
   "expected": ["Vàng miếng là sản phẩm vàng được dập thành miếng"],
   "doc": "vbhn-117-2026-nd-nhnn", "tags": ["nfd", "dinh-nghia"]},
  {"id": "q10", "query": "...", "answerable": false, "tags": ["khong-co-dap-an"]}
]}
```

- `expected`: text snippets; a result containing any of them is a hit. Chunk IDs change on every load, so they are never used. Matching normalises both sides to NFC, strips `**` and collapses whitespace. Pick short snippets unique to the right place that cross no table cell or chunk boundary.
- `answerable: false`: no `expected`, excluded from scores; the result still records its top score per mode.
- `form`: `nfc` (default) or `nfd`; the script converts the query before sending. Unaccented questions are written unaccented in `query`.
- `doc` (an id in `eval/documents.json`) and `tags` are for reading results only.

## Baseline

`results/baseline.json`: unpatched Fork `fd7a2586fd58`, `chinese_lindera`, 1024-dim embedding. Recall@10 keyword/vector/hybrid 0.6154 / 0.7692 / 0.8077; NFC passes; footnote, Điều heading and breadcrumb checks fail (`eval/keyword-set-review.md`). The 9-question seed baseline lives at commit `72f03bd`, and the seed tables in `docs/validation/issue-7.md` and `issue-8.md` are historical; neither compares with the 30-question set.

## Result JSON

- `fork`, `tokenizer`, `models.embedding` (name, dimensions), `chunking`: the measured config; a comparison means something only when you know which of these changed.
- `documents`: parse status, seconds to searchable, child and parent chunk counts.
- `chunk_checks.<name>`: `pass`, items checked, failed items.
- `search.modes.<mode>`: `recall@k` (k = 1, 3, 5, 10) is the share of answerable questions whose first hit is in the top k; `mrr` averages 1/rank of the first hit (0 when missing from the top 10); `latency_ms` (p50, p95, mean) times the `hybrid-search` HTTP request in the `form` variant; `failed` lists misses.
- `unicode_equivalence`: `pass`, pairs checked, NFC/NFD pairs whose lists differ.
- `questions`: per question and mode, hit `rank` (`null` = miss), top score, top 3 results; `modes.<mode>.unicode_equivalence` keeps `nfc_ids` and `nfd_ids`.

## Chars per token

`scripts/measure_tokens.py --kb <kb_id>` sends each child chunk of a kept knowledge base to embeder-gateway (`EMBEDER_GATEWAY_URL`, or `--embedder-url` when that URL only resolves inside containers) and takes `usage.prompt_tokens` minus the 20 fixed prompt-format tokens, so it counts with the real `Qwen3-VL-Embedding-2B` tokenizer. Characters are code points, like the chunker's runes. It also rebuilds full text from chunk offsets to measure each Điều and probes the embedder's input limit. Writes `results/chars-per-token.json`; delete the `e2e-*` knowledge base afterwards.
