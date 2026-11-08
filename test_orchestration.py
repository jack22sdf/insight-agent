import unittest
import pandas as pd
from orchestration import run_analysis

class OrchestrationTests(unittest.TestCase):
    def run_case(self, responses, **kw):
        self.calls = []
        def fake(role, payload):
            self.calls.append((role, payload))
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return run_analysis(pd.DataFrame({'d':['2026-01-01'], 'a':['10'], 'g':['A']}), 'd','a','g','分析', gateway_fn=fake, **kw)
    def test_repair(self):
        result = self.run_case([{'tools':['daily'],'goal':'趋势'}, 'draft', {'approved':False,'feedback':'修改'}, 'fixed', {'approved':True,'feedback':'通过'}])
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(len(self.calls), 5)
        self.assertNotIn('groups', self.calls[1][1]['evidence'])
    def test_rejection_bounded(self):
        result = self.run_case([{'tools':['quality'],'goal':'质量'}, 'draft', {'approved':False,'feedback':'修改'}, 'fixed', {'approved':False,'feedback':'仍错误'}])
        self.assertEqual(result['status'], 'needs_review')
        self.assertFalse(result['review']['approved'])
    def test_bad_plan(self):
        result = self.run_case([{'tools':['exec'],'goal':'hack'}])
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(result['metrics']['total'], '10')
    def test_provider_failure(self):
        result = self.run_case([RuntimeError('secret-key')])
        self.assertNotIn('secret-key', str(result))
    def test_offline(self):
        result = self.run_case([], offline=True)
        self.assertEqual(result['status'], 'degraded')
        self.assertEqual(self.calls, [])
    def test_invalid_review(self):
        result = self.run_case([{'tools':['daily'],'goal':'趋势'}, 'draft', {'approved':'true','feedback':'wrong type'}])
        self.assertEqual(result['status'], 'degraded')

if __name__ == '__main__': unittest.main()
