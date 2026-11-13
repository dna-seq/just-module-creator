# Registry replies captured live

Real responses from the registry, kept so a test's stub answers in the shape the server gives
rather than one written from the model's docstring (F150 was a reader built on an invented shape).

- `rename_account_dry_run.json`: `RegistryClient.rename_account("sheep-dryrun", dry_run=True)` on the
  polygon (registry 0.30.0, format 0.8.4), 2026-11-13, by the saved rehearsal account `sheep`. A dry run
  changes nothing. The applied form could not be captured without renaming that account; the tests build it
  from this reply plus the fields `AccountRename` documents, and say so.
