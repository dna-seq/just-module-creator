# run-centenarian-a — state as of MCP disconnect

Paper: PMID 41057961 / PMC12506250 / DOI 10.1186/s40246-025-00772-3
"Genetic signatures of exceptional longevity..." Human Genomics 2025;19:115. CC-BY-NC-ND.

## Established facts
- 21 individuals (3 centenarians + 18 supercentenarians). NO CONTROL GROUP. Paper's own words:
  "future studies on larger cohorts with appropriate controls"; "These results are preliminary".
- 110 deleterious SNPs / 79-80 genes in Supplementary File 13 (MOESM13, sheet "Del SNPs and ref").
  111 data rows; 64 carry an rsID; 47 have none; 16 flagged Novel.
- PAPER COORDINATES ARE GRCh37, NOT GRCh38. Verified on 5 rsIDs; offsets 0.1-5.6 Mb,
  rs61849494 also strand-flipped (paper G/A vs GRCh38 C/T).
  => author rsid-only rows; never paste the paper's chrom/start/ref/alt.
  => the 47 no-rsID variants are unusable without liftover: EXCLUDED, reported.
- Body names 8 rsIDs. rs412051 + rs9885916 are the only two the paper ties to longevity,
  and it does so by citing refs 29/30, not by its own test.
    ref 29 = Muntane 2018 Mol Biol Evol - PRIMATE phylogenetics, not human longevity assoc.
    ref 30 = Kiel PhD thesis 2014, cited via a WPS-Office cloud link (dead-ish).
  rs150316320 / rs141207681: frequency remark only, no longevity claim, absent from
    MOESM11 and MOESM13 => EXCLUDED (would be padding).
- Roster = 64 rsID-bearing deleterious SNPs + rs412051 = 65.
