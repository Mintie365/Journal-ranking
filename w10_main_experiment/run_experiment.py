"""Offline W10 main experiment, fixed cached prestige, final topic memberships."""
import csv, hashlib, importlib.util, inspect, json, math, sqlite3, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
OLD=ROOT/'Round 1 experiment'
SOFT=ROOT/'Round 2 experiment/soft_topic_classification'
DB=ROOT/'Round 2 experiment/process/results/w10_clean_recovered.sqlite'
FROZEN=ROOT/'Round 2 experiment/process/results/frozen_w10'
R3=OLD/'rank 3'
R2=OLD/'rank 2'
YEARS=[2023,2024,2025]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

core=module('round3_readonly_core',R3/'core.py')
sys.path.insert(0,str(R2))
legacy=module('round2_readonly_aggregation',R2/'model.py')
sys.path.pop(0)

def forbidden(*a,**k):raise RuntimeError('PageRank recomputation is prohibited')
legacy.prestige=forbidden;core.round2.prestige=forbidden;core.round2.round1.prestige=forbidden

def read(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def csvout(name,rows,fields=None):
    path=BASE/name;path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),extrasaction='ignore');w.writeheader();w.writerows(rows)

def save(name,value):
    (BASE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()

def ro(path):
    c=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;return c

def in_evaluation_window(edge,year,cfg):
    lo,hi=cfg['windows'][str(year)]['citing'];blo,bhi=cfg['windows'][str(year)]['cited']
    return lo<=edge['citing_year']<=hi and blo<=edge['cited_year']<=bhi

def base_citation_weight(edge,year,cfg):
    discount=cfg['rho'] if edge['citing_source_id']==edge['cited_source_id'] else 1.0
    return legacy.round1.temporal_weight(edge['citing_year'],year,cfg['half_life_years'])*discount/1.0

def config():
    c=core.configuration();c['kappas']=[10]
    c['windows']={str(y):{'citing':[y-2,y],'cited':[y-11,y-2]} for y in YEARS}
    c.update(cited_window_years=10,citing_window_years=3,citation_lag_years=2,
        topic_weight_method='frozen_final_soft_or_single_or_accepted_equal',
        models=['A','B'],network_nodes=170,target_journals=36,background_journals=134,
        prestige_policy='read_original_annual_cached_pi_only_no_network_rebuild',
        source_prestige_weight='(pi / mean_over_all_170_nodes) ** gamma',
        actual_topic_paper_count='positive_q_only_zero_memberships_contribute_no_mass',
        cited_window_policy='calendar bounds only; no new per-edge minimum-age constraint',
        page_rank_calls=0,new_llm_calls=0,new_external_api_calls=0)
    return c

def parameter_audit(cfg):
    r3=core.configuration();r2=json.loads((R2/'config.json').read_text())
    checks={k:cfg[k]==r3[k] for k in ['years','topics','gamma','delta','alpha','rho','half_life_years',
        'top_k_tie_policy','top_k_positive_scores_only','rank_tie_relative_tolerance','rank_tie_absolute_tolerance']}
    checks.update(rho_matches_inherited_impact=cfg['rho']==r2['self_citation_weight'],
        half_life_matches_inherited_impact=cfg['half_life_years']==r2['half_life_years'],
        citing_windows_unchanged=all(cfg['windows'][str(y)]['citing']==r3['windows'][str(y)]['citing'] for y in YEARS),
        only_A_kappa10_and_single_B=cfg['kappas']==[10] and cfg['models']==['A','B'])
    assert all(checks.values())
    save('parameter_audit.json',{'checks':checks,'intentional_changes':[
        'Cited windows expanded from four calendar years to ten as explicitly specified.',
        'Previously frozen final topic weights replace equal-membership labels.',
        'Latest accepted W10 paper/citation database is used.',
        'Only the requested main A(kappa=10) and B are evaluated; no sensitivity grids.'],
        'preserved_prestige_boundary':r2['prestige_boundary'],
        'decay_clock':'evaluation_year minus citing_publication_year; not cited-paper age',
        'reference_normalization':'delta=0: every valid citing paper has R**0=1, including absent reference counts',
        'W10_adapter_reason':'The inherited matrices_for_year nests topic accumulation behind prestige_cited_start=2016. '
            'Topic accumulation is separated from that prestige-only bound so 2012-2015 cited papers enter W10. '
            'No B/P/pi is rebuilt; cached historical prestige remains unchanged.',
        'reused_functions':{'citation_time_decay':str(OLD/'rank 1/model.py')+':temporal_weight',
            'prestige_weight':str(R2/'common.py')+':source_weights',
            'publication_mass':str(R2/'model.py')+':window_mass',
            'chronology':str(R2/'model.py')+':valid_chronology',
            'score_rank_top5':str(R3/'core.py')+':scores/rank_values/top_k/compare',
            'correlations':str(R3/'core.py')+':spearman/kendall_b'}})

def load(cfg):
    protected=[DB,FROZEN/'soft_topic_input_2012_2023.csv',FROZEN/'data_freeze_manifest.json',
        SOFT/'topic_membership_w10_final.csv',SOFT/'topic_classification_final_status.csv',SOFT/'final_validation_summary.json',
        SOFT/'taxonomy_snapshot.json',ROOT/'Round 2 experiment/process/results/remaining_unresolved_journal_years.csv',
        R2/'config.json',R2/'model.py',R2/'common.py',OLD/'rank 1/model.py',R2/'results/run_manifest.json',
        OLD/'journal selection/inputs/JR_target_36_journals.csv',
        R2/'results/source_prestige_by_year.csv',R3/'core.py',R3/'config.json',R3/'analysis.py',R3/'tests/test_round3.py']
    protected += [R2/'results/matrices'/f'model_{y}.npz' for y in YEARS]
    protected += [p for p in (R3/'results').rglob('*') if p.is_file()]
    hashes={str(p):sha(p) for p in protected}
    save('input_fingerprints.json',hashes)
    freeze=json.loads((FROZEN/'data_freeze_manifest.json').read_text())
    assert sha(DB)==freeze['source_database']['sha256_after']
    finalvalidation=json.loads((SOFT/'final_validation_summary.json').read_text());assert finalvalidation['all_checks_passed']
    for name in ['topic_membership_w10_final.csv','topic_classification_final_status.csv']:
        assert sha(SOFT/name)==finalvalidation['output_sha256'][name]
    statuses={r['work_id']:r for r in read(SOFT/'topic_classification_final_status.csv')}
    memberships=read(SOFT/'topic_membership_w10_final.csv');seen=set();labels=defaultdict(dict)
    for m in memberships:
        key=m['work_id'],m['topic_id'];assert key not in seen;seen.add(key)
        p=statuses[m['work_id']]
        assert m['journal_source_id']==p['journal_source_id'] and m['publication_year']==p['publication_year']
        if m['has_valid_topic_weights']=='1':
            q=float(m['topic_weight']);assert math.isfinite(q) and 0<=q<=1 and m['topic_id'] in cfg['topics']
            labels[m['work_id']][m['topic_id']]=q
        else: assert m['topic_weight']==''
    for w,p in statuses.items():
        if p['has_valid_topic_weights']=='1':assert w in labels and abs(sum(labels[w].values())-1)<1e-12
        else:assert w not in labels
    # Zero-valued candidate weights stay unchanged in the input; diagnostics count only positive membership.
    positive={w:{t:q for t,q in qs.items() if q>0} for w,qs in labels.items()}
    with ro(DB) as db:
        journals=[dict(r) for r in db.execute('select * from journal_selection order by source_id')]
        denominator=[dict(r) for r in db.execute('select work_id,source_id,publication_year,normalized_work_type work_type,publication_date from eligible_cited order by work_id')]
        works={r['work_id']:dict(r) for r in db.execute('select work_id,source_id,publication_year,publication_date,work_type,normalized_work_type,is_citing from works')}
        edges=[dict(r) for r in db.execute('select * from valid_w10_edges order by citing_work_id,cited_work_id')]
    assert len(denominator)==len(statuses)==22067 and {w['work_id'] for w in denominator}==set(statuses)
    assert len(edges)==len({(r['citing_work_id'],r['cited_work_id']) for r in edges})==106423
    union=[e for e in edges if any(y-2<=e['citing_year']<=y and y-11<=e['cited_year']<=y-2 for y in YEARS)]
    assert len(union)==101282
    save('citation_window_union_audit.json',{'accepted_pooled_pairs':len(edges),'three_requested_window_union_pairs':len(union),
        'outside_all_requested_windows':len(edges)-len(union),
        'outside_by_citing_and_cited_year':dict(Counter(f'{e["citing_year"]}->{e["cited_year"]}' for e in edges if not any(y-2<=e['citing_year']<=y and y-11<=e['cited_year']<=y-2 for y in YEARS)))})
    ids=[j['source_id'] for j in journals];assert len(ids)==len(set(ids))==170
    assert Counter(j['role'] for j in journals)=={'target':36,'background':134}
    targetids={j['source_id'] for j in journals if j['role']=='target'}
    targetlist=read(OLD/'journal selection/inputs/JR_target_36_journals.csv')
    assert targetids=={r['openalex_source_id'].split('/')[-1] for r in targetlist}
    manifest=json.loads((R2/'results/run_manifest.json').read_text());assert ids==manifest['fixed_network_journal_ids'] and targetids==set(manifest['target_ids'])
    for w in denominator:
        p=statuses[w['work_id']];assert w['source_id']==p['journal_source_id'] and w['publication_year']==int(p['publication_year'])
        assert w['source_id'] in targetids and w['work_type'] in ['article','review'] and 2012<=w['publication_year']<=2023
    for e in edges:
        a=works[e['citing_work_id']];b=works[e['cited_work_id']]
        assert e['validation_status']=='ACCEPTED' and a['source_id'] in ids and b['source_id'] in targetids
        assert e['citing_year']==a['publication_year'] and e['cited_year']==b['publication_year']
        assert e['citing_source_id']==a['source_id'] and e['cited_source_id']==b['source_id']
        assert a['is_citing']==1 and a['work_type'] in ['article','review'] and b['normalized_work_type'] in ['article','review']
        assert e['citing_work_type']==a['work_type'] and e['cited_work_type']==b['normalized_work_type']
        assert 2021<=e['citing_year']<=2025 and 2012<=e['cited_year']<=2023
        assert legacy.valid_chronology(a,b) and e['journal_self_citation']==int(a['source_id']==b['source_id'])
    return journals,denominator,works,edges,statuses,positive,hashes

def run():
    cfg=config();save('experiment_config.json',cfg);parameter_audit(cfg)
    print('Loading immutable inputs and checking hashes',flush=True)
    journals,denominator,works,edges,statuses,labels,hashes=load(cfg)
    ids=[j['source_id'] for j in journals];index={j:i for i,j in enumerate(ids)}
    targets=[i for i,j in enumerate(journals) if j['role']=='target'];targetids=[ids[i] for i in targets]
    topics={t:i for i,t in enumerate(cfg['topics'])}
    taxonomy=json.loads((SOFT/'taxonomy_snapshot.json').read_text())
    names={t['topic_id']:t['name_en'] for t in taxonomy['topics']}
    limitations=read(ROOT/'Round 2 experiment/process/results/remaining_unresolved_journal_years.csv');assert len(limitations)==19
    prestige_csv={(int(r['year']),r['journal_id']):r for r in read(R2/'results/source_prestige_by_year.csv')}
    output=[];auditrows=[];paperimpact=[];coverage=[];matrixinfo=[]
    npzdir=BASE/'matrices';npzdir.mkdir(exist_ok=True)
    for year in YEARS:
        lo,hi=cfg['windows'][str(year)]['citing'];blo,bhi=cfg['windows'][str(year)]['cited']
        with np.load(R2/'results/matrices'/f'model_{year}.npz') as cached:
            assert list(cached['journal_ids'])==ids
            pi=cached['pi'].copy();P=cached['P'].copy()
        assert len(pi)==170 and np.all(pi>0) and abs(pi.sum()-1)<1e-12
        residual=float(np.abs(pi-(cfg['alpha']*np.einsum('i,ij->j',pi,P,optimize=False)+(1-cfg['alpha'])/170)).sum())
        assert residual<1e-10;np.testing.assert_allclose(P.sum(axis=1),1,atol=1e-12)
        weights=legacy.source_weights(pi,cfg['gamma'])
        for i,sid in enumerate(ids):
            np.testing.assert_allclose(pi[i],float(prestige_csv[year,sid]['prestige']),rtol=0,atol=1e-16)
            np.testing.assert_allclose(weights[i],float(prestige_csv[year,sid]['gamma1_weight']),rtol=1e-14)
        N,actual,effective=legacy.window_mass(denominator,labels,index,topics,blo,bhi)
        A=np.zeros((16,170,170));selfA=np.zeros_like(A)
        bypaper=defaultdict(list);Nbybasis=defaultdict(lambda:np.zeros_like(N));Cbybasis=defaultdict(lambda:np.zeros_like(N))
        counts=Counter();fingerprint=hashlib.sha256();support=np.zeros_like(N,dtype=int)
        for e in edges:
            if not in_evaluation_window(e,year,cfg):continue
            counts['eligible_pairs']+=1;fingerprint.update((e['citing_work_id']+'|'+e['cited_work_id']+'\n').encode())
            i,j=index[e['citing_source_id']],index[e['cited_source_id']]
            # Exactly inherited Round 2 citation kernel; delta=0 gives denominator 1.
            weight=base_citation_weight(e,year,cfg)
            impact=weights[i]*weight;bypaper[e['cited_work_id']].append(impact)
            counts['self_pairs']+=i==j;counts['pre2016_pairs']+=e['cited_year']<2016
            qs=labels.get(e['cited_work_id'],{})
            if not qs:counts['pairs_without_substantive_membership']+=1
            else:counts['pairs_with_substantive_membership']+=1
            for t,q in qs.items():
                k=topics[t];A[k,i,j]+=weight*q;support[k,j]+=1
                if i==j:selfA[k,i,j]+=weight*q
                Cbybasis[statuses[e['cited_work_id']]['coverage_basis']][k,j]+=impact*q
        C=np.einsum('i,kij->kj',weights,A);selfC=np.einsum('i,kij->kj',weights,selfA)
        # Independent per-paper aggregation, without the topic citation matrix.
        checkN=np.zeros_like(N);checkC=np.zeros_like(N)
        yearpapers=[w for w in denominator if blo<=w['publication_year']<=bhi]
        for w in yearpapers:
            wid=w['work_id'];j=index[w['source_id']];impact=math.fsum(bypaper.get(wid,[]))
            qs=labels.get(wid,{})
            for t,q in qs.items():
                k=topics[t];checkN[k,j]+=q;checkC[k,j]+=impact*q
                Nbybasis[statuses[wid]['coverage_basis']][k,j]+=q
            paperimpact.append({'year':year,'work_id':wid,'journal_id':w['source_id'],'cited_year':w['publication_year'],
                'paper_weighted_citation_impact':impact,'citation_pairs':len(bypaper.get(wid,[])),
                'has_valid_topic_weights':int(wid in labels),'coverage_basis':statuses[wid]['coverage_basis']})
        np.testing.assert_allclose(N,checkN,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(C,checkC,rtol=2e-12,atol=2e-11)
        np.testing.assert_allclose(sum(Nbybasis.values()),N,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(sum(Cbybasis.values()),C,rtol=2e-12,atol=2e-11)
        assert abs(N.sum()-sum(w['work_id'] in labels for w in yearpapers))<1e-8
        assert abs(C.sum()-math.fsum(v for wid,vs in bypaper.items() if wid in labels for v in vs))<1e-7
        assert np.all(C[N==0]==0)
        perjournal=defaultdict(list)
        for w in yearpapers:perjournal[w['source_id']].append(statuses[w['work_id']])
        for j in targets:
            ps=perjournal[ids[j]];ct=Counter(p['coverage_basis'] for p in ps if p['has_valid_topic_weights']=='1')
            total=len(ps);valid=sum(ct.values())
            lim=[r for r in limitations if r['journal_id']==ids[j] and blo<=int(r['publication_year'])<=bhi]
            cov={'year':year,'journal_id':ids[j],'journal_name':journals[j]['journal_name'],'cited_window':f'{blo}-{bhi}',
                 'observed_eligible_papers':total,'valid_topic_weight_papers':valid,'valid_topic_weight_coverage':valid/total if total else None,
                 'abstract_based_papers':ct['ABSTRACT_BASED'],'title_only_papers':ct['TITLE_ONLY'],'equal_fallback_papers':ct['EQUAL_FALLBACK'],
                 'unknown_papers':sum(p['final_status']=='UNKNOWN' for p in ps),'other_papers':sum(p['final_status']=='OTHER' for p in ps),
                 'excluded_papers':sum(p['final_status']=='EXCLUDED_NO_INITIAL_LABELS' for p in ps),
                 'unresolved_journal_years_in_window':len(lim),'unresolved_years':';'.join(r['publication_year'] for r in lim)}
            coverage.append(cov)
        for k,t in enumerate(cfg['topics']):
            common=[]
            for j in targets:
                cov=next(r for r in coverage if r['year']==year and r['journal_id']==ids[j])
                common.append({'year':year,'topic_id':t,'topic_name':names[t],'journal_id':ids[j],'journal_name':journals[j]['journal_name'],
                    'weighted_citations':float(C[k,j]),'topic_publication_mass':float(N[k,j]),
                    'actual_topic_paper_count':int(actual[k,j]),'effective_sample_size':float(effective[k,j]) if N[k,j]>0 else None,
                    'citing_window':f'{lo}-{hi}','cited_window':f'{blo}-{bhi}',
                    'N_abstract_based':float(Nbybasis['ABSTRACT_BASED'][k,j]),'N_title_only':float(Nbybasis['TITLE_ONLY'][k,j]),
                    'N_equal_fallback':float(Nbybasis['EQUAL_FALLBACK'][k,j]),
                    'C_abstract_based':float(Cbybasis['ABSTRACT_BASED'][k,j]),'C_title_only':float(Cbybasis['TITLE_ONLY'][k,j]),
                    'C_equal_fallback':float(Cbybasis['EQUAL_FALLBACK'][k,j]),
                    'effective_topic_citation_pairs':int(support[k,j]),'self_weighted_citations':float(selfC[k,j]),
                    'journal_valid_topic_weight_coverage':cov['valid_topic_weight_coverage'],
                    'unresolved_journal_years_in_window':cov['unresolved_journal_years_in_window'],
                    'classification_coverage_flag':'HAS_UNRESOLVED_JOURNAL_YEAR' if cov['unresolved_journal_years_in_window'] else 'OBSERVED_CORPUS_ONLY',
                    'classification_input_basis_flags':';'.join(b for b,a in [('ABSTRACT_BASED',Nbybasis['ABSTRACT_BASED']),('TITLE_ONLY',Nbybasis['TITLE_ONLY']),('EQUAL_FALLBACK',Nbybasis['EQUAL_FALLBACK'])] if a[k,j]>0)})
            for model in ['A','B']:
                scores=core.scores([r['weighted_citations'] for r in common],[r['topic_publication_mass'] for r in common],model,10 if model=='A' else None)
                rank,_=core.rank_values(scores,targetids,cfg)
                for i,r in enumerate(common):
                    n=r['topic_publication_mass'];c=r['weighted_citations']
                    output.append({**r,'model':model,'kappa':10 if model=='A' else None,
                        'score':float(scores[i]) if n>0 else None,'rank':int(rank[i]) if n>0 else None,
                        'ranking_status':'Undefined (N=0)' if n==0 else 'Defined zero impact' if c==0 else 'Defined positive impact',
                        'small_sample_flag':n>0 and core.below_mass_threshold(n,10)})
        expected={2023:58415,2024:57161,2025:56538}[year];assert counts['eligible_pairs']==expected
        auditrows.append({'year':year,'citing_window':f'{lo}-{hi}','cited_window':f'{blo}-{bhi}',**dict(counts),
            'observed_eligible_cited_papers':len(yearpapers),'weighted_papers':sum(w['work_id'] in labels for w in yearpapers),
            'N_sum':float(N.sum()),'C_sum':float(C.sum()),'eligible_pair_sha256':fingerprint.hexdigest(),
            'cached_prestige_fixed_point_residual':residual,'prestige_nodes':170,'page_rank_recomputations':0})
        np.savez_compressed(npzdir/f'w10_aggregation_{year}.npz',journal_ids=np.array(ids),target_indices=np.array(targets),topic_ids=np.array(cfg['topics']),
            pi=pi,source_weights=weights,A=A,N=N,C=C,actual=actual,effective=effective)
        print('Computed',year,'pairs',counts['eligible_pairs'],'N',round(N.sum(),6),'C',round(C.sum(),6),flush=True)
    output.sort(key=lambda r:(r['year'],r['model'],r['topic_id'],r['rank'] if r['rank'] is not None else float('inf'),r['journal_id']))
    full=[{**r,'N':r['topic_publication_mass'],'C':r['weighted_citations']} for r in output]
    fields=['year','model','topic_id','topic_name','journal_id','journal_name','N','C','score','rank','ranking_status','kappa','citing_window','cited_window']+[k for k in output[0] if k not in ['weighted_citations','topic_publication_mass'] and k not in ['year','model','topic_id','topic_name','journal_id','journal_name','score','rank','ranking_status','kappa','citing_window','cited_window']]
    csvout('w10_rankings_full.csv',full,fields)
    save('workbook_rows.json',full)
    csvout('yearly_citation_audit.csv',auditrows);csvout('classification_coverage_by_journal_year.csv',coverage)
    csvout('citation_impact_by_paper_year.csv',paperimpact)
    csvout('data_limitations_19_journal_years.csv',limitations)
    from comparisons import analyze
    analysis=analyze(output,cfg,core,csvout,save)
    from report import make_report
    make_report(output,auditrows,coverage,statuses,limitations,analysis,cfg,BASE)
    assert len(output)==3456 and len({(r['year'],r['model'],r['topic_id'],r['journal_id']) for r in output})==3456
    assert hashes=={p:sha(p) for p in hashes}
    save('run_manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'config':cfg,
        'data_version':json.loads((FROZEN/'data_freeze_manifest.json').read_text())['data_version'],
        'input_sha256':hashes,'code_sha256':{p.name:sha(p) for p in BASE.glob('*.py')},
        'row_count':len(output),'records_per_year_model':576,'page_rank_calls':0,'llm_calls':0,'external_api_calls':0,
        'pooled_accepted_citation_pairs':106423,'three_window_union_pairs':101282,'topic_weighted_papers':len(labels),
        'runtime':{'python':sys.version,'numpy':np.__version__}})
    print('W10 main rankings and analyses saved:',BASE,flush=True)

if __name__=='__main__':run()
