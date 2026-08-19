# Choosing the table kind — moved

**This decision now lives in the `module-tables` skill.** Load it rather than reading a second copy
here; one copy per fact is what keeps the two from drifting.

| You want | Load |
|---|---|
| which table kind a finding belongs in, keyed on grain | `module-tables` |
| the axes that must go in a key, or the rows collide | `module-tables` |
| every column, key, signature and symptom of one table | `module-tables` → `references/<table>.md` — one dossier per CSV and parquet |
| where each file may sit, and what `derived/` is | `module-tables` → `references/LAYOUT.md` |

For a column's type, its vocabulary or whether it is required, ask `describe_table` /
`table_requirements` / `list_tables` — those answers are generated from the live models and cannot
drift from what the compiler accepts.
