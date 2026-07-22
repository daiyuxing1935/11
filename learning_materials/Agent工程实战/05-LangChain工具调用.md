# 项目 5：给 Agent 接入订单查询工具

## 一、目标

定义一个真实可调用的业务工具，并学会校验模型生成的工具名与参数。

## 开始前：准备本节项目

创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`，在依赖文件中声明 `langchain`、`langchain-openai`、`python-dotenv`。

<!-- lab-check:structure -->

使用项目终端创建 `.venv` 并安装当前依赖。AI 会确认包声明和实际安装状态都正确。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、先写普通业务函数

```python
ORDER_DB = {
    "O-100": {"status": "已发货", "carrier": "顺丰"},
    "O-200": {"status": "退款审核中", "carrier": None},
}

def query_order(order_id: str) -> dict:
    order_id = order_id.strip()
    if not order_id:
        raise ValueError("order_id 不能为空")
    return ORDER_DB.get(order_id, {"status": "not_found"})
```

先让普通函数通过测试，再把它暴露给模型。这样业务逻辑不会和框架绑死。

## 三、注册 LangChain 工具

```python
from langchain.tools import tool

@tool
def query_order_tool(order_id: str) -> dict:
    """根据订单编号查询当前状态。订单编号形如 O-100。"""
    return query_order(order_id)
```

工具名称、参数类型和 docstring 会成为模型看到的契约。说明不清会直接降低工具选择准确率。

## 四、手动查看工具调用

```python
model_with_tools = model.bind_tools([query_order_tool])
response = model_with_tools.invoke("帮我查订单 O-100")
print(response.tool_calls)
```

一个典型调用包含 `id`、`name`、`args`。在执行前必须确认 name 已注册、args 是字典且必填字段存在。

### 工具相关 API 到底做了什么

| 框架代码 | 作用 | 常见误解 |
|---|---|---|
| `from langchain.tools import tool` | 导入工具装饰器，把普通 Python 函数转换为 LangChain Tool | `tool` 不会自动执行函数，也不会替你处理权限 |
| `@tool` | 从函数名、类型标注和 docstring 生成工具名称、参数 Schema 与描述 | docstring 不是普通注释，它会参与模型的工具选择 |
| `model.bind_tools([...])` | 给当前模型绑定可供选择的工具 Schema，返回新的模型 Runnable | 绑定不等于调用；此时业务函数还没有运行 |
| `response.tool_calls` | 读取模型建议的结构化调用列表 | 这是“模型提出的执行请求”，必须校验后才能交给真实业务函数 |

每个 `tool_call` 的 `id` 用来把后续 `ToolMessage` 与原请求对应起来；`name` 决定候选工具；`args` 是模型生成的参数。工程代码应使用服务端工具注册表查找 `name`，绝不能按模型返回的字符串动态导入或执行任意函数。

在 `solution.py` 中实现 `execute_tool_call`，让所有工具共用同一条名称校验、参数校验和错误转换边界。

<!-- lab-check:implementation -->

## 五、隔离工具故障

数据库超时不能让整个对话进程崩溃。工具异常应转换成带 `tool_call_id` 的工具消息，让模型决定重试、解释或转人工。

在 `app.py` 中导入 `execute_tool_call`，再用 `@tool` 注册的订单工具完成一次“模型提出调用 → 服务端校验 → 执行业务函数”的小项目链路。

<!-- lab-check:integration -->

## 六、实验任务

<!-- lab-check:acceptance -->

进入实验 2-2，实现 `execute_tool_call`：

- 拒绝未注册工具；
- 拒绝缺少参数；
- 成功时返回统一消息；
- 工具自身异常转换为 error 消息。

## 七、常见错误

1. 直接调用模型给出的任意函数名。
2. 把工具异常文本伪装成正常结果。
3. 返回工具结果时遗漏 `tool_call_id`，模型无法对应原调用。
4. 工具函数同时做查询、写入和删除，权限边界过大。

## 八、下一步

下一节使用 `create_agent` 让模型自动在“思考—调用工具—读取结果—回答”之间循环。

[LangChain 官方工具文档](https://docs.langchain.com/oss/python/langchain/tools)
