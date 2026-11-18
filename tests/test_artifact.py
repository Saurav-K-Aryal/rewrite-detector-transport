import tempfile,unittest
from artifact.audit import run,valid_length
from artifact.frozen_stats import exact_interval,paired_summary
from artifact.common import ROOT,read_json,read_rows

class EvidenceTests(unittest.TestCase):
    def test_protected_output_rejected_before_any_write(self):
        from artifact.common import safe_output
        for path in [ROOT, ROOT.parent, ROOT/'data', ROOT/'data/new', ROOT/'results', ROOT/'results/reference', ROOT/'artifact']:
            with self.assertRaises(ValueError):safe_output(path)
        self.assertEqual(safe_output(ROOT/'results/recomputed'),ROOT/'results/recomputed')
    def test_complete_offline_reference_reconciliation(self):
        with tempfile.TemporaryDirectory() as out:result=run(out,verify=True,plots=False)
        self.assertEqual(result['scores'],60900);self.assertEqual(result['interval_family'],357)
        self.assertEqual(result['primary_status'],'pending_independent_review_and_adjudication')
    def test_exact_zero_failure_interval_is_not_zero_width(self):
        lo,hi=exact_interval(0,500);self.assertEqual(lo,0);self.assertGreater(hi,0)
        self.assertAlmostEqual(hi,.01895135203877737)
    def test_parent_pairing_rejects_cross_question_join(self):
        with self.assertRaises(ValueError):paired_summary([{'qid':'a','id':'p'}],[{'qid':'b','parent_id':'p'}],[{'flag':1,'score':1.}],[{'flag':0,'score':0.}])
    def test_length_contract_has_both_boundaries(self):
        base={'done':True,'status':'completed','finish_reason':'stop'}
        self.assertFalse(valid_length(dict(base,word_count=99)));self.assertTrue(valid_length(dict(base,word_count=100)))
        self.assertTrue(valid_length(dict(base,word_count=128)));self.assertFalse(valid_length(dict(base,word_count=129)))
    def test_text_and_review_labels_are_not_exported(self):
        for row in read_rows('data/records.jsonl.gz'):
            self.assertFalse({'text','question','title','human_answer','reviewer_id','meaning_preserved'}&set(row))
        self.assertFalse(any('PRIVATE_KEY' in p.name or 'ANNOTATIONS_LOCKED' in p.name for p in ROOT.rglob('*')))
    def test_calibration_and_readme_scope(self):
        cal=read_json('data/radar_calibration_scores.json');self.assertEqual(sorted(cal['values'])[475],cal['threshold'])
        text=(ROOT/'README.md').read_text().lower()
        for word in ['saurav','aryal','howard','university']:self.assertNotIn(word,text)

if __name__=='__main__':unittest.main()
