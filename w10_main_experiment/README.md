# W10 main experiment

The six-sheet workbook and `w10_rankings_full.csv` contain Model A (kappa=10) and Model B for 2023, 2024, and 2025. The English report explains outcomes and limitations. All comparison CSVs and validation records are in this directory.

Each Year–Model–Topic grid retains all 36 target journals. Blank score/rank with `Undefined (N=0)` is not zero impact. Positive-score Top5 uses competition rank <=5 and includes cutoff ties. `N` is fractional mass; `C` is shared citation impact. Do not compare the numerical score scales of A and B.

## Reproduce locally

Use the bundled runtimes available on this host:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/vickey/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 "Round 2 experiment/w10_main_experiment/run_experiment.py"
PYTHONDONTWRITEBYTECODE=1 /Users/vickey/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 "Round 2 experiment/w10_main_experiment/run_tests.py"
/Users/vickey/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node "Round 2 experiment/w10_main_experiment/build_workbook.mjs"
PYTHONDONTWRITEBYTECODE=1 /Users/vickey/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 "Round 2 experiment/w10_main_experiment/verify_experiment.py"
```

Run these from the Journal Ranking project root. The local `node_modules` symlink points to the bundled runtime's packages. Scripts write only within this experiment directory; previous experiment results, original databases, and classification inputs are read only and hash-protected. These commands regenerate this experiment's own outputs.

`experiment_config.json`, `parameter_audit.json`, `run_manifest.json`, and `input_fingerprints.json` record parameters, inherited code, cache sources, data versions, and hashes. `validation_summary.json` independently checks citations, N/C, ranks, correlations, and all six sheets' typed data cells.

## Citation pool and historical prestige

The accepted pooled table has 106,423 unique pairs. Exactly 101,282 pairs fall in the union of the three requested evaluation windows. Annual counts are 58,415, 57,161, and 56,538; annual samples overlap. `citation_window_union_audit.json` records the 5,141 pooled pairs outside every requested window.

The original cached annual prestige is reused without recomputing PageRank or a network. Its historical boundary remains cited publication year >=2016. Only the topic-impact adapter uses the newly requested ten-year cited windows, including 2012–2015 where eligible. The inherited citation kernel is unchanged; citing-paper age controls half-life decay. Lag=2 denotes the cited-window endpoint, not an extra minimum age for every edge.

The 19 unresolved journal-years remain explicit limitations, never assumed true zero publication cells. Classification coverage and Abstract-based, Title-only, and Equal Fallback N/C components remain available for interpretation. No classification, API retrieval, or sensitivity branch is performed.
