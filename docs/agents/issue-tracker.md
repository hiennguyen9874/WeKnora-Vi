# Issue tracker: GitHub

Issues and specs live in this repository's GitHub Issues. Use the `gh` CLI.

- Create: `gh issue create --title "..." --body "..."` (use a heredoc for multiline bodies).
- Read: `gh issue view <number> --comments`; fetch labels as needed.
- List: `gh issue list --state open` with appropriate label and state filters.
- Comment: `gh issue comment <number> --body "..."`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

Infer the repository from the Git remote. Publishing to the issue tracker means
creating a GitHub issue; fetching a ticket means viewing its issue and comments.

## Pull requests as a triage surface

**PRs as a request surface: no.** Set to `yes` if external PRs should be
triaged as requests. When enabled, use `gh pr` to list, read, comment on,
label, and close PRs. GitHub shares issue and PR numbers; resolve the type
before acting.

## Wayfinding operations

A map is an issue labelled `wayfinder:map`. Link child tickets as GitHub
sub-issues; if unavailable, use a task list in the map and `Part of #<map>`
in each child. Label children `wayfinder:<type>`.

Represent blockers using GitHub issue dependencies; if unavailable, put
`Blocked by: #<n>, ...` in the child body. A ticket is unblocked when all
blockers are closed. Select the first open, unassigned, unblocked child in map
order. Claim it with `gh issue edit <n> --add-assignee @me`; resolve it by
commenting, closing it, and adding a context pointer to the map.
