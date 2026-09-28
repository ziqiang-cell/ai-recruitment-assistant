# AI Recruitment Assistant — 2026-09-27 工作总结

## 1. 今日工作概览

今天主要完成了两个阶段的工作：

1. 完成并验证 **V4：结构化招聘分析**
2. 开始进入并理解 **V5：RAG 企业招聘知识库**

今天的重点已经从“让大模型能回答”进一步升级到了：

```text
大模型输出
↓
JSON 结构化
↓
Python 解析
↓
业务字段展示
↓
企业知识库检索增强
```

---

# 2. V4：结构化招聘分析

## 2.1 V4 核心目标

V3 中，DeepSeek 返回的是一大段自然语言。

V4 将其升级为固定 JSON：

```json
{
  "match_score": 0,
  "matched_requirements": [],
  "missing_requirements": [],
  "strengths": [],
  "risks": [],
  "interview_questions": [],
  "summary": ""
}
```

程序链路变为：

```text
JD + PDF 简历
↓
Prompt
↓
DeepSeek
↓
JSON 字符串
↓
json.loads()
↓
Python dict
↓
Streamlit 分字段展示
```

---

## 2.2 新增 analysis_parser.py

V4 新增：

```text
analysis_parser.py
```

主要职责：

```text
模型返回文本
↓
JSON 解析
↓
字段校验
↓
match_score 处理
↓
返回 Python dict
```

重点理解：

```python
json.loads(response_text)
```

含义：

```text
JSON 字符串
↓
Python dict
```

这样 app.py 才可以直接使用：

```python
analysis["match_score"]
analysis["strengths"]
analysis["summary"]
```

---

## 2.3 Prompt 结构化输出

prompt.py 中明确要求模型：

- 只返回 JSON
- 不返回 Markdown
- 不使用 ```json 代码块
- 不编造候选人经历
- 缺失能力写“未体现”或“需要确认”
- 固定字段名称和格式

这一阶段学到了一个很重要的概念：

> LLM 不仅可以生成自然语言，也可以作为结构化数据生成器。

---

## 2.4 V4 页面结果

Streamlit 页面已经能够分别展示：

```text
模型估算岗位匹配度
已匹配岗位要求
未体现或不足的岗位要求
候选人优势
风险与待确认事项
建议面试问题
总体总结
```

这使项目从：

```text
LLM 回答展示页面
```

升级成：

```text
具有固定业务结构的招聘分析系统
```

---

# 3. V4 匹配能力测试

今天使用同一个 JD 测试了两份不同简历。

## 低匹配简历

原有矿物加工 / 科研方向简历：

```text
匹配度：5 / 100
```

系统识别：

- Python 未体现
- LLM API 未体现
- Prompt Engineering 未体现
- RAG 未体现
- Git / Web / AI 项目未体现

同时仍然能够提取：

- 科研能力
- 实验能力
- 论文和英语能力

说明系统不会简单把“优秀科研经历”错误映射成“AI 应用开发能力”。

---

## 高匹配 AI 测试简历

生成了一份虚构测试简历，包含：

```text
Python
DeepSeek API
Prompt Engineering
RAG
Embedding
FAISS / Chroma
Streamlit
FastAPI
Git
Debug
GitHub
AI 项目经验
```

同一 JD 下：

```text
第一次：93 / 100
第二次：90 / 100
```

说明：

```text
低匹配简历：5
高匹配简历：90+
```

两者区分明显。

同时也认识到：

> match_score 是 LLM 根据证据生成的辅助评分，不等于真实录用概率。

模型存在一定随机性，因此 93 → 90 属于正常小幅波动。

---

# 4. 今日深入理解 JSON

今天重点理解了 JSON。

## JSON 是什么

JSON 是一种：

> 结构化文本数据格式。

例如：

```json
{
  "name": "张三",
  "age": 22,
  "skills": ["Python", "RAG"]
}
```

核心结构：

```text
key : value
```

例如：

```json
"match_score": 90
```

---

## JSON 与 Python dict

JSON：

```json
{
  "match_score": 90
}
```

Python dict：

```python
{
    "match_score": 90
}
```

两者外观很像，但：

```text
JSON
= 文本数据格式

