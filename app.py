"""
投资顾问 Agent Demo — Web UI
运行：streamlit run app.py
"""

import os
import re
import json
import time
import streamlit as st
from anthropic import Anthropic

# ─────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────

st.set_page_config(
    page_title="投资顾问 Agent Demo",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
.agent-card {
    background: #f8f9fa;
    border-left: 4px solid #dee2e6;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 6px 0;
    font-size: 14px;
    color: #495057;
}
.agent-card.running {
    border-left-color: #339af0;
    background: #e7f5ff;
    color: #1864ab;
}
.agent-card.done {
    border-left-color: #40c057;
    background: #ebfbee;
    color: #2f9e44;
}
.agent-card.error {
    border-left-color: #fa5252;
    background: #fff5f5;
    color: #c92a2a;
}
.step-label {
    font-weight: 600;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# Prompts
# ─────────────────────────────────────────

PLANNER_PROMPT = """你是一个投资顾问规划Agent。
接收用户的投资相关问题，将其拆解为子任务并输出执行计划。

子任务类型只能从以下4种中选取：
- web_search     : 搜索行业信息、政策动态
- fund_analysis  : 对单支基金进行深度分析
- fund_compare   : 横向对比多支同类基金
- report_write   : 汇总信息，生成研究报告或投资方案

如果问题超出投资顾问范围，输出：{"action": "reject", "reason": "..."}
如果问题意图不明确，输出：{"action": "clarify", "question": "..."}

其他情况输出：
{
  "action": "plan",
  "risk_preference": "<从用户描述中提取的风险偏好，未提及则为null>",
  "subtasks": [
    {"id": 1, "type": "<类型>", "description": "<具体任务描述>", "depends_on": []}
  ]
}

只输出JSON，不要包裹在代码块中，不要有任何其他内容。"""

SEARCH_AGENT_PROMPT = """你是一个金融信息搜索Agent。
根据给定的搜索任务描述，模拟搜索并返回结构化的行业信息摘要。
输出格式：
{
  "task_id": <id>,
  "findings": "<搜索到的关键信息，200字以内>",
  "key_companies": ["<公司1>", "<公司2>"],
  "key_funds": ["<相关基金1>", "<相关基金2>"]
}
只输出JSON，不要包裹在代码块中，不要有任何其他内容。"""

FUND_ANALYSIS_AGENT_PROMPT = """你是一个基金分析Agent。
根据给定的分析任务，输出基金的结构化分析报告。
输出格式：
{
  "task_id": <id>,
  "fund_name": "<基金名称>",
  "risk_level": "<低/中/高>",
  "recent_performance": "<近期表现描述>",
  "holdings_summary": "<主要持仓概述>",
  "suitable_for": "<适合的投资者类型>"
}
只输出JSON，不要包裹在代码块中，不要有任何其他内容。"""

FUND_COMPARE_AGENT_PROMPT = """你是一个基金对比Agent。
根据给定的对比任务，输出多支基金的横向对比结果。
输出格式：
{
  "task_id": <id>,
  "funds_compared": ["<基金1>", "<基金2>"],
  "comparison_summary": "<对比核心结论，150字以内>",
  "recommendation": "<综合推荐意见>"
}
只输出JSON，不要包裹在代码块中，不要有任何其他内容。"""

REPORT_AGENT_PROMPT = """你是一个投资报告撰写Agent。
根据所有子Agent的输出结果和用户原始问题，生成一份完整的投资顾问报告。
报告结构：
1. 核心结论（2-3句话）
2. 行业/市场概况
3. 基金分析与推荐
4. 风险提示
5. 免责声明：以上内容均由AI生成，仅供参考，不构成投资建议。

风险偏好参数会传入，请确保推荐结果与风险偏好一致。"""

# ─────────────────────────────────────────
# Agent 工具函数
# ─────────────────────────────────────────

AGENT_TYPE_LABELS = {
    "web_search":    ("🔍", "搜索Agent"),
    "fund_analysis": ("📋", "基金分析Agent"),
    "fund_compare":  ("⚖️", "基金对比Agent"),
    "report_write":  ("📝", "报告Agent"),
}

def parse_json(text: str) -> dict:
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        brace_match = re.search(r"\{[\s\S]*\}", text)
        if brace_match:
            return json.loads(brace_match.group(0))
        raise


def get_client():
    api_key = st.session_state.get("api_key") or os.environ.get("AIHUBMIX_API_KEY")
    return Anthropic(api_key=api_key, base_url="https://aihubmix.com")


def run_planner(client, question):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=PLANNER_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    return parse_json(response.content[0].text.strip())


def run_search_agent(client, task):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SEARCH_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}],
    )
    return parse_json(response.content[0].text.strip())


def run_fund_analysis_agent(client, task):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=FUND_ANALYSIS_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}],
    )
    return parse_json(response.content[0].text.strip())


def run_fund_compare_agent(client, task):
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=FUND_COMPARE_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}],
    )
    return parse_json(response.content[0].text.strip())


