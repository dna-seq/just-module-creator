# STRchive's HTT record, for the repeat-band tests

`STRchive-loci.json` holds one locus, `HD_HTT`, taken from STRchive v2.26.0's catalogue
(`https://raw.githubusercontent.com/dashnowlab/STRchive/v2.26.0/data/STRchive-loci.json`, MIT licence,
the Dashnow lab), as the enricher's `strchive` lane built it on 2026-09-02.

**Trimmed, not edited.** Nine long free-text fields were dropped to keep the fixture small:
`disease_description`, `hpo_terms`, `prevalence_details`, `details`, `detection`, `mechanism_detail`,
`locus_tags`, `references`, `additional_literature`. Every field the drafter and `check_repeat_bands` read
(coordinates, motifs, `locus_structure`, the benign/intermediate/pathogenic bounds, `ref_copies`) is as
STRchive publishes it. There is no `release.json` beside it, so a run on this file names no release,
which is the honest answer for a loose file.

The suite uses it to show that `draft_from_strchive` reads the provisioned lane or a `catalogue` argument
(F129), and that `check_repeat_bands` takes a bare file.
