# 项目 10：实现带分数与来源的 RAG 检索

## 一、目标

不要一上来就接向量数据库。先实现一个可测试的 Top-K 检索器，理解检索阶段必须产出正文、分数和来源。

## 开始前：准备本节项目

创建 `requirements.txt`、`.env.example`、`solution.py`、`app.py`。工程阶段需要 `langchain`、`langgraph`、`python-dotenv`。

<!-- lab-check:structure -->

创建当前项目的 `.venv`，再安装 `requirements.txt` 中的依赖。

<!-- lab-check:environment -->

<!-- lab-check:dependencies -->

## 二、准备小型知识库

```python
documents = [
    {"id": "refund-1", "text": "实体商品签收后7天内可申请退款", "terms": ["实体", "退款", "7天"]},
    {"id": "refund-2", "text": "退款审核通常需要1个工作日", "terms": ["退款", "审核", "时效"]},
    {"id": "invoice-1", "text": "电子发票可在订单页下载", "terms": ["发票", "订单"]},
]
```

## 三、先写确定性相关度

```python
def score(query_terms, document):
    return len(set(query_terms) & set(document["terms"]))
```

然后过滤、排序、截断：

```python
results.sort(key=lambda item: (-item["score"], item["id"]))
return results[:k]
```

id 作为第二排序键非常重要：分数相同时结果仍可复现，便于缓存和测试。

把过滤、稳定排序和 Top-K 截断整理为 `solution.py` 中的 `retrieve_top_k`，并保持查询词与文档输入不被修改。

<!-- lab-check:implementation -->

## 四、换成真实向量检索时保持契约

后续可把 `score()` 替换为 embedding 相似度，把列表替换为向量数据库，但对图中下游节点仍返回：

```python
{"id": "来源ID", "text": "正文", "score": 0.83}
```

这样框架升级不会牵动回答与引用逻辑。

## 五、阈值不是越低越好

低相关文档会给模型制造错误上下文。`min_score` 应通过验证集调整；没有结果时允许返回空列表，下一节点负责澄清或转人工。

在 `app.py` 中导入 `retrieve_top_k`，并接入一个最小 LangGraph 检索节点：输入查询词，输出带 `id`、`text`、`score` 的证据列表。

<!-- lab-check:integration -->

## 六、实验任务

<!-- lab-check:acceptance -->

实验 4-1 实现 `retrieve_top_k`，私有用例会检查重复查询词、同分稳定排序、阈值与输入不可变。

## 七、验收

至少准备：高相关、同分、全低分、空文档、重复词、非法 k 六类场景。不要只拿一个“看起来能工作”的问题演示。

## 八、下一步

检索只是找到材料。下一节确保生成答案只引用实际使用的材料，并在无证据时安全降级。
