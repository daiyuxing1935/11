# 项目 4：把客服规则做成 LangChain 提示链

## 一、目标

实现一个可复用的客服提示模板，同一段代码可以处理不同用户、订单和问题。

## 开始前：准备本节项目

在实验室创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`。本阶段依赖 `langchain`、`langchain-openai`、`python-dotenv`。

<!-- lab-check:structure -->

执行 `python -m venv .venv` 创建隔离环境，再执行 `pip install -r requirements.txt`。环境和依赖是两个独立检查点。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、安装与目录

```text
support-chain/
├── prompts.py
└── main.py
```

## 三、定义模板

```python
from langchain_core.prompts import ChatPromptTemplate

support_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是电商客服。\n规则：\n1. 不猜测订单状态；\n2. 信息不足时先追问；\n3. 回答末尾给出下一步操作。"""),
    ("user", "用户编号：{user_id}\n问题：{question}"),
])
```

## 四、组成一条链

```python
chain = support_prompt | model

result = chain.invoke({
    "user_id": "U-100",
    "question": "退款一般需要多久？",
})
print(result.content)
```

`|` 把上一步输出交给下一步：字典先被模板渲染成消息，再交给模型。

### 框架类与函数逐项说明

| 框架代码 | 输入 | 输出 / 作用 |
|---|---|---|
| `ChatPromptTemplate` | 一组带角色的消息模板 | 得到可重复渲染的聊天提示对象，避免每次手工拼整段字符串 |
| `ChatPromptTemplate.from_messages(...)` | `("system", 模板)`、`("user", 模板)` 等消息定义 | 编译出带输入变量契约的模板；花括号字段会成为调用时必须提供的变量 |
| `support_prompt | model` | 左侧提示模板、右侧聊天模型 | 创建 Runnable 链；左侧输出的消息对象会自动成为右侧输入 |
| `chain.invoke({...})` | 与模板字段对应的字典 | 先渲染提示，再调用模型，最终返回 `AIMessage` |

这里的管道符不是把两段字符串相加，而是在 LangChain Runnable 协议下组合两个可执行组件。以后接入输出解析器、检索器时仍可以沿用同一组合方式。基础的字典创建和函数定义不在本节重复讲解。

## 五、先在边界校验输入

```python
def ask_support(chain, user_id, question):
    user_id = str(user_id).strip()
    question = str(question).strip()
    if not user_id or not question:
        raise ValueError("user_id 和 question 不能为空")
    return chain.invoke({"user_id": user_id, "question": question}).content
```

实验室中的核心函数叫 `render_support_prompt`。先在 `solution.py` 中实现确定性的模板契约，再回看 `ChatPromptTemplate` 如何把相同问题封装成框架组件。

<!-- lab-check:implementation -->

不要让缺字段错误跑到模型请求之后才暴露，那会浪费时间和调用费用。

## 六、小项目改造

为模板增加 `channel`（网页/电话）和 `tone`（简洁/详细），但不要通过字符串拼接创建整段提示。运行三组输入，确认模板能够复用。

在 `app.py` 中从 `solution` 导入核心函数，并导入 `langchain_core.prompts.ChatPromptTemplate` 完成实际框架接入。

<!-- lab-check:integration -->

## 七、实验任务

<!-- lab-check:acceptance -->

实验 2-1 不依赖网络：你要独立实现一个安全模板渲染器，处理重复字段、额外字段和缺失字段。它会帮助你理解 `PromptTemplate` 在做什么。

## 八、常见错误

1. 模板写了 `{order_id}`，调用时没有传入。
2. 把用户内容拼进 system，造成角色边界混乱。
3. 业务规则只写在前端，后端调用时丢失。
4. 直接使用 `eval` 渲染模板，产生安全风险。

## 九、下一步

下一节给客服接入订单查询工具，让它从“会说”升级为“能做”。