Python dict
= Python 内存中的数据结构
```

---

## json.loads()

```python
json.loads()
```

作用：

```text
JSON 字符串
↓
Python 对象 / dict
```

---

## json.dumps()

```python
json.dumps()
```

作用：

```text
Python 对象
↓
JSON 字符串
```

---

# 5. V5：开始进入 RAG

今天正式开始理解并搭建：

# V5：RAG 企业招聘知识库

RAG 全称：

```text
Retrieval-Augmented Generation
```

中文：

```text
检索增强生成
```

核心思想：

> 先从企业自己的资料中检索相关内容，再把这些资料交给大模型进行回答。

---

# 6. 为什么招聘助手需要 RAG

V4：

```text
JD
+
候选人简历
↓
DeepSeek
```

问题：

```text
DeepSeek 不知道某家公司的内部招聘标准。
```

V5：

```text
JD
+
候选人简历
+
企业招聘知识库
↓
DeepSeek
```

这样模型可以根据：

- 企业岗位标准
- 面试评分规则
- 人才能力要求

辅助分析候选人。

---

# 7. RAG 核心概念

## 7.1 Knowledge Base

企业自己的知识资料，例如：

```text
knowledge_base/

ai_intern_recruitment_standard.md
interview_scoring_guide.md
company_talent_standard.md
```

---

## 7.2 Chunk

将长文档切成小块。

例如：

```text
chunk_size = 400
chunk_overlap = 80
```

大概效果：

```text
Chunk 0：0 ~ 399
Chunk 1：320 ~ 719
Chunk 2：640 ~ ...
```

Overlap 用于降低信息被切断的问题。

---

## 7.3 Embedding

Embedding 将文本转换成数字向量。

例如：

```text
"Python 开发"

↓

