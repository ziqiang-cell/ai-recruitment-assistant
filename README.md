# AI 招聘助手 V5

输入岗位 JD 和 PDF 简历后，程序先检索企业招聘知识库，再调用 DeepSeek 生成结构化招聘分析。CLI 版本仍可使用本地 PDF 路径。

V5 的 RAG 流程：招聘文档 → 固定长度 Chunk → 本地 Embedding → Chroma → Similarity Search → Prompt → LLM。候选人的能力和经历仍只根据简历判断。

## 安装依赖

需要 Python 3。在本目录打开终端，运行：

```bash
python -m pip install -r requirements.txt
```

V5 新增 `chromadb`。首次构建知识库时，Chroma 的本地默认 Embedding 模型可能需要下载；之后数据库保存在项目的 `chroma_db/` 中。

如果 Windows 上 `python` 命令不可用，将命令中的 `python` 换成 `py`。

## 配置 API Key

1. 从 DeepSeek 平台获取 API Key。
2. 在项目目录复制 `.env.example`，把副本命名为 `.env`。
3. 打开 `.env`，在等号后填写自己的密钥，例如 `DEEPSEEK_API_KEY=你的密钥`。

`.env` 已写入 `.gitignore`，不要把真实密钥写进 Python 文件，也不要分享 `.env`。如果已经通过系统环境变量设置了 `DEEPSEEK_API_KEY`，可以不创建 `.env`。

## 运行

命令行版本：

```bash
python main.py
```

输入岗位 JD，以空行结束；再输入本地 PDF 简历路径，例如 `C:\Users\你\Documents\resume.pdf`。CLI 会输出 JSON 和知识库参考依据。

Web 版本：

```bash
streamlit run app.py
```

浏览器打开终端显示的地址，输入岗位 JD、上传 PDF 简历，点击“开始分析”。侧边栏勾选“显示 RAG 检索结果”，可查看实际检索到的来源、片段序号和文本；默认不显示。如果 `streamlit` 命令不可用，可以运行 `python -m streamlit run app.py`。DeepSeek API 调用需要网络连接，可能产生费用。

模型输出必须是指定结构的 JSON，包含 `knowledge_references`。如果模型返回无效 JSON、字段不完整或引用了未检索到的来源，程序会显示中文提示。匹配度是模型基于简历证据估算的辅助指标，不代表录用决定。

`knowledge_base/` 存放企业招聘资料，当前三个 Markdown 文件都是虚构的测试标准，可加入 UTF-8 编码的 `.md` 或 `.txt` 文件。`chroma_db/` 是本地生成的向量数据库，已加入 `.gitignore`；修改知识库文档后再次分析会按稳定片段 ID 更新入库内容。

目前只支持**包含可复制文字**的 PDF。扫描件或纯图片 PDF 无法提取文字，暂时不支持 OCR。如果提示“未提取到文字”，请换用文字版 PDF。

## 文件

- `app.py`：Streamlit Web 入口，负责输入、RAG 调试开关和结构化结果展示。
- `main.py`：命令行入口，读取 JD 和 PDF 路径，检索知识库并打印分析结果。
- `pdf_parser.py`：从本地 PDF 路径或 Streamlit 上传文件中逐页提取文字。
- `rag.py`：读取与切分知识库文档，写入 Chroma，并按 JD 检索相关片段。
- `knowledge_base/`：三个虚构的招聘标准测试文档。
- `prompt.py`：用 `build_prompt(jd, resume, retrieved_context)` 拼接提示词，并要求固定 JSON 结构。
- `llm.py`：读取 API Key，调用 DeepSeek 的 JSON 输出模式，返回模型回答字符串。
- `analysis_parser.py`：把模型回答解析成 Python 字典，并检查字段与基本类型。
- `requirements.txt`：列出运行时需要安装的第三方包。
- `.env.example`：API Key 配置示例，不含真实密钥。
- `.gitignore`：避免将 `.env` 等本地文件加入 Git。

阅读 Web 代码时，沿着 `jd`、`retrieved_chunks`、`resume_text`、`final_prompt`、`answer` 和 `analysis` 逐步追踪数据。
