# AI Recruitment Assistant — 2026-10-15 V6 验收收尾日志

本日志依据已审核的收尾准备包正式落盘，于文档提交前形成。文档提交是否成功及其 SHA 以 Git 历史和本轮交付包为准；截至本日志落盘时，main 尚未合并，远端尚未推送。本轮不新增运行测试，不改变第二轮验收结论。

## 1. 版本与范围

V6 为 RAG 基础工程化：返回并展示检索距离，默认关闭的 max_distance 过滤，ensure 空库构建／非空复用，指定 collection 手动重建，知识库文件数／Chunk 数，三类 Query smoke，保留 CLI、Web 与空检索兼容。

代码提交：`cae600b179421789ad5f31d21db651e994b90384`；分支 feature/rag-engineering。准备时 main 为 `7ec9d37a131c01cb46507430a6b9bb573df7dcf3`，尚未合并。本轮仅归档文档并获准创建一次文档提交，不修改 Python 源码、原始数据库或知识库。

## 2. 验收环境

Windows，项目 .venv Python 3.14.0。实际版本：openai 3.19.2, python-dotenv 1.2.3, httpx 0.28.1, pypdf 6.19.0, streamlit 1.64.0, chromadb 1.5.9, socksio 1.0.0, onnxruntime 1.30.0。

默认 shell 曾指向 Anaconda 3.12.7，因此验收明确使用 .venv。无依赖安装升级、无模型下载。

## 3. 第二轮实际测试

最终有效用例 42 项：**40 PASS、0 FAIL、2 BLOCKED**，含隔离防护与交付 ZIP 校验。必要用例没有失败或阻塞；两个非必要执行项是策略排除的真实 API／完整生产链和真实浏览器／部署。

真实 Chroma 1.5.9 与默认本地 ONNX all-MiniLM-L6-v2，在独立路径和现有模型缓存副本中实测，未替换 Embedding。三文件四 Chunk；验证空库建库、非空复用、三 Query、有限距离、Top-K、阈值、重复 upsert、重建和其他 collection 保留。

独立重建场景：缩短文档后 3 文件／3 Chunk，删一文件后 2／2，全删后 0／0。不是在原始数据库执行。

Python parser／Prompt／来源拒绝真实执行；阈值精确边界另有 Mock DB。CLI 使用实际入口、虚构 PDF、真实隔离 RAG、Mock LLM。Web 使用真实 Streamlit AppTest 与上传控件、真实 PDF 解析及隔离 Chroma；模型响应全部 Mock。

首轮 11 个 Web 用例被测试网络防护拦截 Windows 内部 socketpair，记录为 harness 失败并保留证据；调整项目外防护后仅重试这些用例，全部通过。最终不重复计数、不隐藏首轮证据。

## 4. 限制与结论

结论：**CONDITIONAL PASS（V6 隔离功能有条件通过）**。

未调用真实 DeepSeek，不证明当前密钥、账户、API 或模型质量；AppTest 不等于真实浏览器验收。原始 Chroma 未打开，不证明原库健康。没有生产部署、并发、故障中断恢复或系统检索准确率验收。

## 5. 原始保护与引用差异

第二轮保护前后清单一致：源码、原知识库、工作日志、原 Chroma、默认模型缓存、Git；.env 仅元数据，未读密钥。

收尾准备阶段发现验收之后 `.git/refs` 集合不同。专项审计分类 B：refs/codex/turn-diffs 两旧路径删除、两新路径新增，均指向同一 tree `94cb49a6a32d49cb63a4d2c50dec0e50aae0aed6`。内容摘要与目标不变，HEAD／main／feature／origin-main 不变，源文件保护一致。允许准备文档；具体写入进程未取证，不宣称还原进程因果。

## 6. 验收归档

- 交付文件：AI_Recruitment_Assistant_V6_Acceptance_Delivery.zip。
- SHA256：`dfeb6787ff37d65f58c69ef2ee6feb124382f0a3460705850b32425afddf7f3a`。
- 项目外已有归档，未将 ZIP、数据库、模型缓存或 .env 加入 Git。需用户选择长期备份位置。
- 当前收尾准备包：AI_Recruitment_Assistant_V6_Git_Closeout_Prep.zip；属于草稿准备，不是 Git 发布证明。

## 7. 风险与后续

Top-K 不保证相关、1.0 非最佳阈值；引用仅校验文件名；重建异常可能留空／部分库；非空 ensure 不同步文件修改；Web 结果跨 rerun 保留未做；依赖未锁版本。保留这些限制，不擅自重构。

本轮已获准原样归档 9/28 日志、新建本日志、最小更新 README 并创建一次文档提交。main 快进合并、联网核实及推送仍待另行批准。9/28 记录是当时 V5 验收和 V6 计划，不覆盖或倒填成 V6 已完成。

下一版本范围未授权。真实 API／浏览器、检索评估或环境基线可按需求另行讨论，不自动开发 V7、Agent、LangChain 或 FastAPI。
