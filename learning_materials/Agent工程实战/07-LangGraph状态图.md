# 项目 7：搭建第一个 LangGraph 状态图

## 一、目标

把一段按顺序执行的代码改成显式状态图：输入节点清理问题，模型节点生成回答，输出节点完成结果。

## 开始前：准备本节项目

创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`。本阶段依赖改为 `langgraph` 与 `langchain`。

<!-- lab-check:structure -->

在项目终端创建 `.venv`，再从 `requirements.txt` 安装依赖。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、安装

```bash
pip install -U langgraph langchain langchain-openai
```

## 三、定义状态

```python
from typing import TypedDict

class SupportState(TypedDict, total=False):
    question: str
    normalized_question: str
    answer: str
    trace: list[str]
```

状态是节点之间共享的数据契约。不要把数据库连接、文件句柄等难以序列化的对象塞进状态。

## 四、编写节点

```python
def normalize_node(state: SupportState):
    question = state["question"].strip()
    if not question:
        raise ValueError("question 不能为空")
    return {
        "normalized_question": question,
        "trace": [*state.get("trace", []), "normalize"],
    }

def answer_node(state: SupportState):
    response = model.invoke(state["normalized_question"])
    return {
        "answer": str(response.content),
        "trace": [*state.get("trace", []), "answer"],
    }
```

节点返回“状态增量”，而不是偷偷修改全局变量。

## 五、连成一张图

```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(SupportState)
builder.add_node("normalize", normalize_node)
builder.add_node("answer", answer_node)
builder.add_edge(START, "normalize")
builder.add_edge("normalize", "answer")
builder.add_edge("answer", END)

graph = builder.compile()
result = graph.invoke({"question": "  如何退款？ ", "trace": []})
print(result["answer"])
print(result["trace"])
```

### LangGraph 图 API 拆解

| 框架代码 | 作用 | 返回 / 后续 |
|---|---|---|
| `StateGraph(SupportState)` | 创建以 `SupportState` 为状态契约的图构建器 | 此时还不能运行，只是在描述节点和边 |
| `add_node("normalize", normalize_node)` | 把节点名与可调用函数注册到图中 | 节点接收当前状态，返回本节点负责的状态增量 |
| `START` / `END` | LangGraph 提供的特殊起点和终点标记 | 它们不是你定义的业务节点，也不会执行模型调用 |
| `add_edge(a, b)` | 声明节点完成后的固定流向 | 只负责连线，不负责合并状态 |
| `builder.compile()` | 校验图结构并生成可运行图 | 返回的 `graph` 才具有 `invoke`、`stream` 等运行方法 |
| `graph.invoke(input)` | 用初始状态运行整张图直到结束 | 返回合并后的最终状态字典，不只是最后一个节点的返回值 |

节点返回字典后，LangGraph 会按状态 Schema 与 reducer 规则合并增量。若多个节点可能同时更新同一字段，就必须明确合并语义；否则复杂图中容易产生冲突。这里不展开 `TypedDict` 的基础类型语法，只关注它作为图状态契约的作用。

在 `solution.py` 中实现 `merge_state`，分别处理普通字段覆盖和列表字段追加，并保证不修改输入状态。

<!-- lab-check:implementation -->

然后在 `app.py` 中导入 `merge_state` 与 `langgraph.graph.StateGraph`，搭起两个节点的最小图并运行一组初始状态。

<!-- lab-check:integration -->

## 六、实验任务

<!-- lab-check:acceptance -->

实验 3-1 会让你实现简化版状态合并器。你必须分清两种语义：普通字段覆盖；带 reducer 的列表字段追加。输入状态不可被原地修改。

## 七、常见错误

1. 节点返回整个旧状态，导致字段更新来源难追踪。
2. 多个节点写同一字段，却没有定义合并规则。
3. 节点依赖未声明字段，运行到中途才 KeyError。
4. 把“流程走到哪”藏在函数调用栈里，无法观察。

## 八、下一步

当前图只有一条直线。下一节用条件边把咨询分到订单、知识库或人工节点。

[LangGraph 官方 Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
