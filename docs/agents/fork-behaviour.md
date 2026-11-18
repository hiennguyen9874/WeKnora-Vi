# Fork behaviour

What each Vietnamese patch in the Fork changes, the settings chosen on top of it, and the gotchas. Each section links its evidence in `docs/validation/`; the Fork source wins when this page disagrees with it.

## Models

`config/builtin_models.yaml` declares four models, read from `.env`. The app loads the file only at start.

- `builtin-llm` (KnowledgeQA) and `builtin-vlm` (VLLM) are the same LLM; a knowledge base accepts only a VLLM-type model for image description.
- `builtin-embedding`: `Qwen3-VL-Embedding-2B` at 1024 dimensions via dimension override (ADR 0001), `input_type_field: input_type`, `max_batch_size: 64`.
- `builtin-rerank`: `Qwen3-VL-Reranker-2B`, `score_scale: probability`, text only.
- "Test connection" needs a **system admin**: the account `scripts/setup.py` registers is only workspace owner until the bootstrap recreate (README "Dựng stack").

## Knowledge base config

`knowledge_base_body` and `CHUNKING` in `scripts/setup.py` are the source of truth, and `scripts/e2e.py` creates its knowledge bases with the same config. Rerunning setup on an existing knowledge base resets only the `CHUNKING` keys; to apply any other change, delete the knowledge base in the UI and rerun.

## Processing language and prompts (#5)

- The Fork maps `vi` and `vi-VN` to `Vietnamese` when injecting the Ngôn ngữ xử lý into prompts, and adds no UI locale. Keep `WEKNORA_LANGUAGE=vi-VN`, `DEFAULT_LOCALE=en-US`, `VITE_DEFAULT_LOCALE=en-US`.
- `config/prompt_templates/` is a full copy of the Fork's templates, mounted read-only over the **whole** `/app/config/prompt_templates`. The only edit: the Chinese examples in `default_rewrite` `content` (including the intent-classification guide) become Vietnamese. An unsynced mount hides new templates in the image; the resync is in `fork-patches.md` "Images and reload".
- Suggested questions from chunks appear only when `question_generation_config.enabled` is set before loading; setup leaves it off.
- Evidence: `docs/validation/issue-5.md`.

## OCR footnotes (#6)

- The PaddleOCR-VL request no longer drops the `footnote` label; header, footer, page number and aside are still dropped.
- Needs the OCR gateway's Footnote fix (gateway #19) in `two-stage` mode: the Fork label list cannot recover text an old gateway never returns.
- Evidence: `docs/validation/issue-6.md` (6/6 footnotes kept; q07, q25, q26 found by hybrid at ranks 6/1/1).

## Unicode NFC (#9)

- Every parser's output is normalised to NFC before chunking (parent and child chunks), as are manual text and passages. Queries are normalised at the hybrid-search entry (rerank branch included) and in the chat pipeline before rewrite, expansion or search.
- Citation positions still point into the original file; never use NFC offsets to open an NFD file.
- Already-loaded documents need reloading; there is no data migration.
- `fixtures/legal/hien-phap-2013-dieu-8-nfd.txt` is stored as real NFD and loaded by the text parser. Editors may silently convert it to NFC; `scripts/e2e.py` rejects the fixture if so.
- Evidence: `docs/validation/issue-9.md`. The TXT fixture changed the corpus, so score shifts against the three-PDF baseline are not attributable to NFC alone.

## BM25 tokenizer (#11, #12)

- `icu` without accent folding, chosen by ADR 0002: keyword R@10 0.8462 against 0.8077 for `chinese_lindera`, hybrid equal, no whitespace or punctuation tokens. Evidence: `docs/validation/issue-11.md`.
- Migration `000137_embeddings_bm25_icu` (named `000134` before the #14 sync) rebuilds the index over existing chunks at app start; no reload needed. Evidence: `docs/validation/issue-12.md`.
- Rollback to `chinese_lindera` is `goto 136` (README "Rollback tokenizer BM25"); `down 1` at the current pin only removes IM migration `138`. Migration `138` may refuse to roll back when multi-thread IM data violates the old unique index; leave the mappings intact.
- `scripts/bm25_tokenizers.py apply <candidate>` rebuilds `embeddings_search_idx` from `eval/bm25-tokenizer.sql` for experiments only (`schema_migrations` does not record it); `apply icu` restores the Fork index.

## Chunker: Vietnamese and chunk size (#7)

- Text with at least 10% Vietnamese-only letters (ă, đ, ơ, ư, ĩ, ũ and vowels U+1EA0..U+1EF9) is detected as `vi`. `vi` uses 2.5 chars/token, and when no separators are configured, defaults to `\n\n`, `\n`, `. `, `; `.
- 2.5 sits near p10 of the measured chars/token (mean 3.18), so tables and numbers are not undercounted. The chunker multiplies by 0.9 more: token limit 512 means a 1152-char ceiling.
- Chosen sizes (`CHUNKING`): parent 4096 holds a whole Điều except the two longest; child 384 (~120 tokens) is the only pair tried that was no worse than baseline on any vector or hybrid metric. Larger children raise R@10 but lower R@1 and MRR. Token limit 512 is a safety ceiling and cuts nothing at 384.
- Parents split at Điều boundaries and merge short consecutive Điều up to ~2048 chars (max 4096), so a parent never starts mid-Điều unless that Điều exceeds 4096.
- Measured on the 9-question seed set: rerun baseline and sizes on the 30-question set before arguing from new scores. Evidence: `docs/validation/issue-7.md`.

## Chunker: legal headings (#8)

Active only with strategy `auto`, `heading` or `heuristic`; an empty strategy is the legacy tier with no heading splits. Setup uses `auto`.

- `Phần`/`Chương`/`Mục` with a Roman or Arabic number, and `Điều N.` (including `Điều 11a.` and Roman numbers), are headings whether OCR returns `## ...` or a plain line. Levels: Phần > Chương > Mục > Điều; a quoted Điều (`“Điều 4. ...`, amended content) nests under the Điều amending it. An in-sentence reference (`Điều 37 của Thông tư ...`) is not a heading.
- With `languages: ["vi"]`, Khoản (`1.`, `2.`) is not a heading; other languages keep the `1. Title` pattern.
- Chương/Mục/Điều heading lines are never split, even when longer than a child chunk.
- An oversized section splits at its child headings first, then by separators.
- A child's breadcrumb (`context_header`) is the heading path at the child's start, located by position in the full text, even when the parent merges several Điều or the heuristic tier cuts a parent mid-Điều.
- Uppercase Vietnamese headings (`NHỮNG QUY ĐỊNH CHUNG`) enter the breadcrumb without `#`; one following a bare Phần/Chương/Mục number line joins that level's name.
- The heuristic tier recognises `Trang N` and `Trang N/M` footers.
- The post-review fixes (Roman Điều, uppercase breadcrumb, cross-parent context) passed Go tests but have no E2E run yet. Evidence: `docs/validation/issue-8.md`.
