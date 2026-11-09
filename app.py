import hashlib
import csv
import io
import json
import os
import pandas as pd
import streamlit as st
from contextlib import nullcontext
from access_control import online_access
from engine import report
from orchestration import run_analysis

st.set_page_config(page_title='Insight Agent · 经营分析', page_icon='◈', layout='wide')
st.title('◈ Insight Agent')
st.caption('经营分析 / Planner → Analyst → Reviewer → 有界修订')
with st.sidebar:
    st.header('数据工作区')
    uploaded = st.file_uploader('上传 CSV（UTF-8，最大 10 MB）', type=['csv'])
    offline = st.checkbox('离线计算（不调用模型）', value=True)
    password = st.text_input('在线访问密码', type='password', max_chars=256) if not offline else ''
    st.info('DeepSeek 已配置' if os.getenv('DEEPSEEK_API_KEY') or os.getenv('LLM_API_KEY') else '未配置模型，使用离线计算')
    st.caption('在线模式将问题、字段名和汇总指标发送给配置的服务。模型复核不等于事实保证。')
sample = 'date,amount,category\n2026-10-01,1200,直营\n2026-10-01,800,电商\n2026-10-02,1500,直营\n2026-10-02,950,电商\n2026-10-03,-100,电商\n2026-10-03,1800,直营\n'
raw = uploaded.getvalue() if uploaded else sample.encode()
try:
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('文件超过 10 MB')
    headers = next(csv.reader(io.StringIO(raw.decode('utf-8-sig'))), [])
    if not headers or len(headers) != len(set(headers)) or any(not h.strip() for h in headers):
        raise ValueError('表头为空或重复')
    # Keep money as source text; float conversion before Decimal loses precision.
    frame = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    if len(frame) > 100000:
        raise ValueError('最多支持 100000 行')
except Exception:
    st.session_state.pop('analysis', None)
    st.error('CSV 无法读取或超出限制，请检查编码、格式及文件大小。')
    st.stop()
st.subheader('01 / 定义分析口径')
st.caption('当前使用上传数据' if uploaded else '当前使用内置示例数据')
st.dataframe(frame.head(100), width='stretch')
if len(frame.columns) < 3:
    st.session_state.pop('analysis', None)
    st.error('至少需要日期、金额、分组三个字段')
    st.stop()
cols = list(frame.columns)
a, b, c = st.columns(3)
date = a.selectbox('日期字段', cols, index=cols.index('date') if 'date' in cols else 0)
amount = b.selectbox('金额字段', cols, index=cols.index('amount') if 'amount' in cols else 1)
group = c.selectbox('分组字段', cols, index=cols.index('category') if 'category' in cols else 2)
question = st.text_input('分析问题', '概括收入走势、渠道贡献和需要关注的数据质量问题', max_chars=2000)
fingerprint = hashlib.sha256(raw + json.dumps([date, amount, group, question, offline]).encode()).hexdigest()
if st.session_state.get('fingerprint') != fingerprint:
    st.session_state.pop('analysis', None)
if st.button('运行分析 →', type='primary'):
    st.session_state.pop('analysis', None)
    if len({date, amount, group}) != 3 or not question.strip():
        st.error('请选择三个不同字段并填写分析问题')
    else:
        try:
            with st.spinner('规划、计算、分析与复核中…'):
                with nullcontext() if offline else online_access(password):
                    outcome = run_analysis(frame, date, amount, group, question, offline=offline)
            st.session_state['analysis'] = outcome
            st.session_state['fingerprint'] = fingerprint
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error('分析流程异常，请重试或选择离线计算。')
if 'analysis' in st.session_state:
    outcome = st.session_state['analysis']
    result = outcome['metrics']
    st.subheader('02 / 分析结果')
    st.write('运行状态：', outcome['status'])
    if outcome['status'] == 'degraded':
        st.warning('模型协作未完成，当前仅提供确定性计算结果。')
    elif outcome['status'] == 'needs_review':
        st.warning('修订后仍未通过复核，以下分析需要人工检查。')
    a, b, c = st.columns(3)
    a.metric('净金额', f"{float(result['total']):,.2f}")
    b.metric('数据行数', result['rows'])
    c.metric('负金额行数', result['negative_rows'])
    a, b = st.columns(2)
    a.line_chart(pd.Series({k: float(v) for k, v in result['daily'].items()}, name='净金额'))
    b.bar_chart(pd.Series({k: float(v) for k, v in result['groups'].items()}, name='净金额'))
    st.info(result['semantics'])
    if result['duplicate_rows']:
        st.warning(f"发现 {result['duplicate_rows']} 行重复记录，请检查业务含义。")
    st.markdown(outcome['explanation'])
    with st.expander('Agent 计划、复核与执行轨迹', expanded=True):
        st.json({key: outcome[key] for key in ('plan', 'review', 'events')})
    with st.expander('审计计算结果'):
        st.json(result)
    document = report(result, outcome['explanation'], question)
    document += '\n\n## 编排审计\n\n```json\n' + json.dumps({k: outcome[k] for k in ('status','plan','review','events')}, ensure_ascii=False, indent=2) + '\n```'
    st.download_button('下载 Markdown 报告', document, 'analysis.md')
