# W10 Main Experiment: Model A versus Model B

## 1. Experimental Setup

The experiment retains all 36 target journals and the original 134 background journals. The prestige network has exactly 170 fixed nodes. Evaluation years are 2023, 2024, and 2025. The citing window spans three calendar years and the cited window spans ten. Citation lag denotes the cited-window endpoint t−2; it does not introduce an additional per-edge minimum citation age.

| Evaluation year | Citing window | Cited window |
|---|---|---|
| 2023 | 2021–2023 | 2012–2021 |
| 2024 | 2022–2024 | 2013–2022 |
| 2025 | 2023–2025 | 2014–2023 |

All other main-model settings inherit Round 3: prestige exponent γ=1, citation half-life 2 years, journal self-citation multiplier 0.5, reference-length exponent δ=0, and Model A regularization κ=10. The original PageRank damping factor is 0.85. No PageRank, LLM classification, data collection, or sensitivity experiment was run.
The original annual prestige vectors are read directly from the saved Round 2 matrices inherited by Round 3. Their original network boundary—registered journals, cited publication years 2016 through the citing year—is unchanged. The source multiplier is (πᵢ / mean₁₇₀(π))^γ. Cached vectors are checked against the saved source-prestige CSV and fixed-point equation, without iteration.
The W10 adapter separates topic citation accumulation from the old prestige-only 2016 cutoff. This allows 2012–2015 target papers to receive topic impact without rebuilding the prestige network. The inherited time-decay function, source-weight function, denominator aggregation, chronology check, scoring functions, and ranking functions are reused. The exact parameter crosswalk is in parameter_audit.json.

## 2. Dataset and Topic Membership

The frozen target population contains 22,067 unique Work IDs dated 2012–2023. The cleaned citation table has 106,423 unique accepted pairs. Applying the three specified evaluation windows yields a distinct union of 101,282 pairs; 5,141 accepted pooled pairs fall outside every requested evaluation window and are not forced into an evaluation year. Annual samples overlap, so their counts must not be summed to estimate a union.

| Final classification status | Papers |
|---|---:|
| SINGLE | 3,551 |
| MULTIPLE_SOFT_SUCCESS | 16,387 |
| MULTIPLE_EQUAL_FALLBACK | 231 |
| UNKNOWN | 513 |
| OTHER | 1,379 |
| EXCLUDED_NO_INITIAL_LABELS | 6 |
| API_FAILED | 0 |

Only has_valid_topic_weights=1 supplies substantive T01–T16 membership. Single papers retain q=1, Multiple Soft papers retain their final normalized weights, and the 231 accepted Equal Fallback papers retain q=1/|K|. UNKNOWN, OTHER, and the six explicitly excluded 2022 papers contribute neither topic mass nor topic citation impact. They remain in the frozen population and coverage accounting.
Title-only classifications are provisional and remain identifiable. The frozen corpus has 19,469 papers with effective abstract-based weights, 469 with effective title-only weights, and 231 with accepted equal weights. Where an earlier hard label used a title but the accepted soft weights used an abstract, the effective-weight basis is abstract-based and both original input bases remain available in the classification data. Weights were not altered or reclassified. Candidate weights equal to zero contribute zero; actual contributing-paper counts count positive q only.

| Year | Observed eligible cited papers | Papers with topic weights | Eligible citation pairs | Pairs without substantive topics | Pre-2016 cited pairs |
|---|---:|---:|---:|---:|---:|
| 2023 | 18,148 | 16,519 | 58,415 | 565 | 23,240 |
| 2024 | 18,641 | 16,945 | 57,161 | 524 | 16,520 |
| 2025 | 19,059 | 17,374 | 56,538 | 361 | 10,454 |

## 3. Model A and Model B

For an eligible citation from paper a in source i to target paper b in journal j, the pre-topic contribution is

`w(a,b,t) = (π_i(t)/mean_170 π(t)) × 2^(-(t−year_a)/2) × (0.5 if i=j else 1)`.

