# Fork patches

Every change to WeKnora behaviour is a commit in the Fork (`references/WeKnora`), then a submodule pin in the Repo triển khai. What the existing patches do: `fork-behaviour.md`.

## Steps

1. The submodule sits on a detached HEAD at the pinned commit. Run `git -C references/WeKnora switch main` and confirm `main` equals the pinned commit before editing.
2. Write the test first at the seam named in spec #1 "Testing Decisions", next to the existing tests for that area. Run it and watch it go **red**; keep the failure message for the validation doc.
3. Patch, then run the test **green**, plus the touched packages (`make test` covers the whole Fork).
4. Commit in the Fork with a lowercase Conventional Commit (`fix(chunker): ...`), push to `origin main`.
5. In the Repo triển khai, `git add references/WeKnora` and commit the pin with the docs and evidence for the issue (see `validation.md`). Push to `master`.

Done when both repos are pushed, the pin points at the pushed Fork commit, and `git -C references/WeKnora status` is clean.

## Syncing upstream

Merge `upstream/main` into the Fork's `main`; history stays append-only (merge commits, plain push). The last sync (#15) reached Tencent `7d064bc3a`; `docs/validation/issue-15.md` and `issue-14.md` are worked examples.

```sh
git -C references/WeKnora fetch upstream
git -C references/WeKnora switch main
git -C references/WeKnora merge --no-ff upstream/main
ls references/WeKnora/migrations/versioned | cut -c1-6 | sort | uniq -c | awk '$1>2'   # must print nothing
```

- golang-migrate refuses two migrations with the same number. Migrations already applied on the Fork database keep their identity; renumber the incoming upstream one to the next free number and update tests that reference the file name. That is why upstream's IM migration is `138` while the Fork's ICU migration stays `137`.
- `schema_migrations` stores a single version. A migration whose content changes under an already-applied number is **skipped** by the app. From Fork `137`, the current pin only needs `138` to run; leave the recorded version alone. The version adjustment in `issue-14.md` is history, not a recipe.
- After the merge: rebuild `./scripts/compose.sh up -d --build --no-deps app docreader frontend`, resync `config/prompt_templates/` (below), run E2E, then pin as in step 5.

## Images and reload

- `scripts/compose.sh` tags images with the Fork's short commit; uncommitted Fork changes add `-dirty`. Cite the tag of the image you measured; record final acceptance on a pushed, clean commit.
- Go change: `./scripts/compose.sh up -d --build --no-deps app`. Migrations run at app start only.
- `config/builtin_models.yaml`, `config/prompt_templates/` or `.env` change: `./scripts/compose.sh up -d --force-recreate app`, no build.
- `config/prompt_templates/` mounts over the whole image directory. After upgrading the Fork, resync it from the Fork, then reapply the Vietnamese `default_rewrite` examples.
- `./scripts/compose.sh down -v` deletes all data volumes.

## Known baseline failures

These fail on the unpatched Fork too; note them as unrelated rather than fixing them inside an issue:

- The MCP test in `internal/application/service/mcp_service_test.go` that resolves `example.com` (needs DNS).
- `TestPostgresMigrationsServeAgentHistory` in `internal/database` (downs the newest migration and waits for an index from `000106`).
