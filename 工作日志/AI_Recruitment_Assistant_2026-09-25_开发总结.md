# AI Recruitment Assistant — 2026-09-25 开发总结

## 1. 今日目标

今天完成了 AI 招聘助手从 **V0 → V1 → V2** 的基础开发闭环，并完成了 Git / GitHub 项目管理流程。

项目当前已经能够：

- 接收岗位 JD
- 读取候选人 PDF 简历
- 提取 PDF 文本
- 构建招聘分析 Prompt
- 调用 DeepSeek API
- 输出候选人与岗位的匹配分析
- 使用 Git 进行版本管理
- 将项目推送到 GitHub

---

## 2. 当前项目结构

```text
ai-recruitment-assistant/
│
├── .env
├── .env.example
├── .gitignore
├── .venv/
│
├── main.py
├── prompt.py
├── llm.py
├── pdf_parser.py
│
├── README.md
└── requirements.txt
```

说明：

- `.env`：保存真实的 `DEEPSEEK_API_KEY`，禁止上传 GitHub
- `.env.example`：环境变量示例文件，可上传 GitHub
- `.gitignore`：忽略 `.env`、`.venv/`、`__pycache__/`、`*.pyc`
- `main.py`：程序主入口
- `prompt.py`：构建招聘分析 Prompt
- `llm.py`：调用 DeepSeek API
- `pdf_parser.py`：读取并提取 PDF 简历文本
- `requirements.txt`：项目依赖
- `README.md`：项目说明

---

## 3. V0：完成 Prompt 构建

最初版本实现：

```text
输入岗位 JD
      ↓
输入候选人简历文本
      ↓
build_prompt()
      ↓
输出最终 Prompt
```

学习和接触的 Python 基础包括：

- `def` 函数
- 参数与返回值
- `input()`
- `print()`
- `list`
- `append()`
- `while`
- `if`
- `break`
- `return`
- `join()`
- f-string
- Python 模块导入

核心代码关系：

```text
main.py
   ↓
prompt.py
   ↓
build_prompt(jd, resume)
```

---

## 4. V1：接入 DeepSeek API

V1 将项目从“生成 Prompt”升级为真正的 LLM 应用：

```text
JD + Resume
     ↓
build_prompt()
     ↓
final_prompt
     ↓
get_ai_response()
     ↓
DeepSeek API
     ↓
招聘分析结果
```

新增：

```text
llm.py
```

主要职责：

- 加载 `.env`
- 获取 `DEEPSEEK_API_KEY`
- 创建 DeepSeek API Client
- 发送 Prompt
- 获取模型回答
- 处理 API 调用异常

接触的重要概念：

- API
- API Key
- Request
- Response
- 环境变量
- `.env`
- `python-dotenv`
- OpenAI Compatible API
- `try / except`
- 第三方 Python SDK

---

## 5. API Key 安全配置

项目使用：

```text
.env
```

保存真实 API Key：

```text
DEEPSEEK_API_KEY=真实Key
```

同时使用：

```text
.env.example
```

作为示例：

```text
DEEPSEEK_API_KEY=your_api_key_here
```

`.gitignore` 当前配置：

```gitignore
.env
.venv/
__pycache__/
*.pyc
```

目的：

- 防止 API Key 泄露
- 防止虚拟环境上传 GitHub
- 防止 Python 缓存文件进入仓库

---

## 6. 解决 SOCKS / httpx 依赖问题

首次调用 DeepSeek API 时出现：

```text
ImportError: Using SOCKS proxy, but the 'socksio' package is not installed
```

定位原因：

```text
OpenAI SDK
   ↓
httpx
   ↓
检测到 SOCKS Proxy
   ↓
缺少 socksio
```

解决：

```powershell
python -m pip install "httpx[socks]"
```

并计划将依赖写入：

```text
requirements.txt
```

该问题是今天第一次完整经历：

```text
运行程序
↓
读取 Traceback
↓
定位最后一行报错
↓
分析依赖问题
↓
安装缺失依赖
↓
重新运行
↓
成功
```

---

## 7. V1 成功结果

V1 已成功实现：

```text
用户输入 JD
      ↓
用户输入简历
      ↓
Python
      ↓
Prompt
      ↓
DeepSeek API
      ↓
LLM
      ↓
招聘分析结果
```

成功输出了：

- 匹配的岗位要求
- 尚未体现或不匹配的要求
- 总体判断及理由

至此完成第一个真正的 LLM Application 最小闭环。

---

## 8. Git 初始化与版本管理

项目完成 Git 初始化：

```powershell
git init -b main
```

配置 Git 用户信息：

```powershell
git config --global user.name "ziqiang-cell"
git config --global user.email "..."
```

完成第一次提交：

```powershell
git add .
git commit -m "feat: complete V1 DeepSeek API integration"
```

提交记录：

```text
ffab6c2 feat: complete V1 DeepSeek API integration
```

此时：

```text
git status
```

显示：

```text
nothing to commit, working tree clean
```

说明本地 V1 版本已经成功保存。

---

## 9. GitHub 远程仓库配置

GitHub 已创建公开仓库：

