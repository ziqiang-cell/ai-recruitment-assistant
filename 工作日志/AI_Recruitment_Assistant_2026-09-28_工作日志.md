# AI Recruitment Assistant — 2026-09-28 工作日志

## 1. 今日工作概览

今天主要完成了两件事：

1. 完成 **V5：RAG 企业招聘知识库** 的完整测试与验收
2. 规划并设计 **V6：RAG 基础工程化** 的开发范围

当前项目已经从：

```text
V4：
JD + 简历
→ DeepSeek
→ JSON
→ 结构化招聘分析
```

升级为：

```text
V5：
企业招聘知识库
→ Chunk
→ Embedding
→ Chroma
→ Retrieval
→ Retrieved Context
→ JD + 简历 + 企业招聘标准
→ DeepSeek
→ JSON
→ 结构化招聘分析
→ Knowledge References
```

---

# 2. V5：RAG 企业招聘知识库

## 2.1 V5 核心目标

V5 的目标是：

> 让招聘助手不再只依赖岗位 JD 和候选人简历，而是能够结合企业自己的招聘标准进行分析。

当前知识库包括：

```text
knowledge_base/
├── ai_intern_recruitment_standard.md
├── interview_scoring_guide.md
└── company_talent_standard.md
```

分别用于：

```text
ai_intern_recruitment_standard.md
→ AI 应用开发岗位技术能力标准

interview_scoring_guide.md
→ 面试能力参考权重

company_talent_standard.md
→ 学习能力、Debug、沟通、项目理解等通用标准
```

---

# 3. 今天真正跑通的 RAG 链路

完整链路：

```text
企业招聘文档
↓
load_knowledge_documents()
↓
chunk_text()
↓
Chunk
↓
Embedding
↓
ChromaDB
↓
岗位 JD
↓
Similarity Search
↓
Top-K Chunk
↓
Retrieved Context
↓
Prompt Augmentation
↓
DeepSeek
↓
JSON
↓
analysis_parser
↓
Streamlit
```

这说明 V5 已经不再只是“代码结构完成”，而是实际完成了：

```text
Indexing
+
Retrieval
+
Augmentation
+
Generation
```

四个完整阶段。

---

# 4. rag.py 的当前职责

今天重点理解了：

```text
rag.py
```

主要负责：

```text
知识库读取
Chunk 切分
Chroma 建库
向量存储
相似度检索
返回相关知识片段
```

---

## 4.1 load_knowledge_documents()

作用：

```text
读取 knowledge_base/*.md / *.txt
```

返回：

```python
{
    "text": "...",
    "source": "ai_intern_recruitment_standard.md"
}
```

---

## 4.2 chunk_text()

当前使用类似：

```text
chunk_size = 400
chunk_overlap = 80
```

作用：

```text
长文档
↓
切成多个较小 Chunk
```

Overlap 的意义：

> 减少关键信息刚好被切断造成的上下文损失。

---

## 4.3 ChromaDB

当前使用：

```text
ChromaDB
```

作为本地向量数据库。

本地生成：

```text
chroma_db/
```

该目录用于保存：

```text
Chunk
+
Embedding
+
metadata
```

其中 metadata 包含：

```text
source
chunk_index
```

---

## 4.4 build_or_update_knowledge_base()

当前作用：

```text
读取企业招聘文档
↓
切 Chunk
↓
生成稳定 ID
↓
Chroma Embedding
↓
upsert
```

稳定 ID 例如：

```text
ai_intern_recruitment_standard.md::0
```

这样重复运行时不会无限插入完全相同的数据。

---

## 4.5 retrieve_context()

当前函数：

```python
retrieve_context(jd, top_k=4)
```

主要流程：

```text
岗位 JD
↓
Embedding
↓
与 Chroma 中已有 Chunk 向量比较
↓
Similarity Search
↓
返回 Top-K
```

返回结构类似：

```python
[
    {
        "text": "...",
        "source": "xxx.md",
        "chunk_index": 0
    }
]
```

---

# 5. 为什么当前 JD 会检索出这些 Chunk

今天实际观察到的检索结果包括：

```text
ai_intern_recruitment_standard.md
interview_scoring_guide.md
company_talent_standard.md
```

这是合理的。

原因是当前 JD 主要包含：

```text
Python
LLM API
Prompt Engineering
RAG
Git
Web
Debug
项目能力
学习能力
沟通能力
```

而三个知识库文件分别覆盖：

```text
AI 岗位硬技能
面试评价能力
企业通用能力
```

