# V7.2：离线 Function Calling 与 Python 学习

本轮新增 `agent_tools.py`、`function_calling.py`、`function_calling_demo.py`、`tests/test_function_calling.py` 和本文档。V7.1 的 `rag.py`、`rag_tools.py` 以及现有 Web/CLI 流程保持原样。

这是离线开发版本：没有真实模型适配器，不读取 `.env`，不创建 OpenAI/DeepSeek 客户端。示例和验收均使用 Mock；真实 API 与真实数据库的组合尚未验证。

## 1. 一次调用怎样完成

```text
用户输入
  → 模型替身返回 assistant 消息
  → Python 检查工具名称、JSON 和字段
  → V7.1 工具验证参数并返回结构化结果（测试时替换底层检索）
  → 将结果放进 role=tool 消息，并保留 tool_call_id
  → 模型替身生成回答
```

模型提供调用建议，Python 决定是否执行。Schema 是工具说明，不能代替运行时检查。这个分工及工具结果消息格式参考 [DeepSeek Tool Calls](https://api-docs.deepseek.com/guides/tool_calls/) 和 [Chat Completions API](https://api-docs.deepseek.com/api/create-chat-completion/)。参数 JSON 可能无效或包含模型虚构字段，因此应用仍须校验。

本轮使用非思考模式的字典消息契约。没有接入 SDK response 对象、流式输出、Beta strict、思考模式或 reasoning_content 的往返处理。未来接真实服务前，需要单独实现并验证适配器，明确关闭思考模式或实现其完整消息协议。

## 2. 三个入口

```python
get_tool_definitions()
dispatch_tool_call(name, arguments_json)
run_single_tool_turn(user_message, request_completion)
```

`get_tool_definitions()` 返回 Chat Completions 风格的工具描述列表。唯一允许的工具名是 `search_recruitment_knowledge`，字段只有 query、top_k、max_distance。

`dispatch_tool_call()` 只接受 JSON 字符串参数。它先验证名称，再解析 JSON；拒绝重复字段、非标准数字、浮点溢出、超过 16000 字符的参数和额外字段。之后才延迟导入 V7.1 工具。query、top_k、max_distance 的类型及范围继续由 `rag_tools.search_recruitment_knowledge()` 校验。

`run_single_tool_turn()` 接收用户输入和一个可信的响应函数。响应函数的调用形式是：

```python
request_completion(messages=[...], tools=[...], tool_choice="auto")
```

返回值必须是 assistant 消息字典，而非完整 API response：

```python
{
    "role": "assistant",
    "content": None,
    "tool_calls": [{
        "id": "call_001",
        "type": "function",
        "function": {
            "name": "search_recruitment_knowledge",
            "arguments": '{"query":"Python","top_k":1}'
        }
    }]
}
```

回调函数属于应用侧可信代码。依赖注入便于测试，但不能阻止任意回调自行联网；本轮通过传入 Mock 和测试启动器的隔离措施保证离线执行。

## 3. 用实际代码学习 Python

### def、参数、默认参数和 return

`function_calling.py` 的定义：

```python
def run_single_tool_turn(user_message, request_completion):
```

`def` 定义函数；括号中的两个名字是参数。调用函数时，把用户文本和响应函数交给它。

V7.1 的入口仍然是：

```python
def search_recruitment_knowledge(query, top_k=4, max_distance=None):
```

`top_k=4` 表示省略时使用默认值 4，`None` 表示没有设置阈值。分发器不会为省略参数硬填另一套默认值。

`return` 将结果交还调用者，并结束当前函数。例如未知工具会立即返回错误，不再执行后面的检索代码：

```python
if not isinstance(name, str) or name != TOOL_NAME:
    return _error("UNKNOWN_TOOL", "请求的工具不在允许列表中。")
```

### if 条件和提前返回

`if` 表示“满足条件时执行”。`isinstance(name, str)` 检查是不是字符串；`!=` 表示不等于。

这类提前返回把无效请求挡在执行入口之前。两个工具调用会直接得到 TOOL_CALL_LIMIT，而不是执行第一个后才发现超限。

### dict、list 和 JSON 字符串

`dict` 是按名字查找值的容器，例如 `{"role": "tool", "tool_call_id": "call_001"}`。

`list` 是按顺序放置多个元素的容器，例如 `messages = [系统消息, 用户消息, 工具调用消息, 工具结果消息]`。

工具调用中的 `arguments` 是字符串，不是 Python 字典：

```python
arguments = json.loads(arguments_json)
```

本项目实际调用还提供了拒绝非标准数字和重复字段的解析选项。`json.loads()` 将字符串转换成 Python 对象；`json.dumps()` 反向转换，并通过 `allow_nan=False` 拒绝 NaN/Infinity。

### import 与跨文件调用

`function_calling.py` 使用：

```python
from agent_tools import dispatch_tool_call, get_tool_definitions
```

这让流程文件可以使用工具文件中的函数。`agent_tools.py` 只有真正执行白名单工具时才导入 `rag_tools`，因此只导入 Schema 或运行纯 Mock 演示不会加载 Chroma。

### try/except

```python
try:
    result = _execute_search(arguments)
    # 检查返回结构和 JSON
except Exception:
    return _error("TOOL_EXECUTION_ERROR", "工具执行失败，请联系维护者。")
```

`try` 运行可能失败的代码，`except` 在失败时返回固定错误，避免把内部路径或凭据拼进响应。模型响应失败和工具执行失败分别报告，不会静默生成假结果。

### 函数作为参数与 ** 字典展开

`request_completion` 是函数参数，它自己也可以被调用。测试传入 `Mock`，未来经过授权和验收后才传入真实适配器。

```python
return search_recruitment_knowledge(**arguments)
```

如果 arguments 是 `{"query": "Python", "top_k": 1}`，`**arguments` 相当于传入 `query="Python", top_k=1`。因此必须先拒绝额外字段，不能直接展开模型提供的任意字典。

## 4. Tool、Function Calling 与 Agent Loop

V7.1 Tool 负责“验证参数并检索”。V7.2 在外面加上模型请求、名称分发和结果消息，形成一次 Function Calling 闭环。模型没有数据库路径、建库函数或执行任意 Python 的入口。

Agent Loop 会持续决定下一步并重复执行工具。本轮只允许一次工具执行，最多两次模型响应，没有 `while` 循环、自动重试、记忆、多 Agent 或框架。

第二次请求设置 `tool_choice="none"`，而且本地代码再次检查返回消息。即使模型替身仍然返回工具调用，也不会执行第二次。

工具返回成功不代表自然语言回答已通过事实核查。系统提示要求不编造来源、将工具文本视为数据，但这不是防提示注入或真实性的完整保证。`distance` 始终只是检索距离。

## 5. 返回与停止行为

流程成功统一返回：

```python
{"ok": True, "answer": "回答文本", "tool_result": {...}, "error": None}
```

不调用工具直接回答时，tool_result 为 None。工具成功但没有结果时，保留真实的空列表，允许模型说明未找到相关标准。

流程失败统一返回 ok=False、answer=None 和固定错误；已有工具结果保留在 tool_result 中。模型异常、响应格式无效、工具超限或工具失败不会自动重试。

工具分发错误包括 UNKNOWN_TOOL、INVALID_ARGUMENTS、TOOL_EXECUTION_ERROR；V7.1 的 INVALID_QUERY、INVALID_TOP_K、INVALID_DISTANCE、KNOWLEDGE_BASE_NOT_READY、RETRIEVAL_ERROR 保持原样。

## 6. 安全运行离线演示

在项目根目录、使用已有虚拟环境运行：

```powershell
.\.venv\Scripts\python.exe -B function_calling_demo.py
```

该演示明确使用 Mock 替换模型响应和工具执行，输入输出均为虚构数据。它不会把虚构结果标成真实知识库证据，也不读取真实数据库。不要把测试中的临时替换或虚构内容接入现有产品流程。

正式验收使用项目外固定启动器，记录源码哈希、固定测试类和独立运行日志。不要直接运行 unittest discover，因为目录中还有真实 Chroma 集成测试，本轮未授权执行。

## 7. 三个 5～10 分钟练习

1. **找出两个响应。** 阅读 `function_calling_demo.py` 中 Mock 的 side_effect 列表，指出哪个元素提出工具调用、哪个元素给出回答；解释为什么它们都属于 assistant。随后运行演示，核对 tool_result 中的 source。
2. **观察未知工具。** 在交互式 Python 中导入 `dispatch_tool_call`，运行 `dispatch_tool_call("unknown", '{"query":"Python"}')`。预期 UNKNOWN_TOOL，results 为空。该路径在导入 RAG 前就停止，不会查询数据库。解释是哪条 if 和 return 做了拦截。
3. **观察多余字段。** 运行 `dispatch_tool_call("search_recruitment_knowledge", '{"query":"Python","database_path":"fictional"}')`。预期 INVALID_ARGUMENTS。删除 database_path 后不要直接查询原始数据库；先用离线演示中的 patch 替换执行边界，再尝试不同 top_k，并比较字典参数。

练习只改演示副本或使用交互环境，不改历史工作日志、V7.1 工具和知识库。运行后仍不得提交、推送或进入下一阶段，等待代码审查。