```text
ai-recruitment-assistant
```

本地绑定远程仓库：

```powershell
git remote add origin https://github.com/ziqiang-cell/ai-recruitment-assistant.git
```

检查：

```powershell
git remote -v
```

完成：

```text
本地 Git
   ↓
origin
   ↓
GitHub Repository
```

---

## 10. 解决 GitHub Push 代理问题

第一次执行：

```powershell
git push -u origin main
```

出现：

```text
Failed to connect to github.com port 443 via 127.0.0.1
```

检查 Git 全局配置发现：

```text
http.proxy=http://127.0.0.1:7890
https.proxy=http://127.0.0.1:7890
```

进一步测试：

```powershell
Test-NetConnection 127.0.0.1 -Port 7890
```

结果：

```text
TcpTestSucceeded : False
```

说明本地 `7890` 代理端口没有服务。

解决：

```powershell
git config --global --unset http.proxy
git config --global --unset https.proxy
```

之后重新：

```powershell
git push -u origin main
```

成功。

GitHub 输出确认：

```text
[new branch] main -> main
branch 'main' set up to track 'origin/main'
```

至此完成：

```text
本地代码
↓
git add
↓
git commit
↓
git push
↓
GitHub
```

---

## 11. V2：PDF 简历解析

V2 的目标是将“手工输入简历”升级为“读取真实 PDF 简历”。

流程：

```text
岗位 JD
   ↓
PDF 简历路径
   ↓
Python 读取 PDF
   ↓
提取简历文字
   ↓
build_prompt()
   ↓
DeepSeek API
   ↓
招聘分析结果
```

新增：

```text
pdf_parser.py
```

使用：

```text
pypdf
```

负责：

- 接收 PDF 文件路径
- 打开 PDF
- 逐页读取
- 提取文本
- 合并文本
- 返回简历内容

---

## 12. V2 测试结果

实际使用测试 PDF：

```text
D:\PythonProject\test_resume.pdf
```

程序成功：

1. 读取 PDF
2. 提取候选人简历信息
3. 将文本传给 Prompt
4. 调用 DeepSeek
5. 输出招聘匹配分析

模型成功识别出了 PDF 中的真实信息，例如：

- 科研项目经历
- 数据汇总
- 谱图解析
- 绘图
- 论文撰写
- MestReNova
- Origin
- EndNote
- CET-6
- 选矿药剂研发方向

说明：

```text
PDF
↓
Text Extraction
↓
LLM
```

链路已经真正跑通。

---

## 13. 当前项目版本状态

目前项目能力：

```text
V0  Prompt 构建                  ✅
V1  DeepSeek API 调用            ✅
V1  .env / API Key 安全管理      ✅
V1  Git 本地版本管理             ✅
V1  GitHub 远程仓库              ✅
V2  PDF 简历解析                 ✅
V2  PDF → LLM 招聘分析           ✅
```

当前还未进入：

```text
Streamlit Web
RAG
数据库
FastAPI
Agent
OCR
多简历批量分析
```

这些暂时没有必要提前加入。

---

## 14. 今天实际学习到的核心能力

### Python

- 函数
- 参数
- 返回值
- list
- while
- if
- 异常处理
- 模块导入
- 第三方依赖
- 文件路径
- PDF 读取

### LLM 应用开发

- Prompt
- API
- API Key
- Request / Response
- DeepSeek API
- OpenAI Compatible SDK
- 环境变量
- LLM Application 基本调用链

### 软件工程

- 模块拆分
- `.env`
- `.gitignore`
- `requirements.txt`
- 虚拟环境
- Git
- commit
- branch
- remote
- push
- GitHub

### Debug

今天解决了两个真实工程问题：

1. `httpx` 缺少 SOCKS 支持
2. Git 全局代理指向失效的 `127.0.0.1:7890`

---

## 15. 明天继续的位置

明天先不要直接进入 RAG。

建议从当前 V2 继续：

```text
第一步
检查 main.py 与 pdf_parser.py
↓

第二步
真正理解 PDF 解析代码
↓

第三步
提交 V2 Git Commit
↓

第四步
将 feature/pdf-resume 合并回 main
↓

第五步
Push 到 GitHub
↓

第六步
进入 V3
```

V2 建议提交信息：

```powershell
git add .
git commit -m "feat: add PDF resume parsing"
```

如果当前正在：

```text
feature/pdf-resume
```

分支，下一步学习：

```text
feature/pdf-resume
      ↓
commit
      ↓
merge
      ↓
main
      ↓
push GitHub
```

---

## 16. 下一阶段规划

后续建议版本路线：

```text
V1
文本 + DeepSeek API
        ✅
        ↓
V2
PDF 简历解析
        ✅
        ↓
V3
Streamlit Web 界面
        ↓
V4
JD / Resume 结构化抽取
        ↓
V5
RAG 招聘知识库
        ↓
V6
FastAPI + 数据库
        ↓
V7
Docker + 测试 + 部署
        ↓
V8
Agent / 更复杂工作流
```

当前原则：

> 不追求一次把项目做复杂，而是保证每一个版本都能运行、能解释、能提交、能在面试中讲清楚。