def run_report_agent(client, question, risk, results):
    context = f"用户原始问题：{question}\n风险偏好：{risk or '未指定'}\n\n各子Agent输出：\n"
    for r in results:
        context += json.dumps(r, ensure_ascii=False, indent=2) + "\n"
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=REPORT_AGENT_PROMPT,
        messages=[{"role": "user", "content": context}],
    )
    return response.content[0].text.strip()


AGENT_ROUTER = {
    "web_search":    run_search_agent,
    "fund_analysis": run_fund_analysis_agent,
    "fund_compare":  run_fund_compare_agent,
}

# ─────────────────────────────────────────
# UI 布局
# ─────────────────────────────────────────

st.title("📊 投资顾问 Agent Demo")
st.caption("多 Agent 协作链路演示 · Powered by Claude")
st.divider()

left, right = st.columns([1, 1.6], gap="large")

# ── 左侧：输入区 ──
with left:
    st.subheader("输入")

    api_key_input = st.text_input(
        "AIhubmix API Key",
        value=os.environ.get("AIHUBMIX_API_KEY", ""),
        type="password",
        placeholder="sk-...",
    )
    if api_key_input:
        st.session_state["api_key"] = api_key_input

    question = st.text_area(
        "投资问题",
        value="帮我做光伏行业深度研究，并结合我偏保守的风险偏好推荐基金组合",
        height=120,
        placeholder="输入你的投资相关问题...",
    )

    run_btn = st.button("🚀 开始分析", use_container_width=True, type="primary")

    st.divider()
    st.subheader("执行计划")
    plan_area = st.empty()
    st.subheader("Agent 执行状态")
    status_area = st.empty()

# ── 右侧：报告区 ──
with right:
    st.subheader("最终报告")
    report_area = st.empty()
    report_area.info("点击「开始分析」，报告将在此处生成。")

# ─────────────────────────────────────────
# 执行逻辑
# ─────────────────────────────────────────

if run_btn:
    if not (st.session_state.get("api_key") or os.environ.get("AIHUBMIX_API_KEY")):
        st.error("请先填写 API Key")
        st.stop()

    client = get_client()
    results = []

    # Step 1: 规划
    plan_area.markdown("_规划 Agent 正在拆解任务…_")
    status_area.empty()

    try:
        plan = run_planner(client, question)
    except Exception as e:
        st.error(f"规划 Agent 失败：{e}")
        st.stop()

    if plan.get("action") == "reject":
        st.warning(f"⚠️ 超出范围：{plan.get('reason')}")
        st.stop()

    if plan.get("action") == "clarify":
        st.info(f"💬 需要补充信息：{plan.get('question')}")
        st.stop()

    subtasks = plan.get("subtasks", [])
    risk = plan.get("risk_preference")

    # 渲染任务清单
    plan_md = f"**风险偏好：** {risk or '未指定'}  \n**子任务数：** {len(subtasks)}\n\n"
    for t in subtasks:
        icon = AGENT_TYPE_LABELS.get(t["type"], ("▸", t["type"]))[0]
        plan_md += f"{icon} `{t['type']}` {t['description'][:40]}…\n\n"
    plan_area.markdown(plan_md)

    # Step 2: 逐步执行子 Agent
    status_slots = {}
    status_html = ""
    for t in subtasks:
        status_slots[t["id"]] = "pending"

    def render_status(active_id=None, done_ids=None, error_ids=None):
        done_ids = done_ids or []
        error_ids = error_ids or []
        html = ""
        for t in subtasks:
            tid = t["id"]
            icon, label = AGENT_TYPE_LABELS.get(t["type"], ("▸", t["type"]))
            desc = t["description"][:50] + "…" if len(t["description"]) > 50 else t["description"]
            if tid in error_ids:
                css = "error"
                prefix = "✗"
            elif tid in done_ids:
                css = "done"
                prefix = "✓"
            elif tid == active_id:
                css = "running"
                prefix = "⟳"
            else:
                css = ""
                prefix = "○"
            html += f'<div class="agent-card {css}"><span class="step-label">{prefix} {icon} {label}</span><br>{desc}</div>'
        status_area.markdown(html, unsafe_allow_html=True)

    render_status()
    done_ids = []
    error_ids = []

    for task in subtasks:
        task_type = task.get("type")
        if task_type not in AGENT_ROUTER:
            continue

        render_status(active_id=task["id"], done_ids=done_ids, error_ids=error_ids)
        try:
            result = AGENT_ROUTER[task_type](client, task)
            results.append(result)
            done_ids.append(task["id"])
        except Exception as e:
            error_ids.append(task["id"])

        render_status(active_id=None, done_ids=done_ids, error_ids=error_ids)

    # Step 3: 报告 Agent
    if results:
        report_area.info("📝 报告 Agent 正在汇总生成报告…")
        try:
            report = run_report_agent(client, question, risk, results)
            report_area.markdown(report)
        except Exception as e:
            report_area.error(f"报告生成失败：{e}")
    else:
        report_area.warning("没有可用的子任务结果，无法生成报告。")