The decay clock is the citing paper’s age at evaluation, exactly as in the inherited code. With δ=0 the reference-length divisor is 1, so missing observed reference counts do not remove otherwise eligible citations. The citation is split by the cited paper’s final q_bk, not the citing paper’s topic. Duplicate citing/cited Work ID pairs count once per eligible evaluation year. Full-date chronology is enforced where available, and year chronology is retained otherwise.

`C_jk(t) = Σ_(a→b, b∈j) w(a,b,t) q_bk`; `N_jk(t) = Σ_(b∈j,cited window) q_bk`.

`Model A: I_A = C/(N+10)`; `Model B: I_B = C`.

N is fractional publication mass, including eligible zero-citation papers, not an integer publication count. Both models share exactly the same C and N arrays. If N=0, score and rank are Undefined in both models, even though the algebraic Model B score might otherwise be zero. If N>0 and C=0, score is exactly zero and receives the common zero-score competition rank. Positive ties use the inherited relative tolerance 1e−10 and absolute tolerance 1e−14 with deterministic Source ID ordering. Top5 includes all positive-score journals whose competition rank is ≤5, including cutoff ties; it never pads with zeros.

## 4. Ranking Results

The full output contains 3,456 records: 36 journals × 16 topics × 3 evaluation years × 2 models. Each of the six Excel sheets contains 576 records sorted by Topic ID, rank, then Source ID; Undefined records remain present at the end of each topic.

| Year | Model | Defined | Undefined | Positive | Defined zero impact |
|---|---|---:|---:|---:|---:|
| 2023 | A | 538 | 38 | 499 | 39 |
| 2023 | B | 538 | 38 | 499 | 39 |
| 2024 | A | 550 | 26 | 507 | 43 |
| 2024 | B | 550 | 26 | 507 | 43 |
| 2025 | A | 558 | 18 | 512 | 46 |
| 2025 | B | 558 | 18 | 512 | 46 |

### Representative 2025 topic champions

| Topic | Model A champion(s) | Model B champion(s) | Top5 overlap |
|---|---|---|---:|
| T01 Statistical inference and asymptotic theory | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 4 |
| T02 Bayesian statistics | ANNALS OF STATISTICS | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T03 Statistical computing and Monte Carlo | ANNALS OF STATISTICS | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T04 Regression and structured models | Annual Review of Statistics and Its Application | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 3 |
| T05 Nonparametric, semiparametric and robust statistics | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 4 |
| T06 Statistical learning and machine learning | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 4 |
| T07 High-dimensional statistics and sparsity | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 4 |
| T08 Multivariate, functional and structured data | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 4 |
| T09 Time series and stochastic dynamics | ANNALS OF STATISTICS | ANNALS OF STATISTICS | 3 |
| T10 Spatial and spatiotemporal statistics | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 3 |
| T11 Survival, event history and reliability | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T12 Causal inference and treatment effects | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T13 Experimental design and sequential studies | BIOMETRIKA | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T14 Survey sampling and official statistics | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | Journal of Survey Statistics and Methodology | 3 |
| T15 Applied statistics and quality methods | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | JOURNAL OF THE AMERICAN STATISTICAL ASSOCIATION | 4 |
| T16 Probability and stochastic process theory | ANNALS OF STATISTICS | BERNOULLI | 1 |

## 5. Model Comparison

Across 48 topic-year comparisons, mean Spearman correlation is **0.952**, median 0.968, minimum 0.693; mean Kendall τ-b is 0.850. Champions agree in **18/48** topic-years. Mean Top5 overlap is 3.521 journals and mean Top5 Jaccard overlap is 0.564. Correlations use the common defined journal population; constants or too-small populations yield Undefined rather than a fabricated correlation.

| Year | Mean Spearman | Mean Kendall τ-b | Same Top1 / 16 | Mean Top5 overlap |
|---|---:|---:|---:|---:|
| 2023 | 0.945 | 0.839 | 6 | 3.562 |
| 2024 | 0.954 | 0.852 | 4 | 3.438 |
| 2025 | 0.956 | 0.858 | 8 | 3.562 |

