# 投资顾问 Agent Demo

基于 Claude API 构建的多 Agent 投资顾问演示框架，展示「规划 → 执行 → 汇总」的核心 Agent 协作链路。

## 演示效果

输入一个投资问题，系统自动完成：

1. **规划 Agent** — 拆解问题，生成子任务执行计划
2. **搜索 Agent** — 模拟检索行业信息、政策动态
3. **基金分析 Agent** — 对候选基金进行深度分析
4. **基金对比 Agent** — 横向对比多支基金
5. **报告 Agent** — 汇总所有结果，生成完整投资报告

```
用户问题：帮我做光伏行业深度研究，并结合我偏保守的风险偏好推荐基金组合
════════════════════════════════════════════════════

[规划Agent] 正在拆解任务...

风险偏好：保守型
拆解为 5 个子任务：
  1. [web_search]    搜索光伏行业最新政策动态...
  2. [web_search]    搜索主要光伏主题基金列表...
  3. [fund_analysis] 对候选基金进行深度分析...
  4. [fund_compare]  横向对比候选基金...
  5. [report_write]  生成研究报告及投资方案

─── 执行子任务 ───
  [搜索Agent] 执行中...
  [基金分析Agent] 执行中...
  [基金对比Agent] 执行中...

[报告Agent] 正在汇总生成报告...

─── 最终报告 ───
...
```

## 快速开始

**1. 安装依赖**

```bash
pip install anthropic
```

**2. 配置 API Key**

支持 Anthropic 官方 API 或兼容接口（如 AIhubmix）：

```bash
# 使用 AIhubmix
export AIHUBMIX_API_KEY="your-key-here"
```

**3. 运行**

```bash
python investment_agent_demo.py
```

修改文件末尾的 `question` 变量来切换测试问题：

```python
question = "帮我做光伏行业深度研究，并结合我偏保守的风险偏好推荐基金组合"
```

## 架构说明

```
用户输入
   │
   ▼
规划 Agent（Planner）
   │  拆解为子任务列表
   ▼
┌──────────────────────────┐
│  web_search  →  搜索Agent │
│  fund_analysis → 分析Agent│  串行执行
│  fund_compare  → 对比Agent│
└──────────────────────────┘
   │  汇总所有结果
   ▼
报告 Agent（Reporter）
   │
   ▼
最终投资报告
```

## 支持的任务类型

| 类型 | 说明 |
|------|------|
| `web_search` | 搜索行业信息、政策动态 |
| `fund_analysis` | 对单支基金进行深度分析 |
| `fund_compare` | 横向对比多支同类基金 |
| `report_write` | 汇总信息，生成研究报告 |

## 注意事项

- 所有 Agent 输出均为 AI 模拟生成，**不构成真实投资建议**
- 本项目为演示框架，不接入真实行情数据源
- 子任务当前为串行执行，`depends_on` 字段预留供后续并行化扩展

## License

MIT
