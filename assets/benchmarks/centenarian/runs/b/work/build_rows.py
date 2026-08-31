"""Build variants.csv + studies.csv from the paper's Additional file 13 plus GRCh38 resolution."""
import csv, json, sys, collections

SCRATCH='/data/sources/just-module-creator/data/interim/repro-bench-2/run-centenarian-b/work/'
OUT='/data/sources/just-module-creator/data/interim/repro-bench-2/run-centenarian-b/longevity_centenarian/'
PMID='41057961'; TRAIT='OBA_VT0005372'; CUR='claude-opus-5'
COMP={'A':'T','T':'A','C':'G','G':'C'}
def rc(s): return ''.join(COMP.get(c,c) for c in reversed(s))

QSET="Among them, 4980 had non-synonymous variants, and 110 variants were observed to have deleterious effects."
QPRIOR="have been previously associated with longevity in earlier studies"
QRARE="suggesting these deleterious SNPs were not found to be common among the population"

PRIOR={'rs412051','rs9885916'}                                   # body: prior longevity association
RARE={'rs575564328','rs75029097','rs11228733','rs61849494','rs150316320','rs141207681'}  # body: MAF<1%

recs=json.load(open(SCRATCH+'del_snps.json'))
paper={}
for r in recs:
    d=r.get('dbsnp')
    if d and d!='None': paper[d]={'gene':r['gene'],'variant':r['variant'],
                                  'g37':f"{r['chrom']}:{r['pos']}",'novel':r['novel']}
paper.setdefault('rs412051',{'gene':'','variant':'','g37':'','novel':'No'})  # body-only

loci=collections.defaultdict(list); state={}; finds={}
for row in csv.DictReader(open(SCRATCH+'grch38_loci.tsv'), delimiter='\t'):
    rs=row['rsid'].strip()
    state[rs]=row.get('rsid_state','').strip()
    if row.get('findings'): finds[rs]=row['findings']
    c=row.get('chrom','').strip()
    if c and c not in ('UNRESOLVED','UNKNOWN'):
        loci[rs].append({'chrom':c,'start':row['start'].strip(),
                         'ref':row['ref'].strip().upper(),'alts':row['alts'].strip().upper()})
    else:
        loci[rs]  # touch

vrows=[]; srows=[]; report=[]
for rs in sorted(paper, key=lambda x:int(x[2:])):
    info=paper[rs]; L=loci.get(rs,[])
    if len(L)==0:
        report.append((rs,info['gene'],'DROPPED','no GRCh38 locus resolved ('+state.get(rs,'?')+')')); continue
    if len(L)>1:
        report.append((rs,info['gene'],'DROPPED','resolves to %d loci - paralogous/PAR, ambiguous'%len(L))); continue
    l=L[0]; ref=l['ref']; alts=[a for a in l['alts'].split(',') if a]
    if not ref or not alts:
        report.append((rs,info['gene'],'DROPPED','GRCh38 ref/alts incomplete')); continue
    # reconcile the paper's GRCh37 ref/alt against GRCh38
    agree='n/a'
    if info['variant'] and '/' in info['variant']:
        pr,pa=info['variant'].split('/')[:2]
        if pr==ref and pa in alts: agree='same-strand'
        elif rc(pr)==ref and rc(pa) in alts: agree='revcomp'
        elif pr==ref: agree='ref-only'
        else: agree='MISMATCH'
    # choose the alt: the paper's if identifiable, else the sole alt, else skip
    alt=None
    if info['variant'] and '/' in info['variant']:
        pa=info['variant'].split('/')[1]
        if pa in alts: alt=pa
        elif rc(pa) in alts: alt=rc(pa)
    if alt is None:
        if len(alts)==1: alt=alts[0]
        else:
            report.append((rs,info['gene'],'DROPPED','%d alts on GRCh38 and the paper allele matches none'%len(alts))); continue
    gene=info['gene']; cat='prior_longevity_association' if rs in PRIOR else 'cohort_shared_deleterious'
    het='/'.join(sorted({ref,alt})) if ref!=alt else ref
    hom=f'{alt}/{alt}'
    gtxt=f' in {gene}' if gene else ''
    if rs in PRIOR:
        tail=(f'The paper reports {rs} as previously associated with longevity in earlier work and '
              'observed in this cohort; it presents no association test of its own.')
    else:
        tail=('One of 110 coding variants predicted deleterious by SIFT and shared by all 21 individuals '
              'in the cohort.')
    lim=('Descriptive only: the study had no control group and tested no association between this '
         'variant and longevity.')
    for gt,zyg in ((het,'Heterozygous'),(hom,'Homozygous for the non-reference allele')):
        vrows.append({'rsid':rs,'genotype':gt,'state':'alt',
            'conclusion':f'{zyg} at {rs}{gtxt}. {tail} {lim}',
            'gene':gene,'phenotype':'exceptional longevity (observational cohort)','category':cat,
            'curator':CUR,'direction':'unknown','stat_significance':'unknown','trait_efo_id':TRAIT})
    q = QPRIOR if rs in PRIOR else (QRARE if rs in RARE else QSET)
    srows.append({'rsid':rs,'pmid':PMID,
        'population':'21 long-lived individuals aged 106-117 (13 female, 8 male; African, Caucasian and Asian ancestry); no control group',
        'conclusion':(f'{rs} observed among the coding variants shared by this cohort. '
                      + ('Reported by the authors as previously associated with longevity in earlier studies.' if rs in PRIOR
                         else ('SIFT-deleterious; population frequency below 1%.' if rs in RARE
                               else 'SIFT-deleterious.'))),
        'study_design':'observational cohort variant catalogue; no control group; no association testing',
        'stat_significance':'unknown','trait_efo_id':TRAIT,'provenance_quote':q,'curator':CUR})
    report.append((rs,gene,'KEPT',f'{agree}; GRCh37 {info["g37"]} {info["variant"]} -> GRCh38 {l["chrom"]}:{l["start"]} {ref}>{alt}'))

VC=["rsid","chrom","start","ref","alts","genotype","weight","state","conclusion","negatives","priority","gene","phenotype","category","clinvar","pathogenic","benign","curator","method","direction","stat_significance","effect_size","effect_measure","effect_allele","flags","trait_efo_id","clin_sig","requires_callable","acmg_sf","actionability","callable_from","quality_from","min_quality"]
SC=["rsid","chrom","start","ref","pmid","population","p_value","conclusion","study_design","stat_significance","effect_size","effect_measure","effect_allele","trait_efo_id","doi","provenance_quote","provenance_regex","curator","p_value_num"]
for path,cols,rows in ((OUT+'variants.csv',VC,vrows),(OUT+'studies.csv',SC,srows)):
    with open(path,'w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore'); w.writeheader()
        for r in rows: w.writerow({c:r.get(c,'') for c in cols})
kept=[r for r in report if r[2]=='KEPT']; dropped=[r for r in report if r[2]=='DROPPED']
print(f'variants.csv {len(vrows)} rows ({len(kept)} variants x 2 genotypes)')
print(f'studies.csv  {len(srows)} rows')
print(f'kept {len(kept)}  dropped {len(dropped)}')
print('\nagreement of paper GRCh37 alleles vs GRCh38:')
for k,v in collections.Counter(r[3].split(';')[0] for r in kept).most_common(): print(f'  {k}: {v}')
if dropped:
    print('\nDROPPED:')
    for r in dropped: print(' ',r[0],r[1],'-',r[3])
json.dump([{'rsid':r[0],'gene':r[1],'status':r[2],'note':r[3]} for r in report],
          open(SCRATCH+'build_report.json','w'),indent=1)
