# 项目 9：加入线程记忆、检查点与故障恢复

## 一、目标

让同一 `thread_id` 的多轮调用延续状态，不同用户之间不串话，并理解失败后恢复的基础。

## 开始前：准备本节项目

创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`，声明 `langgraph` 与 `langchain`。

<!-- lab-check:structure -->

在当前项目创建 `.venv` 并安装依赖。检查通过后，后续恢复问题才可以聚焦到 thread 与 checkpoint，而不是环境差异。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、内存检查点

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

调用时必须给线程标识：

```python
config = {"configurable": {"thread_id": "user-U100-session-1"}}

graph.invoke(
    {"messages": [{"role": "user", "content": "我想查订单"}]},
    config=config,
)
graph.invoke(
    {"messages": [{"role": "user", "content": "编号是 O-100"}]},
    config=config,
)
```

### 检查点 API 拆解

| 框架代码 | 作用 | 工程边界 |
|---|---|---|
| `InMemorySaver()` | 创建进程内检查点保存器 | 适合本地实验；进程退出后内容消失，不适合生产数据 |
| `builder.compile(checkpointer=checkpointer)` | 把保存器接入编译后的图运行时 | 只有传入 checkpointer 的图才会按线程保存状态快照 |
| `configurable.thread_id` | 指定本次调用属于哪个会话线程 | 它是状态隔离键；必须稳定、唯一，并在服务端校验所属用户 |
| `graph.invoke(input, config=config)` | 在指定线程中执行并保存检查点 | 同一线程后续调用可以读取已有状态，不同线程相互隔离 |
| `graph.get_state(config)` | 读取线程的最新状态快照 | `values` 是当前状态，`next` 表示下一批待执行节点 |

`config` 不属于业务状态，因此不会出现在 `SupportState` 中。它承载的是运行时配置，例如线程标识；业务消息、订单号等仍应放在图状态里。不要把 API Key 放入状态或配置后再写入检查点。

在 `solution.py` 中实现 `save_checkpoint` 与 `load_checkpoint`，每次保存都生成独立快照，并按线程隔离数据。

<!-- lab-check:implementation -->

## 三、线程与长期记忆不是一回事

Checkpointer 保存单个会话线程的状态；跨线程共享用户偏好要使用 Store。不要用固定字符串作为所有用户的 thread_id，否则对话会串在一起。

## 四、查看状态

```python
snapshot = graph.get_state(config)
print(snapshot.values)
print(snapshot.next)
```

检查点能支持对话记忆、人工中断、时间旅行调试和故障恢复。

在 `app.py` 中导入这两个函数与 `InMemorySaver`，用两个不同 `thread_id` 运行多轮调用，确认状态不会串话。

<!-- lab-check:integration -->

## 五、生产环境选择

`InMemorySaver` 适合学习与测试，进程退出后数据消失。生产可按部署环境选择 SQLite、Postgres、Redis 等持久化实现，并为线程设置所有权和过期策略。

## 六、实验任务

<!-- lab-check:acceptance -->

实验 3-3 会让你实现一个小型 checkpointer：

- 每个线程独立版本；
- 每次保存产生快照；
- 读取只返回最新版本；
- 保存与读取都进行防御性复制。

如果快照和运行中状态共享嵌套列表，后续修改会悄悄篡改历史，故障恢复将失去可信度。

## 七、常见错误

1. thread_id 使用用户名明文且不校验所有权。
2. 所有请求共用同一个 thread_id。
3. 把内存 checkpointer 当作持久化数据库。
4. 状态里保存不可序列化对象。

## 八、下一步

图已经能记忆和恢复。最后阶段加入企业知识检索，使回答基于可追溯证据。

[LangGraph 官方持久化文档](https://docs.langchain.com/oss/python/langgraph/persistence)