[0.21, -0.38, 0.72, ...]
```

语义越接近的文本，其向量通常越接近。

Embedding 使计算机能够进行：

```text
语义相似度比较
```

---

## 7.4 Vector Database

向量数据库用于存储：

```text
文本 Chunk
+
Embedding
+
metadata
```

V5 使用：

```text
ChromaDB
```

---

## 7.5 Similarity Search

用户输入岗位 JD 后：

```text
JD
↓
Embedding
↓
与数据库里的 Chunk 向量比较
↓
找最相关的 Top-K Chunk
```

这就是：

```text
Similarity Search
```

---

# 8. V5 新增 rag.py

当前新增：

```text
rag.py
```

它主要负责：

```text
知识库读取
Chunk 切分
Chroma 建库
向量存储
相似度检索
返回相关知识片段
```

---

# 9. rag.py 当前结构理解

## load_knowledge_documents()

功能：

```text
读取 knowledge_base/*.md / *.txt
```

返回：

```python
{
    "text": "...",
    "source": "文件名.md"
}
```

---

## chunk_text()

功能：

```text
长文本
↓
固定长度切块
↓
返回 chunks
```

---

## _get_collection()

作用：

```text
连接本地 ChromaDB
```

数据库目录：

```text
chroma_db/
```

collection：

```text
recruitment_standards
```

---

## build_or_update_knowledge_base()

完整入库过程：

```text
读取文档
↓
Chunk
↓
生成稳定 ID
↓
保存 metadata
↓
Chroma Embedding
↓
upsert
```

其中：

```text
upsert
=
存在则更新
不存在则插入
```

可避免每次启动都重复添加数据。

---

## retrieve_context()

当前核心检索函数：

```python
retrieve_context(query, top_k=4)
```

流程：

```text
岗位 JD
↓
Chroma query
↓
Similarity Search
↓
Top 4 Chunk
↓
返回：
text
source
chunk_index
```

---

# 10. V5 app.py 新链路

V4：

```text
JD
↓
PDF
↓
Prompt
↓
DeepSeek
```

V5：

```text
JD
↓
build_or_update_knowledge_base()
↓
retrieve_context(jd)
↓
企业招聘相关 Chunk
↓
PDF 简历解析
↓
build_prompt(jd, resume, retrieved_context)
↓
DeepSeek
↓
JSON
↓
analysis_parser
↓
Streamlit
```

---

# 11. RAG Debug 功能

V5 页面新增：

```text
显示 RAG 检索结果
```

checkbox。

勾选后可以看到：

```text
source
chunk_index
chunk text
```

这个功能的学习价值很高。

可以直接判断：

```text
模型回答不好
```

到底是：

```text
Retriever 找错资料
```

还是：

```text
Retriever 找对资料，但 LLM 使用不好
```

---

# 12. prompt.py 的 V5 变化

V4：

```python
build_prompt(jd, resume)
```

V5：

```python
build_prompt(jd, resume, retrieved_context)
```

Prompt 中现在包含：

```text
【岗位 JD】

【候选人简历】

【企业招聘知识库参考资料】
```

同时明确规定：

> 企业知识库是招聘标准，不是候选人的个人经历。

这是非常重要的约束。

避免模型产生类似错误：

```text
知识库要求 RAG
↓
错误认为候选人具备 RAG
```

---

# 13. knowledge_references

V5 JSON 新增：

```json
"knowledge_references": [
  {
    "source": "",
    "evidence": ""
  }
]
```

作用：

```text
显示本次招聘分析参考了哪些企业知识库资料
```

使分析结果更加：

```text
可解释
可追踪
可验证
```

---

# 14. allowed_sources

app.py 中增加：

```python
allowed_sources = {
    chunk["source"]
    for chunk in retrieved_chunks
}
```

随后传给：

```python
parse_analysis_response()
```

作用：

> 检查 DeepSeek 返回的知识库引用是否真的来自本次 Retriever 检索结果。

这样可以降低：

```text
模型虚构引用文件名
```

的问题。

---

# 15. 当前完整架构

当前项目整体已经演进为：

```text
                     企业招聘知识库
                           ↓
                        Chunk
                           ↓
                       Embedding
                           ↓
                        Chroma
                           ↓
                       Retrieval
                           ↓
                    Retrieved Context
                           │
                           │
岗位 JD ───────────────────┤
                           │
候选人 PDF → PDF Parser ──┤
                           ↓
                        Prompt
                           ↓
                       DeepSeek
                           ↓
                          JSON
                           ↓
                   analysis_parser
                           ↓
                     Streamlit Web
```

---

# 16. 当前版本进度

目前：

```text
V0  Prompt 构建                     ✅
V1  DeepSeek API                    ✅
V2  PDF 简历解析                    ✅
V3  Streamlit Web                   ✅
V4  JSON 结构化招聘分析             ✅
V5  RAG 企业招聘知识库              开发中
```

---

# 17. 今天学习到的核心知识

## LLM 应用

- Structured Output
- JSON
- Prompt 约束
- LLM 输出随机性
- 结构化字段验证

## RAG

- Knowledge Base
- Chunk
- Chunk Overlap
- Embedding
- Vector
- Vector Database
- ChromaDB
- Similarity Search
- Top-K
- Retrieved Context
- Metadata
- RAG Debug

## Python

- `json.loads()`
- dict
- list
- set
- Path
- 文件读取
- `zip()`
- `range()`
- 数据结构拼装

## 软件工程

- 知识库与候选人事实分离
- Retrieval 与 Generation 分离
- 引用来源校验
- Debug 可视化
- 模块职责拆分

---

# 18. 下一步工作

下一次继续 V5。

优先顺序：

```text
1. 检查 knowledge_base 中的 3 个 Markdown 文档

2. 安装并运行 chromadb

3. 启动 Streamlit

4. 勾选：
   显示 RAG 检索结果

5. 输入真实 AI 岗位 JD

6. 观察：
   Retriever 实际找到了哪些 Chunk

7. 检查：
   Prompt 是否正确加入 Retrieved Context

8. 验证：
   knowledge_references 是否正确

9. 测试：
   低匹配简历
   高匹配 AI 简历

10. V5 验收通过后：
    commit
    merge
    push
```

---

# 19. 今日总结

今天项目完成了一次非常重要的升级。

V4 让系统从：

```text
大模型生成文字
```

升级成：

```text
大模型生成结构化业务数据
```

V5 又开始进一步升级为：

```text
企业私有知识
↓
检索
↓
增强 Prompt
↓
大模型分析
```

当前项目已经不再只是：

> “调用一次 DeepSeek API 的 Demo”

而是在逐步形成：

> “具备文档处理、结构化输出、Web 交互和企业知识库检索能力的 AI 招聘应用”。

下一步重点不是继续堆功能，而是把：

```text
Chunk
→ Embedding
→ Chroma
→ Retrieval
→ Prompt
```

这条真实 RAG 链路完全跑通并看懂。
