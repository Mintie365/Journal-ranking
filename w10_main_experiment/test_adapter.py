import unittest
import numpy as np
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('w10_adapter_under_test',Path(__file__).with_name('run_experiment.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class W10AdapterTests(unittest.TestCase):
    def test_historical_2012_citation_enters_w10_without_prestige_gate(self):
        cfg=m.config();e={'citing_year':2021,'cited_year':2012}
        self.assertTrue(m.in_evaluation_window(e,2023,cfg))
        self.assertFalse(m.in_evaluation_window({**e,'cited_year':2011},2023,cfg))
        self.assertFalse(m.in_evaluation_window(e,2024,cfg))

    def test_lag_is_endpoint_not_extra_per_edge_age_filter(self):
        self.assertTrue(m.in_evaluation_window({'citing_year':2021,'cited_year':2021},2023,m.config()))

    def test_decay_uses_citing_age_self_discount_and_no_reference_divisor(self):
        cfg=m.config();e={'citing_year':2021,'cited_year':2012,'citing_source_id':'A','cited_source_id':'B'}
        self.assertEqual(m.base_citation_weight(e,2023,cfg),.5)
        self.assertEqual(m.base_citation_weight({**e,'cited_year':2020},2023,cfg),.5)
        self.assertEqual(m.base_citation_weight({**e,'cited_source_id':'A'},2023,cfg),.25)
        self.assertEqual(m.base_citation_weight({**e,'citing_year':2023},2023,cfg),1)

    def test_mass_is_fractional_and_keeps_uncited_papers(self):
        papers=[{'work_id':'a','source_id':'J','publication_year':2012},
                {'work_id':'b','source_id':'J','publication_year':2021},
                {'work_id':'u','source_id':'J','publication_year':2021}]
        labels={'a':{'T01':.8,'T02':.2},'b':{'T01':1}}
        n,actual,effective=m.legacy.window_mass(papers,labels,{'J':0},{'T01':0,'T02':1},2012,2021)
        np.testing.assert_allclose(n[:,0],[1.8,.2]);np.testing.assert_array_equal(actual[:,0],[2,1])
        self.assertAlmostEqual(effective[0,0],1.8**2/(.8**2+1))

    def test_prestige_mean_retains_all_170_nodes(self):
        pi=np.arange(1,171,dtype=float);pi/=pi.sum()
        weights=m.legacy.source_weights(pi,1)
        np.testing.assert_allclose(weights,170*pi);self.assertAlmostEqual(float(weights.mean()),1)

if __name__=='__main__':unittest.main()
