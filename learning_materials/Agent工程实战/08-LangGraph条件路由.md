# 项目 8：用条件边实现客服智能路由

## 一、业务需求

客服请求分为订单查询、FAQ 和闲聊；紧急或低置信度请求必须转人工。这里的重点不是让模型“自由发挥”，而是把高风险规则写成确定性代码。

## 开始前：准备本节项目

在实验室创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`，依赖为 `langgraph`、`langchain`。

<!-- lab-check:structure -->

创建 `.venv` 后安装依赖。先通过环境与依赖检查，再开始连条件边。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、扩展状态

```python
class SupportState(TypedDict, total=False):
    text: str
    intent: str
    confidence: float
    urgent: bool
    answer: str
    trace: list[str]
```

## 三、编写路由函数

```python
def route_request(state: SupportState) -> str:
    if state["urgent"] or state["confidence"] < 0.6:
        return "human"
    routes = {
        "order": "order_tool",
        "faq": "knowledge",
        "chat": "respond",
    }
    return routes[state["intent"]]
```

路由函数只做决策，不调用模型、数据库或外部接口，因此可以用普通单元测试覆盖所有边界。

## 四、添加条件边

```python
builder.add_conditional_edges(
    "classify",
    route_request,
    {
        "human": "human",
        "order_tool": "order_tool",
        "knowledge": "knowledge",
        "respond": "respond",
    },
)
```

### `add_conditional_edges` 的四个关键位置

- 第一个参数 `"classify"` 是路由从哪个节点之后发生。
- 第二个参数 `route_request` 是路由函数。LangGraph 会把当时的完整状态传给它，并使用其返回值选择分支。
- 第三个参数是“路由返回值 → 实际节点名”的映射。显式映射能让返回值契约更清晰，也方便重命名业务节点。
- 这个 API 只负责决定下一跳，不会自动给分支节点连接 `END`；每条分支后续仍要显式连线。

路由函数应该快速、确定且无副作用。模型分类可以发生在前一个 `classify` 节点中，但人工升级等高风险规则最好保留在确定性路由代码里，这样才能对边界值做稳定测试。

在 `solution.py` 中实现 `route_support_request`，明确处理紧急优先级、置信度边界、未知意图和非法类型。

<!-- lab-check:implementation -->

每个业务节点执行后再连接到 `END`，或连接到统一的 `finalize` 节点补齐返回结构。

在 `app.py` 中导入该路由函数与 `StateGraph`，把 `classify` 后的四个分支真正接入图中，并让每个分支能够结束。

<!-- lab-check:integration -->

## 五、规则优先级

先判断人工升级，再判断普通意图。若先处理订单，紧急订单可能绕过人工规则。复杂条件建议写成从高风险到低风险的早返回。

## 六、实验任务

<!-- lab-check:acceptance -->

实验 3-2 要求独立实现路由函数，并处理：置信度边界 `0.6`、布尔值冒充数字、未知意图和缺字段。

## 七、验证用例

```python
assert route_request({"intent": "faq", "confidence": 0.6, "urgent": False}) == "knowledge"
assert route_request({"intent": "order", "confidence": 0.99, "urgent": True}) == "human"
```

再加入 0、1、0.59、未知意图与缺字段测试。

## 八、下一步

当订单接口在中间节点失败时，图需要从已成功位置恢复。下一节加入检查点。
