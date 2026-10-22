"""Comparisons on within-topic ranks; never compare the numerical A/B score scales."""
import json, math
from collections import defaultdict
import numpy as np

def analyze(rows,cfg,core,csvout,save):
    groups=defaultdict(list)
    for r in rows:groups[r['year'],r['topic_id'],r['model']].append(r)
    comparison=[];top=[];differences=[];small=[];stability=[];changes=[];massrelations=[]
    for year in cfg['years']:
        for topic in cfg['topics']:
            a=groups[year,topic,'A'];b=groups[year,topic,'B'];aa={r['journal_id']:r for r in a};bb={r['journal_id']:r for r in b}
            result=core.compare(a,b,cfg)
            related={}
            for model,rs in [('A',a),('B',b)]:
                defined=[r for r in rs if r['rank'] is not None]
                rho_score,n=core.spearman([r['score'] for r in defined],[r['topic_publication_mass'] for r in defined])
                rho_rank,_=core.spearman([r['rank'] for r in defined],[r['topic_publication_mass'] for r in defined])
                related.update({model+'_score_vs_N_spearman':rho_score,model+'_rank_vs_N_spearman':rho_rank})
                massrelations.append({'year':year,'topic_id':topic,'topic_name':a[0]['topic_name'],'model':model,
                    'defined_journals':n,'score_vs_N_spearman':rho_score,'rank_vs_N_spearman':rho_rank})
            comparison.append({'year':year,'topic_id':topic,'topic_name':a[0]['topic_name'],**result,**related})
            ta=core.top_k(a,5,cfg);tb=core.top_k(b,5,cfg)
            ca=core.champions(a);cb=core.champions(b)
            top.append({'year':year,'topic_id':topic,'topic_name':a[0]['topic_name'],
                'top1_same':{r['journal_id'] for r in ca}=={r['journal_id'] for r in cb},
                'A_top1_ids':';'.join(r['journal_id'] for r in ca),'A_top1_journals':';'.join(r['journal_name'] for r in ca),
                'B_top1_ids':';'.join(r['journal_id'] for r in cb),'B_top1_journals':';'.join(r['journal_name'] for r in cb),
                'A_top5_count':len(ta),'B_top5_count':len(tb),
                'top5_overlap':len({r['journal_id'] for r in ta}&{r['journal_id'] for r in tb}),
                'top5_jaccard':result['top5_jaccard'],'top5_overlap_over_smaller_set':result['top5_overlap_over_smaller_set'],
                'A_top5_journals':json.dumps([r['journal_name'] for r in ta],ensure_ascii=False),
                'B_top5_journals':json.dumps([r['journal_name'] for r in tb],ensure_ascii=False),
                'A_top5_mean_N':core.average([r['topic_publication_mass'] for r in ta]),
                'B_top5_mean_N':core.average([r['topic_publication_mass'] for r in tb])})
            for jid,ra in aa.items():
                rb=bb[jid];defined=ra['rank'] is not None
                d={'year':year,'topic_id':topic,'topic_name':ra['topic_name'],'journal_id':jid,'journal_name':ra['journal_name'],
                    'N':ra['topic_publication_mass'],'C':ra['weighted_citations'],'A_rank':ra['rank'],'B_rank':rb['rank'],
                    'A_minus_B_rank':ra['rank']-rb['rank'] if defined else None,
                    'A_rank_improvement_vs_B':rb['rank']-ra['rank'] if defined else None,
                    'absolute_rank_difference':abs(ra['rank']-rb['rank']) if defined else None,
                    'actual_topic_paper_count':ra['actual_topic_paper_count'],'effective_sample_size':ra['effective_sample_size'],
                    'N_title_only':ra['N_title_only'],'N_equal_fallback':ra['N_equal_fallback'],
                    'unresolved_journal_years_in_window':ra['unresolved_journal_years_in_window'],
                    'ranking_status':ra['ranking_status']}
                differences.append(d)
                if defined and core.below_mass_threshold(d['N'],10):
                    small.append({**d,'mass_bin':core.mass_bin(d['N']),
                        'A_positive_top5':ra['score']>0 and ra['rank']<=5,
                        'B_positive_top5':rb['score']>0 and rb['rank']<=5,
                        'A_positive_top10':ra['score']>0 and ra['rank']<=10,
                        'B_positive_top10':rb['score']>0 and rb['rank']<=10})
    for before,after in zip(cfg['years'],cfg['years'][1:]):
        for topic in cfg['topics']:
            for model in ['A','B']:
                first=groups[before,topic,model];last=groups[after,topic,model]
                result=core.compare(first,last,cfg)
                stability.append({'year_before':before,'year_after':after,'topic_id':topic,
                    'topic_name':first[0]['topic_name'],'model':model,**result})
                fa={r['journal_id']:r for r in first};la={r['journal_id']:r for r in last}
                common=sorted(j for j in fa if fa[j]['rank'] is not None and la[j]['rank'] is not None)
                if common:
                    r0,_=core.rank_values(np.array([fa[j]['score'] for j in common]),common,cfg)
                    r1,_=core.rank_values(np.array([la[j]['score'] for j in common]),common,cfg)
                    relative={j:(int(r0[i]),int(r1[i])) for i,j in enumerate(common)}
                else:relative={}
                for jid,r in fa.items():
                    b=la[jid];defined=jid in relative
                    changes.append({'year_before':before,'year_after':after,'model':model,'topic_id':topic,'journal_id':jid,
                        'journal_name':r['journal_name'],'rank_before':r['rank'],'rank_after':b['rank'],
                        'full_population_rank_change':b['rank']-r['rank'] if defined else None,
                        'common_population_rank_before':relative[jid][0] if defined else None,
                        'common_population_rank_after':relative[jid][1] if defined else None,
                        'common_population_rank_change':relative[jid][1]-relative[jid][0] if defined else None,
                        'N_before':r['topic_publication_mass'],'N_after':b['topic_publication_mass'],
                        'status_before':r['ranking_status'],'status_after':b['ranking_status']})
    differences.sort(key=lambda r:(-(r['absolute_rank_difference'] or 0),r['year'],r['topic_id'],r['journal_id']))
    small.sort(key=lambda r:(r['year'],r['A_rank'],r['topic_id'],r['journal_id']))
    for name,rs in [('model_A_B_comparison.csv',comparison),('top1_top5_comparison.csv',top),
                    ('rank_difference_analysis.csv',differences),('small_sample_diagnostics.csv',small),
                    ('yearly_rank_stability.csv',stability),('yearly_rank_changes.csv',changes),
                    ('score_rank_mass_correlations.csv',massrelations)]:
        csvout(name,rs)
    finite=lambda vs:[v for v in vs if v is not None and math.isfinite(v)]
    mean=lambda vs:float(np.mean(finite(vs))) if finite(vs) else None
    median=lambda vs:float(np.median(finite(vs))) if finite(vs) else None
    summary={'A_vs_B_spearman_mean':mean([r['spearman'] for r in comparison]),
        'A_vs_B_spearman_median':median([r['spearman'] for r in comparison]),
        'A_vs_B_spearman_min':min(finite([r['spearman'] for r in comparison])),
        'A_vs_B_kendall_mean':mean([r['kendall_tau_b'] for r in comparison]),
        'same_top1_topic_years':sum(r['top1_same'] for r in top),'topic_years':len(top),
        'top5_overlap_mean':mean([r['top5_overlap'] for r in top]),
        'top5_jaccard_mean':mean([r['top5_jaccard'] for r in top]),
        'A_top5_mean_N':mean([r['A_top5_mean_N'] for r in top]),
        'B_top5_mean_N':mean([r['B_top5_mean_N'] for r in top]),
        'small_mass_records':len(small),
        'small_mass_A_top5':sum(r['A_positive_top5'] for r in small),
        'small_mass_B_top5':sum(r['B_positive_top5'] for r in small),
        'small_mass_A_top10':sum(r['A_positive_top10'] for r in small),
        'small_mass_B_top10':sum(r['B_positive_top10'] for r in small)}
    for model in ['A','B']:
        summary[model+'_score_vs_N_spearman_mean']=mean([r['score_vs_N_spearman'] for r in massrelations if r['model']==model])
        summary[model+'_rank_vs_N_spearman_mean']=mean([r['rank_vs_N_spearman'] for r in massrelations if r['model']==model])
        summary[model+'_adjacent_year_spearman_mean']=mean([r['spearman'] for r in stability if r['model']==model])
        summary[model+'_adjacent_full_mean_absolute_rank_change']=mean([r['full_population_mean_absolute_rank_change'] for r in stability if r['model']==model])
    peryear=[]
    for year in cfg['years']:
        rs=[r for r in comparison if r['year']==year];tt=[r for r in top if r['year']==year]
        peryear.append({'year':year,'mean_spearman':mean([r['spearman'] for r in rs]),
            'mean_kendall':mean([r['kendall_tau_b'] for r in rs]),'same_top1':sum(r['top1_same'] for r in tt),
            'mean_top5_overlap':mean([r['top5_overlap'] for r in tt])})
    summary['by_year']=peryear
    save('analysis_summary.json',summary)
    return {'summary':summary,'comparison':comparison,'top':top,'differences':differences,'small':small,
            'stability':stability,'changes':changes,'massrelations':massrelations,'groups':groups}
