# GRCh37 service replies captured live

Real responses from Ensembl's GRCh37 REST service, kept so a test answers in the shape the service
gives.

- `overlap_19_45411941.json`: `GET https://grch37.rest.ensembl.org/overlap/region/human/19:45411941-45411941?feature=variation`,
  the request `just_dna_enricher.grch37.recover_rsid("19", 45411941)` makes (enricher 0.8.6), captured
  2026-11-14. Two records start there: `rs429358` (APOE e4's defining SNP, `T/C`) and `CM900020`, an HGMD
  mutation record. The second is what makes "only rs-numbers come back" a test that could fail.
