# 毕业项目：端到端智能客服 Agent

## 一、交付目标

完成一个可审计、可恢复、可转人工的客服 Agent，而不只是一个演示聊天框。

## 开始前：建立毕业项目工作区

先在实验室创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`。通过首轮检查后，再按下方推荐目录拆分更多模块。

<!-- lab-check:structure -->

创建毕业项目独立的 `.venv`，并安装 `langchain`、`langgraph`、`python-dotenv`。AI 会同时检查依赖声明与实际安装记录。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

```text
请求校验
   ↓
意图与风险路由
   ├─ order → 订单工具 ─┐
   ├─ faq → 检索 → 有依据回答
   ├─ chat → 普通响应  │
   └─ urgent/低置信度 → 人工
                       ↓
                 统一结果 + trace
```

## 二、推荐目录

```text
support-agent/
├── app.py
├── graph.py
├── state.py
├── nodes/
│   ├── classify.py
│   ├── order.py
│   ├── knowledge.py
│   └── human.py
├── tools/order.py
├── retrieval/store.py
└── tests/
    ├── test_routes.py
    ├── test_tools.py
    └── test_end_to_end.py
```

## 三、统一状态与返回契约

```python
class SupportState(TypedDict, total=False):
    request_id: str
    text: str
    intent: str
    confidence: float
    urgent: bool
    answer: str
    citations: list[str]
    needs_human: bool
    trace: list[str]
```

所有节点只返回增量，最终节点确保 `answer`、`citations`、`trace` 永远存在。

先在 `solution.py` 中实现端到端入口 `handle_support_turn`。它应把路由、订单、知识证据、人工降级和 trace 组成一个稳定返回契约。

<!-- lab-check:implementation -->

## 四、编排图

```python
builder = StateGraph(SupportState)
builder.add_node("validate", validate_node)
builder.add_node("classify", classify_node)
builder.add_node("order", order_node)
builder.add_node("knowledge", knowledge_node)
builder.add_node("respond", respond_node)
builder.add_node("human", human_node)
builder.add_node("finalize", finalize_node)

builder.add_edge(START, "validate")
builder.add_edge("validate", "classify")
builder.add_conditional_edges("classify", route_request, {
    "order": "order", "knowledge": "knowledge",
    "respond": "respond", "human": "human",
})
for node in ("order", "knowledge", "respond", "human"):
    builder.add_edge(node, "finalize")
builder.add_edge("finalize", END)
```

编译时加入 checkpointer，并从鉴权后的用户与会话生成 thread_id。

在 `app.py` 中导入 `handle_support_turn` 与 LangGraph 图组件，分别跑通订单、FAQ、闲聊和人工四条路径。

<!-- lab-check:integration -->

## 五、工程规则

1. 非法输入在 validate 拒绝，不消耗模型调用。
2. 高风险规则由确定性代码控制，不只写在 prompt。
3. 工具与检索异常进入可解释降级分支。
4. trace 只记录节点、状态和耗时摘要，不记录 Key 或敏感原文。
5. 同分选择与规则顺序必须稳定，保证结果可复现。

## 六、端到端测试清单

<!-- lab-check:acceptance -->

- 紧急请求无条件转人工；
- 置信度 0.59 与 0.60 的边界；
- 已存在与不存在的订单；
- 有知识证据与无知识证据；
- 普通闲聊；
- 工具超时；
- 输入对象不可变；
- 不同 thread_id 不串话。

## 七、编程实验 4-3

平台提供精简的 `handle_support_turn` 骨架。你需要独立实现全部分支，并经历三层验收：

1. 服务端私有业务场景；
2. 基于本人代码的原理答辩；
3. 系统注入故障后的定位与修复。

代码测试通过只是入场券。能够解释规则优先级、发现被改坏的边界并修复，才表示具备复杂工程场景能力。

## 八、完成后的扩展

把内存订单库替换为真实 API，把词项检索替换为向量库，把 InMemorySaver 替换为持久化 checkpointer，再增加权限、限流、评估集和观测指标。每次只替换一层，并保持输入输出契约不变。