因此它们与当前 JD 语义高度相关。

---

# 6. Embedding 与语义检索

今天进一步明确：

RAG 并不是简单做：

```text
关键词完全匹配
```

而是：

```text
文本
↓
Embedding
↓
向量
↓
语义距离比较
```

例如：

JD：

```text
要求完整 RAG 项目开发经验
```

知识库：

```text
了解 Chunk、Embedding、向量检索和答案生成流程
```

文字并不完全相同，但语义接近，所以仍然能被检索出来。

---

# 7. RAG Debug 页面验证

今天使用 Streamlit sidebar 中的：

```text
显示 RAG 检索结果
```

成功查看了 Retriever 实际返回的：

```text
source
chunk_index
chunk text
```

这一步很重要，因为以后可以判断：

```text
回答不好
```

到底是：

```text
Retriever 找错资料
```

还是：

```text
Retriever 找对了，但 LLM 使用不好
```

---

# 8. Knowledge References 验证

V5 的 JSON 新增：

```json
"knowledge_references": [
  {
    "source": "",
    "evidence": ""
  }
]
```

今天成功验证：

最终页面中的知识库引用来源，与真实 Retriever 返回的文件一致。

实际出现：

```text
ai_intern_recruitment_standard.md
interview_scoring_guide.md
company_talent_standard.md
```

没有出现不存在的来源。

---

# 9. allowed_sources 的作用

app.py 中：

```python
allowed_sources = {
    chunk["source"]
    for chunk in retrieved_chunks
}
```

再传入：

```python
parse_analysis_response()
```

作用：

> 检查 DeepSeek 最终返回的 knowledge_references.source，是否真的来自本次 RAG 检索结果。

这可以降低：

```text
模型虚构引用来源
```

的问题。

---

# 10. 同 JD、不同简历测试

今天完成了：

```text
同一个 JD
+
低匹配简历
```

以及：

```text
同一个 JD
+
高匹配 AI 简历
```

的测试。

结果符合预期：

```text
RAG 检索结果
→ 基本相同

候选人匹配分析
→ 明显不同
```

这说明当前系统正确区分：

```text
企业招聘标准
```

与：

```text
候选人事实
```

Retriever 当前只根据：

```text
JD
```

查企业标准。

候选人简历只在后续 DeepSeek 分析阶段参与判断。

---

# 11. 不相关岗位测试

今天还测试了：

```text
有机化学实验研发实习生
```

这类与 AI 知识库不相关的 JD。

观察到一个非常重要的现象：

> Top-K 仍然会返回若干 Chunk。

这是正常的。

因为：

```text
Top-K
```

表示：

> 在当前知识库中排名最靠前的 K 个。

并不表示：

> 这 K 个一定绝对相关。

因此：

```text
Top-K
≠
绝对相关
```

这也成为 V6 的主要改进方向。

---

# 12. V5 当前验收结果

当前 V5 已验证：

```text
Knowledge Base              ✅
Chunk                       ✅
Embedding                   ✅
ChromaDB                    ✅
Similarity Search           ✅
Top-K Retrieval             ✅
RAG Debug                   ✅
Retrieved Context → Prompt  ✅
Generation                  ✅
JSON Structured Output      ✅
Knowledge References        ✅
Source Validation           ✅
同 JD 不同 Resume 测试       ✅
不相关 JD 测试               ✅
```

因此：

# V5 正式验收通过

---

# 13. 当前项目版本进度

目前：

```text
V1  DeepSeek API                    ✅
V2  PDF Resume Parsing              ✅
V3  Streamlit Web                   ✅
V4  Structured JSON Analysis        ✅
V5  RAG Recruitment Knowledge Base  ✅
V6  RAG Engineering                 待开发
```

---

# 14. 今天规划的 V6

今天已经明确：

V6 不继续堆：

```text
Agent
Hybrid Search
Reranker
LangChain
FastAPI
数据库
```

而是先进行：

# RAG 基础工程化

V6 只解决几个已经真实观察到的问题。

---

## 14.1 Retrieval Distance

当前 V5 只能看到：

```text
Top-K 结果
```

V6 计划增加：

```text
distance
```

例如：

```text
来源：ai_intern_recruitment_standard.md
片段：0
向量检索距离：0.4231
```

作用：

> 观察不同 Chunk 与 Query 的向量距离。

注意：

```text
distance
```

不是：

```text
概率
准确率
匹配百分比
```

只能作为：

```text
向量检索距离
```

理解。

---

## 14.2 max_distance

V6 计划给：

```python
retrieve_context()
```

