# AI 招聘助手 V2

程序读取手动输入的岗位 JD，从 PDF 简历中提取文字，生成 Prompt，调用 DeepSeek API，并在终端打印招聘分析结果。

## 安装依赖

需要 Python 3。在本目录打开终端，运行：

```bash
python -m pip install -r requirements.txt
```

这会安装 V2 新增的 `pypdf`，以及项目原有的依赖。

如果 Windows 上 `python` 命令不可用，将命令中的 `python` 换成 `py`。

## 配置 API Key

1. 从 DeepSeek 平台获取 API Key。
2. 在项目目录复制 `.env.example`，把副本命名为 `.env`。
3. 打开 `.env`，在等号后填写自己的密钥，例如 `DEEPSEEK_API_KEY=你的密钥`。

`.env` 已写入 `.gitignore`，不要把真实密钥写进 Python 文件，也不要分享 `.env`。如果已经通过系统环境变量设置了 `DEEPSEEK_API_KEY`，可以不创建 `.env`。

## 运行

```bash
python main.py
```

先输入岗位 JD，可以输入多行；输入空行结束。然后输入 PDF 简历的文件路径，例如 `C:\Users\你\Documents\resume.pdf`。程序会提取简历文字，调用 API 并打印分析结果。JD 用空行作为结束标记，因此 JD 内容中暂时不要留空行。API 调用需要网络连接，可能产生费用。

目前只支持**包含可复制文字**的 PDF。扫描件或纯图片 PDF 无法提取文字，暂时不支持 OCR。如果提示“未提取到文字”，请换用文字版 PDF。

## 文件

- `main.py`：读取 JD 和 PDF 路径，调用 PDF 解析、Prompt 和大模型函数，打印分析结果。
- `pdf_parser.py`：逐页提取 PDF 中的文字，并提示常见文件错误。
- `prompt.py`：用 `build_prompt(jd, resume)` 拼接提示词。
- `llm.py`：读取 API Key，调用 DeepSeek，返回模型回答。
- `requirements.txt`：列出运行时需要安装的第三方包。
- `.env.example`：API Key 配置示例，不含真实密钥。
- `.gitignore`：避免将 `.env` 等本地文件加入 Git。

阅读代码时，先沿着 `main.py` 中的 `jd`、`pdf_path`、`resume_text`、`final_prompt` 和 `answer` 逐步追踪数据，再看 `pdf_parser.py` 如何逐页合并文字。
