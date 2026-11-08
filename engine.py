"""Auditable business analysis. LLMs explain; Python computes metrics."""
import json
import os
from decimal import Decimal, InvalidOperation, localcontext
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
if os.getenv('RAG_ENV_PATH'):
    load_dotenv(os.environ['RAG_ENV_PATH'])


def analyze(frame, date_col, amount_col, group_col):
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise ValueError('数据为空或不是表格')
    if not frame.columns.is_unique:
        raise ValueError('数据包含重复列名')
    selected = [date_col, amount_col, group_col]
    if len(set(selected)) != 3 or any(col not in frame.columns for col in selected):
        raise ValueError('请选择三个存在且不同的字段')
    if len(frame) > 1_000_000:
        raise ValueError('数据超过一百万行上限')
    # Parsing strings prevents integers from silently becoming nanosecond timestamps.
    dates = pd.to_datetime(frame[date_col].astype(str), format='mixed', errors='coerce', utc=True)
    if dates.isna().any():
        raise ValueError('日期列存在无效日期，请清洗后重试')
    amounts = []
    for value in frame[amount_col]:
        try:
            raw = str(value).strip()
            if len(raw) > 80:
                raise InvalidOperation
            amount = Decimal(raw)
            if not amount.is_finite():
                raise InvalidOperation
            if abs(amount) > Decimal('1e18') or amount.as_tuple().exponent < -8:
                raise ValueError('金额须在正负 1e18 内，且最多八位小数')
            amounts.append(amount)
        except InvalidOperation:
            raise ValueError('金额列存在空值或非数字，请清洗后重试') from None
    # Dedicated columns avoid collisions with arbitrary uploaded field names.
    data = pd.DataFrame({'day': dates.dt.strftime('%Y-%m-%d').to_numpy(),
                         'amount': amounts,
                         'group': frame[group_col].fillna('').astype(str).str.strip().replace('', '未分类').to_numpy()})
    # 18 integer + 8 fractional + 6 row-count digits fit comfortably in 40.
    with localcontext() as context:
        context.prec = 40
        total = sum(amounts, Decimal(0))
        groups = data.groupby('group')['amount'].sum().sort_values(ascending=False)
        daily = data.groupby('day')['amount'].sum()
        if sum(groups, Decimal(0)) != total or sum(daily, Decimal(0)) != total:
            raise ValueError('汇总一致性校验失败')
        mean = str(total / len(data))
    result = {'rows': len(data), 'total': str(total), 'mean_per_row': mean,
              'negative_rows': sum(a < 0 for a in amounts),
              'duplicate_rows': int(frame.duplicated().sum()),
              'daily': {str(k): str(v) for k, v in daily.items()},
              'groups': {str(k): str(v) for k, v in groups.items()},
              'checks': ['分组金额合计与总金额一致', '每日金额合计与总金额一致'],
              'semantics': '行数不等同于订单数；负值保留计入净额；重复行仅提示、不自动删除；日期统一为 UTC'}
    return result


def report(result, explanation, question):
    return '# Insight Agent 分析报告\n\n问题：' + question + '\n\n## 计算结果\n\n```json\n' + json.dumps(result, ensure_ascii=False, indent=2) + '\n```\n\n## 解读（模型输出需人工核查）\n\n' + explanation
