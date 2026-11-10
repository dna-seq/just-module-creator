# Reference examples, copied from just-dna-format

`hfe_hemochromatosis/` and `cyp2c19_star_alleles/` are just-dna-format's own reference examples, copied
unchanged from its tag `v0.8.3`, the release of the packages this plugin installs. The suite measures
`compare_modules`, the checks, `study_facts` and `record_override` on them.

They are copied rather than read from a sibling checkout because that checkout follows upstream's trunk:
on 2026-11-06 it re-derived these examples in the 0.8 format, and our installed 0.7 compiler refused the
new `resolution.csv` columns, failing five tests that had nothing to do with the change under test.

**When the `just-dna-format` floor in `pyproject.toml` moves to a new minor, copy them again** from the
tag of the release adopted:

    git -C ../just-dna-format archive vX.Y.Z reference_examples/hfe_hemochromatosis \
        reference_examples/cyp2c19_star_alleles | tar -x -C assets/
