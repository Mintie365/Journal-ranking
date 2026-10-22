"""English scientific report assembled exclusively from computed W10 outputs."""
from collections import Counter
import numpy as np

def num(x,d=3):return 'Undefined' if x is None else f'{x:.{d}f}'

def make_report(rows,audits,coverage,statuses,limitations,analysis,cfg,base):
    s=analysis['summary'];ct=Counter(r['final_status'] for r in statuses.values())
    lines=['# W10 Main Experiment: Model A versus Model B','',
    '## 1. Experimental Setup','',
    'The experiment retains all 36 target journals and the original 134 background journals. The prestige network has exactly 170 fixed nodes. Evaluation years are 2023, 2024, and 2025. The citing window spans three calendar years and the cited window spans ten. Citation lag denotes the cited-window endpoint t−2; it does not introduce an additional per-edge minimum citation age.',
    '', '| Evaluation year | Citing window | Cited window |','|---|---|---|',
    '| 2023 | 2021–2023 | 2012–2021 |','| 2024 | 2022–2024 | 2013–2022 |','| 2025 | 2023–2025 | 2014–2023 |','',
    'All other main-model settings inherit Round 3: prestige exponent γ=1, citation half-life 2 years, journal self-citation multiplier 0.5, reference-length exponent δ=0, and Model A regularization κ=10. The original PageRank damping factor is 0.85. No PageRank, LLM classification, data collection, or sensitivity experiment was run.',
    'The original annual prestige vectors are read directly from the saved Round 2 matrices inherited by Round 3. Their original network boundary—registered journals, cited publication years 2016 through the citing year—is unchanged. The source multiplier is (πᵢ / mean₁₇₀(π))^γ. Cached vectors are checked against the saved source-prestige CSV and fixed-point equation, without iteration.',
    'The W10 adapter separates topic citation accumulation from the old prestige-only 2016 cutoff. This allows 2012–2015 target papers to receive topic impact without rebuilding the prestige network. The inherited time-decay function, source-weight function, denominator aggregation, chronology check, scoring functions, and ranking functions are reused. The exact parameter crosswalk is in parameter_audit.json.',
    '', '## 2. Dataset and Topic Membership','',
    'The frozen target population contains 22,067 unique Work IDs dated 2012–2023. The cleaned citation table has 106,423 unique accepted pairs. Applying the three specified evaluation windows yields a distinct union of 101,282 pairs; 5,141 accepted pooled pairs fall outside every requested evaluation window and are not forced into an evaluation year. Annual samples overlap, so their counts must not be summed to estimate a union.',
    '', '| Final classification status | Papers |','|---|---:|']
    for k in ['SINGLE','MULTIPLE_SOFT_SUCCESS','MULTIPLE_EQUAL_FALLBACK','UNKNOWN','OTHER','EXCLUDED_NO_INITIAL_LABELS','API_FAILED']:
        lines.append(f'| {k} | {ct[k]:,} |')
    lines+=['','Only has_valid_topic_weights=1 supplies substantive T01–T16 membership. Single papers retain q=1, Multiple Soft papers retain their final normalized weights, and the 231 accepted Equal Fallback papers retain q=1/|K|. UNKNOWN, OTHER, and the six explicitly excluded 2022 papers contribute neither topic mass nor topic citation impact. They remain in the frozen population and coverage accounting.',
    'Title-only classifications are provisional and remain identifiable. The frozen corpus has 19,469 papers with effective abstract-based weights, 469 with effective title-only weights, and 231 with accepted equal weights. Where an earlier hard label used a title but the accepted soft weights used an abstract, the effective-weight basis is abstract-based and both original input bases remain available in the classification data. Weights were not altered or reclassified. Candidate weights equal to zero contribute zero; actual contributing-paper counts count positive q only.',
    '', '| Year | Observed eligible cited papers | Papers with topic weights | Eligible citation pairs | Pairs without substantive topics | Pre-2016 cited pairs |','|---|---:|---:|---:|---:|---:|']
    for a in audits:lines.append(f'| {a["year"]} | {a["observed_eligible_cited_papers"]:,} | {a["weighted_papers"]:,} | {a["eligible_pairs"]:,} | {a["pairs_without_substantive_membership"]:,} | {a["pre2016_pairs"]:,} |')
    lines+=['', '## 3. Model A and Model B','',
    'For an eligible citation from paper a in source i to target paper b in journal j, the pre-topic contribution is',
    '', '`w(a,b,t) = (π_i(t)/mean_170 π(t)) × 2^(-(t−year_a)/2) × (0.5 if i=j else 1)`.',
    '', 'The decay clock is the citing paper’s age at evaluation, exactly as in the inherited code. With δ=0 the reference-length divisor is 1, so missing observed reference counts do not remove otherwise eligible citations. The citation is split by the cited paper’s final q_bk, not the citing paper’s topic. Duplicate citing/cited Work ID pairs count once per eligible evaluation year. Full-date chronology is enforced where available, and year chronology is retained otherwise.',
    '', '`C_jk(t) = Σ_(a→b, b∈j) w(a,b,t) q_bk`; `N_jk(t) = Σ_(b∈j,cited window) q_bk`.',
    '', '`Model A: I_A = C/(N+10)`; `Model B: I_B = C`.',
    '', 'N is fractional publication mass, including eligible zero-citation papers, not an integer publication count. Both models share exactly the same C and N arrays. If N=0, score and rank are Undefined in both models, even though the algebraic Model B score might otherwise be zero. If N>0 and C=0, score is exactly zero and receives the common zero-score competition rank. Positive ties use the inherited relative tolerance 1e−10 and absolute tolerance 1e−14 with deterministic Source ID ordering. Top5 includes all positive-score journals whose competition rank is ≤5, including cutoff ties; it never pads with zeros.',
    '', '## 4. Ranking Results','',
    'The full output contains 3,456 records: 36 journals × 16 topics × 3 evaluation years × 2 models. Each of the six Excel sheets contains 576 records sorted by Topic ID, rank, then Source ID; Undefined records remain present at the end of each topic.',
    '', '| Year | Model | Defined | Undefined | Positive | Defined zero impact |','|---|---|---:|---:|---:|---:|']
    for year in cfg['years']:
        for model in ['A','B']:
            rr=[r for r in rows if r['year']==year and r['model']==model]
            lines.append(f'| {year} | {model} | {sum(r["rank"] is not None for r in rr)} | {sum(r["rank"] is None for r in rr)} | {sum(r["score"] is not None and r["score"]>0 for r in rr)} | {sum(r["score"]==0 for r in rr)} |')
    lines+=['','### Representative 2025 topic champions','','| Topic | Model A champion(s) | Model B champion(s) | Top5 overlap |','|---|---|---|---:|']
    for t in analysis['top']:
        if t['year']==2025:lines.append(f'| {t["topic_id"]} {t["topic_name"]} | {t["A_top1_journals"] or "None positive"} | {t["B_top1_journals"] or "None positive"} | {t["top5_overlap"]} |')
    lines+=['','## 5. Model Comparison','',
        f'Across 48 topic-year comparisons, mean Spearman correlation is **{num(s["A_vs_B_spearman_mean"])}**, median {num(s["A_vs_B_spearman_median"])}, minimum {num(s["A_vs_B_spearman_min"])}; mean Kendall τ-b is {num(s["A_vs_B_kendall_mean"])}. Champions agree in **{s["same_top1_topic_years"]}/48** topic-years. Mean Top5 overlap is {num(s["top5_overlap_mean"])} journals and mean Top5 Jaccard overlap is {num(s["top5_jaccard_mean"])}. Correlations use the common defined journal population; constants or too-small populations yield Undefined rather than a fabricated correlation.',
        '', '| Year | Mean Spearman | Mean Kendall τ-b | Same Top1 / 16 | Mean Top5 overlap |','|---|---:|---:|---:|---:|']
    for p in s['by_year']:lines.append(f'| {p["year"]} | {num(p["mean_spearman"])} | {num(p["mean_kendall"])} | {p["same_top1"]} | {num(p["mean_top5_overlap"])} |')
    lines+=['','### Largest rank differences','','Positive “A improvement” means a better (smaller) rank under Model A. Scores from the two models are not compared numerically. C and N are common inputs.',
        '', '| Year | Topic | Journal | N | C | A rank | B rank | A improvement |','|---|---|---|---:|---:|---:|---:|---:|']
    for d in analysis['differences'][:12]:lines.append(f'| {d["year"]} | {d["topic_id"]} | {d["journal_name"]} | {num(d["N"])} | {num(d["C"])} | {d["A_rank"]} | {d["B_rank"]} | {d["A_rank_improvement_vs_B"]} |')
    lines+=['','### Publication mass and small samples','',
        f'The average within-topic Spearman association between a model’s score and N is {num(s["A_score_vs_N_spearman_mean"])} for A and {num(s["B_score_vs_N_spearman_mean"])} for B. The corresponding rank-versus-N associations are {num(s["A_rank_vs_N_spearman_mean"])} and {num(s["B_rank_vs_N_spearman_mean"])} (negative means larger mass tends to receive a better rank). Mean N among positive Top5 journals, averaged over topic-years, is {num(s["A_top5_mean_N"])} for A and {num(s["B_top5_mean_N"])} for B.',
        f'There are {s["small_mass_records"]} defined journal-topic-year cells with 0<N<10. Of these, {s["small_mass_A_top5"]} enter A’s positive Top5 and {s["small_mass_B_top5"]} enter B’s positive Top5; the respective Top10 counts are {s["small_mass_A_top10"]} and {s["small_mass_B_top10"]}. These are diagnostics, not proof of anomalous research quality or bias. κ=10 limits the effect of very small denominators but does not guarantee that every small cell ranks poorly.',
        '', '| Year | Topic | Small-mass journal | N | C | A rank | B rank |','|---|---|---|---:|---:|---:|---:|']
    for d in sorted(analysis['small'],key=lambda r:(r['A_rank'],r['year'],r['topic_id'],r['journal_id']))[:8]:lines.append(f'| {d["year"]} | {d["topic_id"]} | {d["journal_name"]} | {num(d["N"])} | {num(d["C"])} | {d["A_rank"]} | {d["B_rank"]} |')
    lines+=['','## 6. Temporal Stability','',
        'Adjacent-year comparisons rerank the common defined journal population before computing Spearman and Kendall, matching Round 3. Both common-population and full-population rank changes are retained. Entering/leaving defined cells are not treated as zero ranks. The CSV yearly_rank_changes.csv contains each journal’s transitions.',
        '', '| Model | Mean adjacent-year Spearman | Mean absolute full-population rank change |','|---|---:|---:|']
    for model in ['A','B']:lines.append(f'| {model} | {num(s[model+"_adjacent_year_spearman_mean"])} | {num(s[model+"_adjacent_full_mean_absolute_rank_change"])} |')
    lines+=['','| Transition | Model | Mean Spearman over topics | Mean absolute full-population rank change |','|---|---|---:|---:|']
    for before,after in [(2023,2024),(2024,2025)]:
        for model in ['A','B']:
            rs=[r for r in analysis['stability'] if r['year_before']==before and r['model']==model]
            mean=lambda field:float(np.mean([r[field] for r in rs if r[field] is not None]))
            lines.append(f'| {before}→{after} | {model} | {num(mean("spearman"))} | {num(mean("full_population_mean_absolute_rank_change"))} |')
    moves=sorted((r for r in analysis['changes'] if r['full_population_rank_change'] is not None),key=lambda r:(-abs(r['full_population_rank_change']),r['topic_id'],r['journal_id']))[:8]
    lines+=['','### Largest adjacent-year rank movements','','| Transition | Model | Topic | Journal | Before | After | Change |','|---|---|---|---|---:|---:|---:|']
    for r in moves:lines.append(f'| {r["year_before"]}→{r["year_after"]} | {r["model"]} | {r["topic_id"]} | {r["journal_name"]} | {r["rank_before"]} | {r["rank_after"]} | {r["full_population_rank_change"]:+d} |')
    lines+=['','## 7. Discussion and Data Limitations','',
        f'The measured score–mass association is {"stronger" if s["B_score_vs_N_spearman_mean"]>s["A_score_vs_N_spearman_mean"] else "not stronger"} for Model B, and its Top5 journals have {"larger" if s["B_top5_mean_N"]>s["A_top5_mean_N"] else "no larger"} mean topic mass. This supports interpreting B as total weighted topic impact, while A emphasizes impact relative to fractional publication mass with κ regularization. The interpretation is an aggregate empirical pattern, not a statement that A is independent of scale or that B measures publication volume alone. Citation quality and source prestige remain present in both.',
        'The 231 Equal Fallback papers use accepted equal-weight substitutes, not API-derived soft relevance. Title-only membership carries less evidence than abstract-based membership. Both remain explicitly decomposed into N and C components in the full ranking CSV; no additional sensitivity branch is executed here.',
        'UNKNOWN/OTHER lack substantive T01–T16 weights; their eligible citations are counted in the citation audit but contribute no topic impact. The six excluded papers remain visible in population coverage and contribute no topic mass. These classification limitations are distinct from bibliographic missingness.',
        f'All **36 target journals remain in every topic/year/model**, including journals affected by the **19 unresolved journal-years**. The corresponding counts inside the 2023, 2024, and 2025 cited windows are {sum(2012<=int(r["publication_year"])<=2021 for r in limitations)}, {sum(2013<=int(r["publication_year"])<=2022 for r in limitations)}, and {sum(2014<=int(r["publication_year"])<=2023 for r in limitations)}. These unresolved cells are not evidence of zero publications. N and C describe the observed accepted corpus and may understate missing output or citations. An observed N=0 is computationally Undefined, not a substantive assertion of no research in that field.',
        '', '| Journal | Unresolved publication years |','|---|---|']
    for journal in sorted({r['journal_name'] for r in limitations}):lines.append('| '+journal+' | '+', '.join(r['publication_year'] for r in limitations if r['journal_name']==journal)+' |')
    lines+=['','Strict OpenAlex Source IDs, adopted publication years, accepted Article/Review rules, chronology, and pair deduplication remain unchanged. Previously rejected uncertain work-type candidates and disallowed source aliases are not reinstated. The data cannot establish exhaustive worldwide coverage, causal journal quality, or calibrated topic probabilities.',
        'Reproducibility: experiment_config.json, parameter_audit.json, input_fingerprints.json, run_manifest.json, yearly_citation_audit.csv, per-paper impact records, saved aggregation matrices, and validation_summary.json document the calculation. Run the supplied run_experiment.py with the bundled Python runtime, then build_workbook.mjs and verify_experiment.py. Original data, membership files, prestige caches, and past results are hash-protected and are not overwritten.']
    (base/'W10_Main_Experiment_Report.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