### Largest rank differences

Positive “A improvement” means a better (smaller) rank under Model A. Scores from the two models are not compared numerically. C and N are common inputs.

| Year | Topic | Journal | N | C | A rank | B rank | A improvement |
|---|---|---|---:|---:|---:|---:|---:|
| 2023 | T16 | Pakistan Journal of Statistics and Operation Research | 133.060 | 44.663 | 30 | 14 | -16 |
| 2023 | T16 | Brazilian Journal of Probability and Statistics | 128.521 | 85.589 | 23 | 7 | -16 |
| 2025 | T16 | Pakistan Journal of Statistics and Operation Research | 157.303 | 31.915 | 30 | 14 | -16 |
| 2023 | T16 | Journal of Statistical Theory and Applications | 118.842 | 40.438 | 29 | 15 | -14 |
| 2023 | T16 | Journal of Computational and Graphical Statistics | 2.633 | 15.657 | 14 | 28 | 14 |
| 2024 | T03 | Monte Carlo Methods and Applications | 142.506 | 29.490 | 32 | 18 | -14 |
| 2024 | T16 | Pakistan Journal of Statistics and Operation Research | 145.257 | 25.976 | 30 | 17 | -13 |
| 2024 | T16 | Brazilian Journal of Probability and Statistics | 133.108 | 102.770 | 19 | 6 | -13 |
| 2025 | T14 | Journal of Survey Statistics and Methodology | 278.435 | 296.893 | 14 | 1 | -13 |
| 2025 | T16 | Journal of Statistical Theory and Applications | 116.135 | 24.852 | 29 | 16 | -13 |
| 2025 | T16 | Journal of Computational and Graphical Statistics | 3.293 | 17.982 | 11 | 24 | 13 |
| 2023 | T03 | Monte Carlo Methods and Applications | 137.954 | 39.635 | 29 | 17 | -12 |

### Publication mass and small samples

The average within-topic Spearman association between a model’s score and N is 0.579 for A and 0.746 for B. The corresponding rank-versus-N associations are -0.579 and -0.746 (negative means larger mass tends to receive a better rank). Mean N among positive Top5 journals, averaged over topic-years, is 57.334 for A and 90.868 for B.
There are 661 defined journal-topic-year cells with 0<N<10. Of these, 32 enter A’s positive Top5 and 4 enter B’s positive Top5; the respective Top10 counts are 85 and 51. These are diagnostics, not proof of anomalous research quality or bias. κ=10 limits the effect of very small denominators but does not guarantee that every small cell ranks poorly.

| Year | Topic | Small-mass journal | N | C | A rank | B rank |
|---|---|---|---:|---:|---:|---:|
| 2025 | T04 | Annual Review of Statistics and Its Application | 6.510 | 224.444 | 1 | 8 |
| 2025 | T14 | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | 6.591 | 99.728 | 1 | 5 |
| 2023 | T16 | Statistics Surveys | 1.751 | 63.642 | 2 | 9 |
| 2024 | T04 | Annual Review of Statistics and Its Application | 6.858 | 185.203 | 2 | 8 |
| 2024 | T16 | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | 5.116 | 91.514 | 2 | 8 |
| 2025 | T16 | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | 7.702 | 99.597 | 2 | 7 |
| 2023 | T04 | Annual Review of Statistics and Its Application | 6.858 | 170.247 | 3 | 10 |
| 2023 | T06 | JOURNAL OF THE ROYAL STATISTICAL SOCIETY SERIES B-STATISTICAL METHODOLOGY | 7.976 | 154.904 | 3 | 6 |

## 6. Temporal Stability

Adjacent-year comparisons rerank the common defined journal population before computing Spearman and Kendall, matching Round 3. Both common-population and full-population rank changes are retained. Entering/leaving defined cells are not treated as zero ranks. The CSV yearly_rank_changes.csv contains each journal’s transitions.

