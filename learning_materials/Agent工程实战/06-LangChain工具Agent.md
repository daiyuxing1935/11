# 项目 6：完成第一个 LangChain 工具 Agent

## 一、目标

把模型和工具交给 `create_agent`，跑通一个能自主决定是否查单的客服 Agent。

## 开始前：准备本节项目

在实验室创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`，声明 `langchain`、`langchain-openai`、`python-dotenv`。

<!-- lab-check:structure -->

创建本项目的 `.venv`，再安装依赖。请在环境检查通过后再排查 Agent 代码，避免把包未安装误判成框架 API 错误。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、最小 Agent

```python
from langchain.agents import create_agent

agent = create_agent(
    model=model,
    tools=[query_order_tool],
    system_prompt="""你是订单客服。涉及真实订单状态时必须调用工具；
    工具返回 not_found 时请核对订单号，不要编造状态。""",
)

result = agent.invoke({
    "messages": [
        {"role": "user", "content": "订单 O-100 到哪了？"}
    ]
})

print(result["messages"][-1].content)
```

### `create_agent` 参数与返回值拆解

| 位置 | 作用 | 工程注意点 |
|---|---|---|
| `from langchain.agents import create_agent` | 导入 LangChain 的预构建 Agent 工厂 | 它适合常见工具循环；明确的复杂业务分支应进一步使用 LangGraph |
| `model=model` | 指定负责推理和生成工具调用的聊天模型 | 模型本身需要支持 tool calling；不同供应商的支持程度可能不同 |
| `tools=[query_order_tool]` | 注册本次 Agent 可调用的最小权限工具集合 | 不要为了方便把所有后台能力都暴露给一个 Agent |
| `system_prompt=...` | 约束角色、工具使用条件和失败策略 | 应写清“何时必须调用”“何时不得猜测”“失败后如何降级” |
| `agent.invoke({"messages": [...]})` | 启动一轮 Agent 工作流 | 输入键是 `messages`；运行过程中可能发生多次模型与工具调用 |
| `result["messages"]` | 返回完整执行消息轨迹 | 最后一条通常是最终回答，中间可能包含带 `tool_calls` 的 AI 消息和工具结果 |

`create_agent` 返回的不是普通聊天模型，而是一个已经编译好的 Agent 图。调用者传入状态字典，运行时在状态中追加消息并决定是否继续循环。只取最后一句适合展示给用户，但排障和审计时应保留中间消息与工具执行记录。

先在 `solution.py` 中实现 `run_tool_plan`，用确定性步骤练习观察记录、失败停止和最大步数，再把这个心智模型映射到 `create_agent`。

<!-- lab-check:implementation -->

## 三、Agent 循环发生了什么

```text
用户消息
  ↓
模型判断需要 query_order_tool
  ↓
执行工具并产生 ToolMessage
  ↓
模型读取观察结果并生成最终回答
```

`create_agent` 的运行时建立在 LangGraph 上。停止条件通常是模型产生最终回答，或达到迭代限制。

## 四、增加第二个工具

```python
@tool
def refund_policy(product_type: str) -> str:
    """查询指定商品类型的退款政策。"""
    policies = {"digital": "数字商品激活后不可退款", "physical": "签收后7天内可申请"}
    return policies.get(product_type, "需要人工确认")
```

将它加入 tools，再提问：“订单 O-200 是实体商品，状态和退款规则分别是什么？”观察 Agent 是否产生多次工具调用。

## 五、保留执行轨迹

生产环境不能只保存最终一句话。至少记录每步工具名、参数摘要、执行状态和耗时，同时避免把 Key 与敏感数据写入日志。

在 `app.py` 中导入 `run_tool_plan`，并导入 `langchain.agents.create_agent` 完成实际 Agent 小项目。至少运行一次无需工具的问题和一次必须查单的问题。

<!-- lab-check:integration -->

## 六、实验任务

<!-- lab-check:acceptance -->

实验 2-3 用确定性工具计划模拟 Agent 循环。你要实现：顺序执行、观察记录、失败停止和最大步数。完成后再回看 `create_agent`，你会更清楚框架替你处理了哪些工作。

## 七、常见错误

1. system prompt 没规定何时必须调用工具。
2. 工具太多且描述相似，模型容易选错。
3. 没有最大迭代限制，异常场景可能反复调用。
4. 只记录最终回答，线上错误无法复盘。

## 八、下一步

简单 Agent 可以交给 `create_agent`。需要明确分支、恢复和人工审批时，下一阶段直接设计 LangGraph。

[LangChain 官方 Agent 文档](https://docs.langchain.com/oss/python/langchain/agents)