增加：

```python
max_distance=None
```

默认：

```text
None
```

保持 V5 Top-K 行为。

启用后：

```text
只保留 distance <= max_distance 的 Chunk
```

主要用于研究：

```text
不相关 JD
↓
如何避免强行返回过远的 Chunk
```

---

# 15. 为什么阈值不能随便定

今天明确：

不能直接认为：

```text
distance < 1
=
一定相关
```

因为距离范围会受到：

```text
Embedding 模型
距离指标
知识库内容
Chunk 方式
Query
```

影响。

因此 V6 中：

```text
max_distance
```

只能作为：

> 实验参数。

需要实际观察和校准。

---

# 16. 知识库重建问题

V5 当前使用：

```text
稳定 ID + upsert
```

可以避免重复数据。

但存在一个工程问题：

如果：

```text
原文有 5 个 Chunk
```

后来文件变短：

```text
只剩 3 个 Chunk
```

那么：

```text
旧 Chunk 3
旧 Chunk 4
```

可能仍残留在 Chroma。

因此 V6 计划增加：

```python
rebuild_knowledge_base()
```

流程：

```text
删除 recruitment_standards collection
↓
重新建立
↓
读取当前真实知识库文件
↓
重新 Chunk
↓
重新写入 Chroma
```

---

# 17. ensure_knowledge_base()

当前 V5 每次点击：

```text
开始分析
```

都会：

```text
build_or_update_knowledge_base()
```

V6 计划新增：

```python
ensure_knowledge_base()
```

逻辑：

```text
如果已有 Chunk
↓
直接使用

如果为空
↓
才建立知识库
```

避免每次分析都重复执行全量 upsert。

---

# 18. 知识库状态

V6 计划增加：

```python
get_knowledge_base_status()
```

返回：

```python
{
    "file_count": 3,
    "chunk_count": 7
}
```

Streamlit sidebar 可以直接显示：

```text
知识库文件：3
向量 Chunk：7
```

同时增加：

```text
重建知识库
```

按钮。

---

# 19. RAG Smoke Test

V6 计划新增：

```text
rag_smoke_test.py
```

不调用 DeepSeek。

只测试：

```text
Retriever
```

计划测试：

```text
Query 1
AI 应用岗位

Query 2
学习能力 / Debug / 沟通

Query 3
有机化学岗位
```

打印：

```text
source
chunk_index
distance
text preview
```

目的：

> 独立验证 Retrieval，而不需要每次启动整个 Web 应用。

---

# 20. 当前完整项目理解

目前系统已经形成：

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

# 21. 今日学习重点

今天真正理解的知识包括：

## RAG

```text
Knowledge Base
Chunk
Chunk Overlap
Embedding
Vector Database
ChromaDB
Similarity Search
Top-K
Retrieved Context
Prompt Augmentation
Knowledge References
Source Validation
```

## RAG 工程问题

```text
Top-K 不等于绝对相关
需要观察 distance
阈值需要实验校准
旧 Chunk 可能残留
需要知识库重建
Retriever 应该能独立测试
```

## 软件工程

```text
Retrieval 与 Generation 分离
企业知识与候选人事实分离
模型引用来源需要程序校验
Debug 页面对于 RAG 很重要
```

---

# 22. 下一步工作

下一次正式进入：

# V6：RAG 基础工程化

按照以下顺序：

```text
1. 创建 feature/rag-engineering 分支

2. 修改 rag.py
   - distance
   - max_distance
   - ensure_knowledge_base()
   - rebuild_knowledge_base()
   - get_knowledge_base_status()

3. 修改 app.py
   - RAG distance Debug
   - 可选 distance threshold
   - 知识库状态
   - 重建知识库按钮

4. 修改 main.py
   - 使用 ensure_knowledge_base()

5. 新增 rag_smoke_test.py

6. 测试：
   AI JD
   通用能力 Query
   化学 JD
   知识库重建
   Smoke Test

7. V6 验收后再 Git commit / merge / push
```

---

# 23. 今日总结

今天最重要的成果是：

> V5 已经从“理论上的 RAG”变成了真正经过检索、引用、低高匹配测试和不相关 Query 测试的完整 RAG 系统。

项目目前已经不只是：

```text
调用 DeepSeek
```

而是：

```text
企业知识库
+
向量检索
+
招聘标准增强
+
候选人分析
+
结构化输出
+
引用校验
```

下一阶段重点不再是“让功能更多”，而是：

> 让 RAG 更可观察、更稳定、更容易维护和调试。
