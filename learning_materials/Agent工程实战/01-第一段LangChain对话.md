# 项目 1：用 LangChain 发出第一条 AI 消息

## 一、本节做完你会得到什么

你会亲手创建一个 `chat.py`，在终端输入问题并看到模型回答。先不做 Agent，只把最短调用链跑通：

```text
你的问题 → 消息列表 → ChatModel.invoke() → AIMessage.content
```

## 二、前置环境

- Python 3.11+
- 一个 OpenAI 兼容模型服务的 API Key
- 不要把 Key 写进代码或提交到 Git

创建项目：

```text
first-agent/
├── .env.example
├── requirements.txt
├── solution.py
└── app.py
```

在编程实验室的项目区按这个名称创建四个文件。教程中的 `chat.py` 代码最终放进 `app.py`，可测试的消息构造逻辑放进 `solution.py`。

<!-- lab-check:structure -->

`requirements.txt`：

```text
langchain>=1.0
langchain-openai>=1.0
python-dotenv>=1.0
```

安装：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

先让虚拟环境检查通过，再让依赖检查确认这些包确实安装在当前项目环境中。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 三、配置模型

复制 `.env.example` 为 `.env`，填入你自己的值：

```properties
LLM_API_KEY=在本机填写
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

`.gitignore` 中加入 `.env`。

## 四、编写第一版 chat.py

```python
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    raise RuntimeError("缺少 LLM_API_KEY，请先配置 .env")

model = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "deepseek-chat"),
    api_key=api_key,
    base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
    temperature=0.2,
    timeout=30,
    max_retries=2,
)

messages = [
    {"role": "system", "content": "你是一位耐心的 Python 助教，回答控制在120字内。"},
    {"role": "user", "content": "请用一个生活例子解释 AI Agent。"},
]

response = model.invoke(messages)
print(response.content)
```

把消息构造部分整理为 `solution.py` 中的 `build_chat_messages`。这里不能只写函数定义或 `pass`，函数需要真正完成输入校验、空白清理和消息构造：

```python
# solution.py
def build_chat_messages(system_prompt, user_input):
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ValueError("system_prompt 必须是非空字符串")
    if not isinstance(user_input, str) or not user_input.strip():
        raise ValueError("user_input 必须是非空字符串")

    return [
        {"role": "system", "content": system_prompt.strip()},
        {"role": "user", "content": user_input.strip()},
    ]
```

实现后先运行语法检查，再点击“运行 9 个测试点”。检查器会实际调用函数，验证正常输入、个性化指令、首尾空白、内部换行、返回对象隔离和非法输入；`pass` 或 `raise NotImplementedError` 都不会通过。每个测试点会单独显示结果。

<!-- lab-check:implementation -->

运行：

```bash
python chat.py
```

在实验室中由 `app.py` 导入 `solution.py` 的函数，并把原来的固定消息列表替换为函数调用：

```python
from solution import build_chat_messages

messages = build_chat_messages(
    "你是一位耐心的 Python 助教，回答控制在120字内。",
    "请用一个生活例子解释 AI Agent。",
)
response = model.invoke(messages)
```

然后接入 `ChatOpenAI`。真实 Key 只放本地 `.env`，不要复制进代码。

<!-- lab-check:integration -->

## 五、你刚刚敲的代码做了什么

`system` 规定长期角色和边界，`user` 保存本轮输入。`invoke()` 返回的是 `AIMessage`，因此正文要从 `response.content` 读取，而不是假设返回值就是字符串。

### 只拆解本节新增的框架代码

| 框架代码 | 作用 | 你需要记住的工程含义 |
|---|---|---|
| `from dotenv import load_dotenv` | 从项目根目录的 `.env` 读取配置并放入当前进程环境 | 它负责“加载配置”，不负责向模型发请求；真实 Key 仍不能写进代码 |
| `from langchain_openai import ChatOpenAI` | 导入 OpenAI 兼容聊天模型适配器 | 类名虽然叫 OpenAI，但只要服务实现兼容协议，也可以通过 `base_url` 接入其他模型服务 |
| `ChatOpenAI(...)` | 创建可复用的模型客户端 | 此时只是保存模型名、地址、重试等配置，还没有产生一次模型调用 |
| `model.invoke(messages)` | 同步发起一次完整对话调用 | 入参是消息序列，返回 `AIMessage`；网络、鉴权和模型错误会在这一行暴露 |
| `response.content` | 读取 `AIMessage` 的正文 | 不要直接把整个 `response` 当字符串，因为对象中还可能包含用量、结束原因等元数据 |

`temperature=0.2` 控制回答随机性，客服和教学场景通常偏低；`timeout=30` 限制一次请求等待时间；`max_retries=2` 只适合重试短暂的网络故障，不能修复错误 Key 或错误模型名。这里不展开 `if`、列表和字典等基础 Python 语法。

## 六、动手改造

把固定问题换成 `input("你：")`，再把空输入拒绝掉。随后进入编程实验 1-1，独立实现消息构造函数。

<!-- lab-check:acceptance -->

## 七、常见错误

1. `401`：Key 无效，或 Key 与 Base URL 不属于同一服务。
2. `model not found`：检查 `LLM_MODEL` 是否为账户可用模型。
3. 一直超时：先用短问题测试，再检查代理、网络和 Base URL。
4. `response` 打印内容很复杂：只打印 `response.content`。

## 八、下一步

当前程序每次退出都会忘记对话。下一节会把消息历史保存下来，实现真正的连续追问。

[LangChain 官方模型文档](https://docs.langchain.com/oss/python/langchain/models)
