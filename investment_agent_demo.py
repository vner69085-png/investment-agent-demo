"""
投资顾问Agent演示框架
用途：给运营/上级演示核心交互链路，不追求代码质量
运行：python investment_agent_demo.py
依赖：pip install anthropic
环境变量：AIHUBMIX_API_KEY
"""

import os
import re
import json
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("AIHUBMIX_API_KEY"),
    base_url="https://aihubmix.com",
)


def parse_json(text: str) -> dict:
    """兼容模型输出带 markdown 代码块的情况"""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


# ─────────────────────────────────────────
# Prompt定义
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
# 各Agent执行函数
# ─────────────────────────────────────────

def run_planner(user_question: str) -> dict:
    print("\n[规划Agent] 正在拆解任务...\n")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=PLANNER_PROMPT,
        messages=[{"role": "user", "content": user_question}]
    )
    raw = response.content[0].text.strip()
    return parse_json(raw)


def run_search_agent(task: dict) -> dict:
    print(f"  [搜索Agent] 执行：{task['description']}")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=SEARCH_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}]
    )
    return parse_json(response.content[0].text.strip())


def run_fund_analysis_agent(task: dict) -> dict:
    print(f"  [基金分析Agent] 执行：{task['description']}")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=FUND_ANALYSIS_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}]
    )
    return parse_json(response.content[0].text.strip())


def run_fund_compare_agent(task: dict) -> dict:
    print(f"  [基金对比Agent] 执行：{task['description']}")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        system=FUND_COMPARE_AGENT_PROMPT,
        messages=[{"role": "user", "content": f"任务ID：{task['id']}\n任务描述：{task['description']}"}]
    )
    return parse_json(response.content[0].text.strip())


def run_report_agent(user_question: str, risk_preference: str, all_results: list) -> str:
    print("\n[报告Agent] 正在汇总生成报告...\n")
    context = f"用户原始问题：{user_question}\n风险偏好：{risk_preference or '未指定'}\n\n各子Agent输出：\n"
    for r in all_results:
        context += json.dumps(r, ensure_ascii=False, indent=2) + "\n"
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        system=REPORT_AGENT_PROMPT,
        messages=[{"role": "user", "content": context}]
    )
    return response.content[0].text.strip()


# ─────────────────────────────────────────
# 主调度逻辑
# ─────────────────────────────────────────

AGENT_ROUTER = {
    "web_search":    run_search_agent,
    "fund_analysis": run_fund_analysis_agent,
    "fund_compare":  run_fund_compare_agent,
}

def run(user_question: str):
    print("=" * 60)
    print(f"用户问题：{user_question}")
    print("=" * 60)

    # Step 1: 规划Agent拆解任务
    plan = run_planner(user_question)

    # 处理拒识和反问
    if plan.get("action") == "reject":
        print(f"\n[拒识] {plan.get('reason')}\n")
        return
    if plan.get("action") == "clarify":
        print(f"\n[需要补充信息] {plan.get('question')}\n")
        return

    # Step 2: 打印待办清单
    subtasks = plan.get("subtasks", [])
    risk = plan.get("risk_preference")
    print(f"风险偏好：{risk or '未指定'}")
    print(f"拆解为 {len(subtasks)} 个子任务：")
    for t in subtasks:
        print(f"  {t['id']}. [{t['type']}] {t['description']}")

    # Step 3: 按顺序执行子Agent（简单串行，depends_on暂不处理）
    print("\n─── 执行子任务 ───")
    results = []
    for task in subtasks:
        task_type = task.get("type")
        if task_type in AGENT_ROUTER:
            result = AGENT_ROUTER[task_type](task)
            results.append(result)
        else:
            print(f"  [跳过] 未知任务类型：{task_type}")

    # Step 4: 报告Agent汇总输出
    if results:
        report = run_report_agent(user_question, risk, results)
        print("─── 最终报告 ───\n")
        print(report)
    print("\n" + "=" * 60)


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────

if __name__ == "__main__":
    # 直接改这里换测试问题
    question = "帮我做光伏行业深度研究，并结合我偏保守的风险偏好推荐基金组合"
    run(question)
