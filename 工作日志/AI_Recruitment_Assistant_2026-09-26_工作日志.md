# AI Recruitment Assistant — 2026-09-26 工作日志

## 1. 今日工作目标

今天主要完成了 **V3：Streamlit Web 界面** 的开发、测试、验收和 Git 收尾。

在 V2 已经实现：

```text
岗位 JD
→ PDF 简历
→ PDF 文本解析
→ Prompt
→ DeepSeek API
→ 招聘分析结果
```

的基础上，今天将项目从命令行程序升级成了可在浏览器中使用的 Web 应用。

---

## 2. 今日完成内容

### 2.1 保留 CLI 版本

项目继续保留：

```text
main.py
```

作为命令行入口。

当前 CLI 版本仍可以通过：

```powershell
python main.py
```

运行。

作用：

- 输入岗位 JD
- 输入本地 PDF 简历路径
- 解析 PDF
- 调用 DeepSeek
- 输出招聘分析结果

保留 CLI 的意义是：

- 方便调试
- Web 出问题时仍可验证核心业务链路
- 前端与业务逻辑解耦

---

### 2.2 新增 Streamlit Web 入口

新增：

```text
app.py
```

作为 Streamlit Web 应用入口。

启动方式：

```powershell
streamlit run app.py
```

浏览器访问：

```text
http://localhost:8501
```

当前页面已经实现：

- 页面标题
- 项目简介
- 岗位 JD 多行输入框
- PDF 简历上传
- “开始分析”按钮
- 加载提示
- 招聘分析结果展示
- 输入异常提示

---

## 3. 当前 Web 流程

当前 V3 运行链路：

```text
浏览器
   ↓
输入岗位 JD
   ↓
上传 PDF 简历
   ↓
点击“开始分析”
   ↓
解析 PDF
   ↓
提取简历文本
   ↓
build_prompt()
   ↓
DeepSeek API
   ↓
招聘分析结果
   ↓
Streamlit 页面展示
```

---

## 4. app.py 核心结构

今天接触并理解了：

```python
import streamlit as st
```

含义：

```text
导入 streamlit 库
并将它简称为 st
```

所以：

```python
st.title()
st.write()
st.text_area()
st.file_uploader()
st.button()
st.spinner()
st.error()
st.markdown()
```

本质上都是调用 Streamlit 提供的 Web UI 功能。

---

## 5. 今天学习到的 Streamlit 基础

### `st.set_page_config()`

设置页面基本配置。

### `st.title()`

显示页面主标题。

### `st.write()`

显示普通文本。

### `st.text_area()`

创建多行文本输入框，用于输入岗位 JD。

### `st.file_uploader()`

上传 PDF 简历。

当前限制：

```python
type=["pdf"]
```

只允许上传 PDF。

### `st.button()`

创建“开始分析”按钮。

点击按钮后才执行招聘分析。

### `st.spinner()`

模型调用期间显示：

```text
正在分析候选人简历，请稍候...
```

让用户知道程序正在工作。

### `st.error()`

在页面显示错误提示。

例如：

- 岗位 JD 为空
- 未上传 PDF
- PDF 无法解析
- API Key 未配置

### `st.stop()`

发生输入错误后停止当前 Streamlit 执行流程。

### `st.markdown()`

用于展示 DeepSeek 返回的 Markdown 格式分析结果。

---

## 6. PDF 模块进一步重构

今天 `pdf_parser.py` 从只支持本地文件路径，升级成同时支持：

```text
CLI 本地 PDF
+
Streamlit 上传 PDF
```

当前主要结构：

```text
extract_text_from_pdf()
        ↓
CLI 使用

extract_text_from_uploaded_pdf()
        ↓
Streamlit 使用

_extract_text()
        ↓
两者共用的核心 PDF 文本提取逻辑
```

这样避免了把同样的 PDF 解析代码复制两份。

这是今天比较重要的软件工程改进：

> 不同入口复用同一套核心业务逻辑。

---

## 7. 当前项目模块职责

目前项目结构已经比较清晰：

```text
ai-recruitment-assistant/
│
├── main.py
├── app.py
├── prompt.py
├── llm.py
├── pdf_parser.py
├── requirements.txt
├── README.md
├── .env
├── .env.example
└── .gitignore
```

各文件职责：

