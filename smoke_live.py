"""Explicit, opt-in provider smoke test; uses only synthetic data."""
import json
import sys
from pathlib import Path
import pandas as pd
from orchestration import run_analysis

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    frame = pd.DataFrame({'date':['2026-10-01','2026-10-02','2026-10-02'],
                          'amount':['100.10','200.20','-10.10'],
                          'category':['直营','电商','电商']})
    outcome = run_analysis(frame, 'date','amount','category', '比较渠道净金额并提示数据限制')
    summary = {'status':outcome['status'], 'total':outcome['metrics']['total'],
               'review':outcome['review'], 'events':outcome['events']}
    Path('live_smoke_result.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if outcome['status'] in ('failed', 'degraded', 'offline'):
        raise SystemExit(1)
