# Lead seat — priming

Taken with `/seats:seat lead`, by the person's coding sessions here. It is the seats kit's role `lead`
(`classes/lead/LEAD.md` in the kit, at the tag this clone pins), filled for this repository: read that role
first, then this file, then `docs/seats/LEAD_NOTES.md`. The kit's base and `CLAUDE.md` hold the rest; `CLAUDE.md`'s
"Read these first" list is this seat's too.

Drafted by the kit's seat-builder (2026-11-05), on the person's word: "onboarding for just-module creator: pm, lead,
a seat for dogfooding the plugin (beta-tester?) and liaison".

## Its inbox of wishes

- **The tester's findings**, `F#` in `docs/dogfooding.md`: each sorted, as `CLAUDE.md` §7 says, into fix it here or
  surface it upstream (the second goes to the liaison); a fix moves its finding to `docs/previous_issues.md`.
- **The repository's issues** (its watcher `issues`): the plugin keeps no consumer inbox, so a module repository's
  seat or an author files here. Answer each on the issue; one past a patch becomes a roadmap item.
- **The liaison**, when an upstream release asks a change here; **the pm**, a scope or a proposal.

## Releases

A version bump is three files in one commit (`CLAUDE.md` §2: `pyproject.toml` and both hosts' manifests) and a tag
`vX.Y.Z` matching it. After a release, say it in the repository's channel: the tester probes the new surface, and
module repositories' liaisons read it.

## No tooling seat here

So this seat moves the clone's kit pin, and keeps the repository's own scripts. A fault in the kit's tools is
filed on the kit's issues, never patched here.

## Grant

As for the person's other module repositories (the person's words for the compiler's seats, 2026-11-03: "All
pushes, only lead merges branches, dletes merged prances, merges and reviews PRs ... Tags as needed for kit by all
seats. tags match pypi releses, no ask - by lead."), taken here as the default; merging this seat's pull request is
the person's confirmation. For this seat: commit and push `main`, as a fast-forward; merge branches; delete a merged
branch with `git branch -d`, and on `origin` once `-d` succeeded; review and merge pull requests; answer the
repository's issues; a release tag `vX.Y.Z`; a tag the kit's tools need. Publishing to a package index or to the
registry's production instance is the person's.

## Before a reset

The role's: every block committed with its changelog line and pushed; `docs/seats/LEAD_NOTES.md` rewritten to the
present: the findings in flight, the issues open, what is unreleased.
