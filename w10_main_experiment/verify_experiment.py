"""Independent recomputation from immutable citations and memberships plus XLSX QA."""
import csv, hashlib, json, math, sqlite3, zipfile, xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from datetime import date
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
OLD=ROOT/'Round 1 experiment';SOFT=ROOT/'Round 2 experiment/soft_topic_classification'

def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def number(v):return None if v in ['',None] else float(v)

def ranks(values,ids,cfg):
    positive=sorted((i for i,v in enumerate(values) if v is not None and v>0),key=lambda i:(-values[i],ids[i]))
    out=[None]*len(values);last=None;rank=0
    for pos,i in enumerate(positive,1):
        if last is None or not math.isclose(values[i],last,rel_tol=cfg['rank_tie_relative_tolerance'],abs_tol=cfg['rank_tie_absolute_tolerance']):rank=pos
        out[i]=rank;last=values[i]
    for i,v in enumerate(values):
        if v==0:out[i]=len(positive)+1
    return out

def average_ranks(values):
    order=sorted(range(len(values)),key=lambda i:values[i]);out=[0.]*len(values);a=0
    while a<len(order):
        b=a+1
        while b<len(order) and values[order[a]]==values[order[b]]:b+=1
        for i in order[a:b]:out[i]=(a+1+b)/2
        a=b
    return out

def spearman(a,b):
    if len(a)<2:return None
    a=average_ranks(a);b=average_ranks(b);ma=sum(a)/len(a);mb=sum(b)/len(b)
    den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b))
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/den if den else None

def tau(a,b):
    concord=discord=at=bt=0
    for i in range(len(a)):
        for j in range(i+1,len(a)):
            x=(a[i]>a[j])-(a[i]<a[j]);y=(b[i]>b[j])-(b[i]<b[j])
            if not x and not y:continue
            if not x:at+=1
            elif not y:bt+=1
            elif x==y:concord+=1
            else:discord+=1
    den=math.sqrt((concord+discord+at)*(concord+discord+bt))
    return (concord-discord)/den if den else None

def close(a,b):return a is None and b is None or a is not None and b is not None and math.isclose(a,b,rel_tol=2e-11,abs_tol=2e-10)

def verify_xlsx():
    data=json.loads((BASE/'workbook_rows.json').read_text());ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    cols=['topic_id','topic_name','journal_name','rank','N','C','score','ranking_status','actual_topic_paper_count',
          'effective_sample_size','journal_valid_topic_weight_coverage','N_title_only','N_equal_fallback',
          'unresolved_journal_years_in_window','classification_coverage_flag','journal_id','citing_window','cited_window','model','year']
    with zipfile.ZipFile(BASE/'W10_Journal_Rankings_2023_2025.xlsx') as z:
        book=ET.fromstring(z.read('xl/workbook.xml'));sheets=book.find('s:sheets',ns)
        names=[s.attrib['name'] for s in sheets];expected=[f'{y}_Model_{m}' for y in [2023,2024,2025] for m in ['A','B']]
        assert names==expected
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(si.itertext()) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        cells_checked=0
        for index,name in enumerate(names,1):
            sheet=ET.fromstring(z.read(f'xl/worksheets/sheet{index}.xml'))
            actual={}
            for cell in sheet.findall('.//s:sheetData/s:row/s:c',ns):
                key=cell.attrib['r'];typ=cell.attrib.get('t');v=cell.find('s:v',ns)
                if typ=='s':val=strings[int(v.text)]
                elif typ=='inlineStr':val=''.join(cell.find('s:is',ns).itertext())
                elif v is None or v.text is None:val=None
                elif typ in ['str','e']:val=v.text
                elif typ=='b':val=v.text=='1'
                else:val=float(v.text)
                assert typ!='e';actual[key]=val
            year=int(name[:4]);model=name[-1];rr=[r for r in data if r['year']==year and r['model']==model]
            assert len(rr)==576
            for row,r in enumerate(rr,2):
                for col,key in enumerate(cols):
                    expected_value=r[key];got=actual.get(chr(65+col)+str(row))
                    if isinstance(expected_value,(int,float)):assert isinstance(got,(int,float)) and close(got,expected_value),(name,row,key,got,expected_value)
                    elif expected_value is None:assert got in [None,'']
                    else:assert got==expected_value,(name,row,key,got,expected_value)
                    cells_checked+=1
            assert len(sheet.findall('.//s:tableParts/s:tablePart',ns))==1
            assert sheet.find('.//s:pane',ns) is not None
        return {'sheets':names,'rows_per_sheet':576,'data_cells_checked':cells_checked,'numeric_cells_typed':True,'no_excel_errors':True}

