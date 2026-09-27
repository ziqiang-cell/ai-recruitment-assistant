# AI 招聘助手 V4

可以在浏览器中输入岗位 JD、上传 PDF 简历，并按匹配度、岗位要求、优势、风险、面试问题和总结分别查看招聘分析。原有命令行版本仍可使用本地 PDF 路径，并打印格式化 JSON。

## 安装依赖

需要 Python 3。在本目录打开终端，运行：

```bash
python -m pip install -r requirements.txt
```

V4 不需要新增第三方依赖；JSON 解析使用 Python 标准库 `json`。

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

输入岗位 JD，以空行结束；再输入本地 PDF 简历路径，例如 `C:\Users\你\Documents\resume.pdf`。

Web 版本：

```bash
streamlit run app.py
```

浏览器打开终端显示的地址，输入岗位 JD、上传 PDF 简历，点击“开始分析”。结果会按字段分别显示。如果 `streamlit` 命令不可用，可以运行 `python -m streamlit run app.py`。API 调用需要网络连接，可能产生费用。

模型输出必须是指定结构的 JSON。如果模型返回无效 JSON、字段不完整或字段类型不正确，程序会显示中文提示，可重新尝试分析。匹配度是模型基于简历证据估算的辅助指标，不代表录用决定。

目前只支持**包含可复制文字**的 PDF。扫描件或纯图片 PDF 无法提取文字，暂时不支持 OCR。如果提示“未提取到文字”，请换用文字版 PDF。

## 文件

- `app.py`：Streamlit Web 入口，负责输入、校验、加载提示和结果展示。
- `main.py`：读取 JD 和 PDF 路径，调用 PDF 解析、Prompt 和大模型函数，打印分析结果。
- `pdf_parser.py`：从本地 PDF 路径或 Streamlit 上传文件中逐页提取文字。
- `prompt.py`：用 `build_prompt(jd, resume)` 拼接提示词，并要求固定 JSON 结构。
- `llm.py`：读取 API Key，调用 DeepSeek 的 JSON 输出模式，返回模型回答字符串。
- `analysis_parser.py`：把模型回答解析成 Python 字典，并检查字段与基本类型。
- `requirements.txt`：列出运行时需要安装的第三方包。
- `.env.example`：API Key 配置示例，不含真实密钥。
- `.gitignore`：避免将 `.env` 等本地文件加入 Git。

阅读 Web 代码时，沿着 `app.py` 中的 `jd`、`uploaded_file`、`resume_text`、`final_prompt`、`answer` 和 `analysis` 逐步追踪数据；`main.py` 是独立保留的命令行入口。