```text
main.py
→ CLI 命令行入口

app.py
→ Streamlit Web 入口

prompt.py
→ 构建招聘分析 Prompt

llm.py
→ 调用 DeepSeek API

pdf_parser.py
→ PDF 文本解析

requirements.txt
→ Python 依赖

.env
→ DeepSeek API Key

.gitignore
→ 忽略敏感文件和虚拟环境
```

---

## 8. V3 功能测试

今天已经完成正常流程测试：

```text
输入岗位 JD
+
上传 test_resume.pdf
+
点击开始分析
```

结果：

- PDF 上传成功
- PDF 文本提取成功
- DeepSeek API 调用成功
- 页面成功显示招聘分析结果

模型成功读取到了真实简历中的：

- 科研项目经历
- 选矿药剂相关经历
- MestReNova
- Origin
- EndNote
- CET-6
- 数据分析和论文相关经历

说明：

```text
Uploaded PDF
→ Text
→ Prompt
→ DeepSeek
→ Web Result
```

链路真实有效。

---

## 9. 异常场景测试

今天还完成了两个基本异常测试。

### 场景 1：岗位 JD 为空

结果：

```text
页面正常提示：
请先输入岗位 JD
```

程序没有崩溃。

### 场景 2：未上传 PDF

结果：

```text
页面正常提示：
请先上传 PDF 简历
```

程序没有崩溃。

因此 V3 的基本输入校验通过。

---

## 10. V3 Git 工作流

今天继续使用功能分支开发：

```text
feature/streamlit-web
```

完成开发和测试后：

```text
feature/streamlit-web
        ↓
commit
        ↓
切回 main
        ↓
merge
        ↓
push GitHub
        ↓
删除 feature 分支
```

最终：

```text
main
```

已经成为最新稳定版本。

本地开发分支：

```text
feature/streamlit-web
```

已经成功删除。

---

## 11. 当前项目版本进度

目前已经完成：

```text
V0  Prompt 构建                    ✅
V1  DeepSeek API                   ✅
V2  PDF 简历解析                   ✅
V3  Streamlit Web                  ✅
```

当前项目已经具备：

```text
Web 页面
+
PDF 上传
+
LLM 调用
+
招聘分析
+
异常提示
+
Git / GitHub 版本管理
```

已经从“代码 Demo”逐步变成一个可以演示的 AI 应用原型。

---

## 12. 今天重点学习到的知识

### Python

- import
- 模块别名
- 函数复用
- 文件对象
- `seek(0)`
- 异常处理
- 模块拆分

### Streamlit

- `st.title()`
- `st.write()`
- `st.text_area()`
- `st.file_uploader()`
- `st.button()`
- `st.spinner()`
- `st.error()`
- `st.stop()`
- `st.markdown()`

### 软件工程

- CLI 与 Web 双入口
- UI 与业务逻辑分离
- 公共函数复用
- 功能分支开发
- merge
- push
- 删除已完成分支

---

## 13. 当前还没有做的内容

目前仍未进入：

```text
结构化招聘分析
RAG
LangChain
FastAPI
数据库
Agent
OCR
多简历比较
复杂 UI
Docker
正式部署
```

当前不急于增加这些功能。

---

## 14. 下一步计划

明天建议进入：

# V4：结构化招聘分析

目标是把当前 DeepSeek 返回的长文本：

```text
匹配要求
尚未体现的要求
总体判断
```

进一步升级成稳定的业务结构，例如：

```text
综合匹配度

技能匹配

优势

不足

推荐面试问题

总体判断
```

后续 Web 页面可以进一步展示为更清晰的结构化招聘分析结果。

建议下一次开发时创建新分支：

```powershell
git switch -c feature/structured-analysis
```

---

## 15. 今日总结

今天最重要的成果不是单纯“做了一个网页”，而是完成了项目结构上的一次升级：

```text
CLI
+
Web
+
共享业务模块
```

当前整体架构已经变成：

```text
                 ┌── main.py
                 │   CLI
用户入口 ─────────┤
                 │
                 └── app.py
                     Web
                      │
                      ↓
            ┌─────────────────┐
            │ prompt.py       │
            │ llm.py          │
            │ pdf_parser.py   │
            └─────────────────┘
```

项目当前状态：

```text
V3 完成并已合并到 main
GitHub 已同步
工作分支已清理
```

明天从 **V4：结构化招聘分析** 继续。