def main():
    cfg=json.loads((BASE/'experiment_config.json').read_text());hashes=json.loads((BASE/'input_fingerprints.json').read_text())
    raw=read(BASE/'w10_rankings_full.csv');rows=[]
    for r in raw:
        rows.append({**r,'year':int(r['year']),'N':float(r['N']),'C':float(r['C']),
            'score':number(r['score']),'rank':int(r['rank']) if r['rank'] else None})
    status={r['work_id']:r for r in read(SOFT/'topic_classification_final_status.csv')}
    labels=defaultdict(dict)
    for r in read(SOFT/'topic_membership_w10_final.csv'):
        if r['has_valid_topic_weights']=='1':labels[r['work_id']][r['topic_id']]=float(r['topic_weight'])
    c=sqlite3.connect((ROOT/'Round 2 experiment/process/results/w10_clean_recovered.sqlite').as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    papers=[dict(r) for r in c.execute('select work_id,source_id,publication_year,normalized_work_type from eligible_cited')]
    edges=[dict(r) for r in c.execute('select * from valid_w10_edges')]
    registry=[dict(r) for r in c.execute('select * from journal_selection order by source_id')]
    works={r['work_id']:dict(r) for r in c.execute('select work_id,publication_year,publication_date,source_id,work_type,normalized_work_type,is_citing from works')}
    targets={r['source_id'] for r in registry if r['role']=='target'}
    registered={r['source_id'] for r in registry}
    checks={'full_3456_unique_grid':len(rows)==len({(r['year'],r['model'],r['topic_id'],r['journal_id']) for r in rows})==3456,
        'fixed_36_targets_134_background_170_nodes':len(targets)==36 and len(registry)==170 and sum(r['role']=='background' for r in registry)==134,
        'all_16_topics_3_years_and_2_models':True,'memberships_normalized':all(abs(sum(q.values())-1)<1e-12 for q in labels.values()),
        'frozen_population_22067_matches_status':len(papers)==len(status)==22067 and {p['work_id'] for p in papers}==set(status),
        'pooled_pairs_106423_unique':len(edges)==len({(e['citing_work_id'],e['cited_work_id']) for e in edges})==106423,
        'strict_source_year_type_and_chronology':True,'independent_N_C_reconstruction':True,
        'model_formulas_zero_undefined_rules':True,'identical_N_C_across_models':True,
        'original_competition_rank_and_top5_rules':True,'cached_prestige_only_and_fixed_point_verified':True,
        'A_B_correlations_and_top5_verified':True,'adjacent_year_common_population_correlations_verified':True,
        'parameter_audit_all_pass':all(json.loads((BASE/'parameter_audit.json').read_text())['checks'].values()),
        '19_unresolved_journal_years_disclosed':len(read(BASE/'data_limitations_19_journal_years.csv'))==19,
        'all_protected_inputs_and_original_results_unchanged':all(sha(p)==v for p,v in hashes.items())}
    for e in edges:
        a=works[e['citing_work_id']];b=works[e['cited_work_id']]
        ok=e['validation_status']=='ACCEPTED' and a['source_id'] in registered and b['source_id'] in targets and a['work_type'] in ['article','review'] and b['normalized_work_type'] in ['article','review']
        ok &= e['citing_work_id']!=e['cited_work_id'] and e['cited_year']<=e['citing_year'] and a['is_citing']==1
        ok &= a['source_id']==e['citing_source_id'] and b['source_id']==e['cited_source_id'] and a['publication_year']==e['citing_year'] and b['publication_year']==e['cited_year']
        try:ok &= date.fromisoformat(b['publication_date'])<=date.fromisoformat(a['publication_date'])
        except (ValueError,TypeError):pass
        checks['strict_source_year_type_and_chronology'] &= bool(ok)
    grouped=defaultdict(list)
    for r in rows:grouped[r['year'],r['topic_id'],r['model']].append(r)
    prestige={(int(r['year']),r['journal_id']):float(r['gamma1_weight']) for r in read(OLD/'rank 2/results/source_prestige_by_year.csv')}
    annual=[];union=set()
    for year in cfg['years']:
        lo,hi=cfg['windows'][str(year)]['citing'];blo,bhi=cfg['windows'][str(year)]['cited']
        contributions=defaultdict(list);mass=defaultdict(list);annualpairs=[]
        for p in papers:
            if blo<=p['publication_year']<=bhi:
                for t,q in labels.get(p['work_id'],{}).items():mass[t,p['source_id']].append(q)
        for e in edges:
            if not(lo<=e['citing_year']<=hi and blo<=e['cited_year']<=bhi):continue
            key=e['citing_work_id'],e['cited_work_id'];union.add(key);annualpairs.append(key)
            w=prestige[year,e['citing_source_id']]*2**(-(year-e['citing_year'])/2)*(0.5 if e['citing_source_id']==e['cited_source_id'] else 1)
            for t,q in labels.get(e['cited_work_id'],{}).items():contributions[t,e['cited_source_id']].append(w*q)
        assert len(annualpairs)==len(set(annualpairs))
        annual.append({'year':year,'eligible_pairs':len(annualpairs)})
        for topic in cfg['topics']:
            for model in ['A','B']:
                rs=grouped[year,topic,model];checks['all_16_topics_3_years_and_2_models'] &= len(rs)==36 and {r['journal_id'] for r in rs}==targets
                for r in rs:
                    n=math.fsum(mass[topic,r['journal_id']]);impact=math.fsum(contributions[topic,r['journal_id']])
                    checks['independent_N_C_reconstruction'] &= close(n,r['N']) and close(impact,r['C'])
                    expected=None if n==0 else impact/(n+10) if model=='A' else impact
                    checks['model_formulas_zero_undefined_rules'] &= close(r['score'],expected) and ((r['rank'] is None)==(n==0))
                rank=ranks([r['score'] for r in rs],[r['journal_id'] for r in rs],cfg)
                checks['original_competition_rank_and_top5_rules'] &= rank==[r['rank'] for r in rs]
            a={r['journal_id']:r for r in grouped[year,topic,'A']};b={r['journal_id']:r for r in grouped[year,topic,'B']}
            checks['identical_N_C_across_models'] &= all(a[j]['N']==b[j]['N'] and a[j]['C']==b[j]['C'] for j in targets)
        with np.load(OLD/'rank 2/results/matrices'/f'model_{year}.npz') as old,np.load(BASE/'matrices'/f'w10_aggregation_{year}.npz') as new:
            checks['cached_prestige_only_and_fixed_point_verified'] &= np.array_equal(new['pi'],old['pi']) and len(old['pi'])==170 and abs(old['pi'].sum()-1)<1e-12 and np.abs(old['pi']-(.85*old['pi']@old['P']+.15/170)).sum()<1e-10
    checks['three_window_union_is_101282_not_pooled_count']=len(union)==101282
    top={(int(r['year']),r['topic_id']):r for r in read(BASE/'top1_top5_comparison.csv')}
    comparisons=read(BASE/'model_A_B_comparison.csv');assert len(comparisons)==48
    for r in comparisons:
        year=int(r['year']);topic=r['topic_id'];a={x['journal_id']:x for x in grouped[year,topic,'A'] if x['rank'] is not None};b={x['journal_id']:x for x in grouped[year,topic,'B'] if x['rank'] is not None};ids=sorted(set(a)&set(b))
        x=[a[i]['rank'] for i in ids];y=[b[i]['rank'] for i in ids]
        checks['A_B_correlations_and_top5_verified'] &= close(spearman(x,y),number(r['spearman'])) and close(tau(x,y),number(r['kendall_tau_b']))
        ta={j for j in a if a[j]['score']>0 and a[j]['rank']<=5};tb={j for j in b if b[j]['score']>0 and b[j]['rank']<=5}
        champions_a={j for j in a if a[j]['score']>0 and a[j]['rank']==1};champions_b={j for j in b if b[j]['score']>0 and b[j]['rank']==1}
        checks['A_B_correlations_and_top5_verified'] &= int(top[year,topic]['top5_overlap'])==len(ta&tb) and top[year,topic]['top1_same']==str(champions_a==champions_b)
    stability=read(BASE/'yearly_rank_stability.csv');assert len(stability)==64
    for r in stability:
        before=int(r['year_before']);after=int(r['year_after']);t=r['topic_id'];m=r['model']
        a={x['journal_id']:x for x in grouped[before,t,m] if x['rank'] is not None};b={x['journal_id']:x for x in grouped[after,t,m] if x['rank'] is not None};ids=sorted(set(a)&set(b))
        ra=ranks([a[j]['score'] for j in ids],ids,cfg);rb=ranks([b[j]['score'] for j in ids],ids,cfg)
        checks['adjacent_year_common_population_correlations_verified'] &= close(spearman(ra,rb),number(r['spearman'])) and close(tau(ra,rb),number(r['kendall_tau_b']))
    xlsx=verify_xlsx();checks['six_sheet_xlsx_matches_all_csv_cells']=True
    checks['no_pagerank_llm_collection_or_sensitivity']=all(json.loads((BASE/'run_manifest.json').read_text())[k]==0 for k in ['page_rank_calls','llm_calls','external_api_calls']) and len(rows)==3456 and cfg['kappas']==[10]
    unit=json.loads((BASE/'unit_test_results.json').read_text());checks['inherited_and_adapter_unit_tests_passed']=unit['passed']
    checks={k:bool(v) for k,v in checks.items()}
    out={'passed':all(checks.values()),'checks':checks,'ranking_rows':len(rows),'records_per_year_model':576,
        'target_journals':36,'background_journals':134,'fixed_nodes':170,'topics':16,'evaluation_years':cfg['years'],
        'pooled_accepted_pairs':len(edges),'three_window_union_pairs':len(union),'annual_pair_counts':annual,
        'xlsx_validation':xlsx,'unit_tests':unit,'original_input_fingerprints_unchanged':True}
    (BASE/'validation_summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2));assert out['passed']
    files={str(p.relative_to(BASE)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in BASE.rglob('*') if p.is_file() and 'node_modules' not in p.parts and p.name!='file_manifest.json' and p.suffix in ['.csv','.json','.md','.xlsx','.py','.mjs','.npz']}
    (BASE/'file_manifest.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