| Model | Mean adjacent-year Spearman | Mean absolute full-population rank change |
|---|---:|---:|
| A | 0.969 | 1.494 |
| B | 0.973 | 1.334 |

| Transition | Model | Mean Spearman over topics | Mean absolute full-population rank change |
|---|---|---:|---:|
| 2023→2024 | A | 0.970 | 1.517 |
| 2023→2024 | B | 0.973 | 1.355 |
| 2024→2025 | A | 0.967 | 1.472 |
| 2024→2025 | B | 0.972 | 1.314 |

### Largest adjacent-year rank movements

| Transition | Model | Topic | Journal | Before | After | Change |
|---|---|---|---|---:|---:|---:|
| 2024→2025 | A | T15 | Statistics Surveys | 7 | 29 | +22 |
| 2024→2025 | B | T15 | Statistics Surveys | 9 | 29 | +20 |
| 2024→2025 | A | T02 | Dependence Modeling | 35 | 20 | -15 |
| 2024→2025 | B | T15 | Hacettepe Journal of Mathematics and Statistics | 27 | 13 | -14 |
| 2023→2024 | A | T02 | Statistics Surveys | 11 | 24 | +13 |
| 2024→2025 | A | T15 | Hacettepe Journal of Mathematics and Statistics | 27 | 14 | -13 |
| 2023→2024 | A | T10 | JOURNAL OF TIME SERIES ANALYSIS | 5 | 17 | +12 |
| 2024→2025 | A | T15 | Wiley Interdisciplinary Reviews-Computational Statistics | 19 | 7 | -12 |

## 7. Discussion and Data Limitations

The measured score–mass association is stronger for Model B, and its Top5 journals have larger mean topic mass. This supports interpreting B as total weighted topic impact, while A emphasizes impact relative to fractional publication mass with κ regularization. The interpretation is an aggregate empirical pattern, not a statement that A is independent of scale or that B measures publication volume alone. Citation quality and source prestige remain present in both.
The 231 Equal Fallback papers use accepted equal-weight substitutes, not API-derived soft relevance. Title-only membership carries less evidence than abstract-based membership. Both remain explicitly decomposed into N and C components in the full ranking CSV; no additional sensitivity branch is executed here.
UNKNOWN/OTHER lack substantive T01–T16 weights; their eligible citations are counted in the citation audit but contribute no topic impact. The six excluded papers remain visible in population coverage and contribute no topic mass. These classification limitations are distinct from bibliographic missingness.
All **36 target journals remain in every topic/year/model**, including journals affected by the **19 unresolved journal-years**. The corresponding counts inside the 2023, 2024, and 2025 cited windows are 19, 15, and 12. These unresolved cells are not evidence of zero publications. N and C describe the observed accepted corpus and may understate missing output or citations. An observed N=0 is computationally Undefined, not a substantive assertion of no research in that field.

| Journal | Unresolved publication years |
|---|---|
| Austrian Journal of Statistics | 2012, 2013 |
| Chilean Journal of Statistics | 2012, 2013, 2014, 2016, 2018, 2019 |
| Journal of Statistical Theory and Applications | 2012 |
| REVSTAT-Statistical Journal | 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2021 |
| SOUTH AFRICAN STATISTICAL JOURNAL | 2017 |

Strict OpenAlex Source IDs, adopted publication years, accepted Article/Review rules, chronology, and pair deduplication remain unchanged. Previously rejected uncertain work-type candidates and disallowed source aliases are not reinstated. The data cannot establish exhaustive worldwide coverage, causal journal quality, or calibrated topic probabilities.
Reproducibility: experiment_config.json, parameter_audit.json, input_fingerprints.json, run_manifest.json, yearly_citation_audit.csv, per-paper impact records, saved aggregation matrices, and validation_summary.json document the calculation. Run the supplied run_experiment.py with the bundled Python runtime, then build_workbook.mjs and verify_experiment.py. Original data, membership files, prestige caches, and past results are hash-protected and are not overwritten.
