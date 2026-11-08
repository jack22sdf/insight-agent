import unittest
import pandas as pd
from engine import analyze

class AnalysisTests(unittest.TestCase):
    def test_decimal_and_returns(self):
        frame = pd.DataFrame({'d':['2026-01-01']*3, 'a':['0.1','0.2','-0.1'], 'g':['A','B','A']})
        result = analyze(frame, 'd','a','g')
        self.assertEqual(result['total'], '0.2')
        self.assertEqual(result['negative_rows'], 1)
    def test_invalid_values(self):
        for date, amount in [('bad','1'), ('2026-01-01','NaN'), ('2026-01-01','Infinity')]:
            with self.assertRaises(ValueError):
                analyze(pd.DataFrame({'d':[date], 'a':[amount], 'g':['A']}), 'd','a','g')
    def test_missing_group(self):
        result = analyze(pd.DataFrame({'d':['2026-01-01'], 'a':['10'], 'g':[None]}), 'd','a','g')
        self.assertEqual(result['groups'], {'未分类':'10'})



class BoundaryTests(unittest.TestCase):
    def test_missing_and_reused_columns(self):
        f = pd.DataFrame({'d':['2026-01-01'], 'a':['1'], 'g':['A']})
        for fields in [('missing','a','g'), ('d','a','a')]:
            with self.assertRaises(ValueError):
                analyze(f, *fields)
    def test_duplicate_columns(self):
        with self.assertRaises(ValueError):
            analyze(pd.DataFrame([['2026-01-01', '1', 'A']], columns=['d','a','a']), 'd','a','g')
    def test_reserved_names_and_mixed_dates(self):
        f = pd.DataFrame({'_day':['2026-01-01', '2026-01-02T12:30:00+08:00'], '_amount':['0.1','0.2'], '_group':['X','Y']})
        r = analyze(f, '_day','_amount','_group')
        self.assertEqual(r['groups'], {'Y':'0.2','X':'0.1'})
        self.assertEqual(len(r['daily']), 2)
    def test_magnitude_and_precision_bounds(self):
        for value in ['1e100000', '0.000000001', '-1e19', 'x', '']:
            with self.assertRaises(ValueError):
                analyze(pd.DataFrame({'d':['2026-01-01'], 'a':[value], 'g':['A']}), 'd','a','g')
    def test_empty(self):
        with self.assertRaises(ValueError):
            analyze(pd.DataFrame(), 'd','a','g')
    def test_integer_date_rejected(self):
        with self.assertRaises(ValueError):
            analyze(pd.DataFrame({'d':[123], 'a':['1'], 'g':['A']}), 'd','a','g')

if __name__ == '__main__':
    unittest.main()
