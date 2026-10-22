import json,sys,unittest
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[1]
sys.dont_write_bytecode=True
loader=unittest.TestLoader()
suite=loader.discover(str(ROOT/'Round 1 experiment/rank 3/tests'),pattern='test_round3.py')
suite.addTests(loader.discover(str(BASE),pattern='test_adapter.py'))
result=unittest.TextTestRunner(verbosity=1).run(suite)
(BASE/'unit_test_results.json').write_text(json.dumps({'passed':result.wasSuccessful(),'tests_run':result.testsRun,
    'failures':len(result.failures),'errors':len(result.errors),'scope':'Inherited Round3 rules and W10 adapter boundary/kernel regressions'},indent=2)+'\n')
if not result.wasSuccessful():raise SystemExit(1)
