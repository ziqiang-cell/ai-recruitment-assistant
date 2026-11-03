# V7.2 SDK 适配器：离线实现与 Python/Agent 学习

本轮只新增 `llm_tool_adapter.py`、`tests/test_llm_tool_adapter.py` 和本文档。main、已发布 RAG/工具闭环、llm.py、Web/CLI、依赖配置及历史记录均未修改。本轮适配器尚未提交或发布。

## 1. 适配器解决什么问题

`function_calling.run_single_tool_turn()` 的回调需要返回 Python 字典；模型 SDK 返回的却是包含 choices、message 等属性的完整对象。新增模块把两种接口连接起来：

```text
run_single_tool_turn
    → request_completion(messages=..., tools=..., tool_choice=...)
    → client.chat.completions.create(...)（本轮是 Mock）
    → _normalise_completion(response)
    → assistant 字典
    → 原有白名单和工具次数检查
```

适配器负责请求与转换；`agent_tools.py` 决定可执行哪个工具；`rag_tools.py` 验证检索参数。模型提供名称和 JSON 参数，Python 才决定是否执行。适配器不会导入 RAG、指定数据库路径或增加工具。

## 2. 实际函数签名

```python
make_request_completion(
    client, *, model="deepseek-flash", timeout=30.0, max_tokens=1024
)
```

它返回另一个函数：

```python
request_completion(*, messages, tools, tool_choice)
```

client 必须显式传入，本轮测试只传 Mock。模块没有 SDK import、密钥读取、dotenv 或默认客户端构造，也不复制、关闭或更改调用者客户端。真实客户端接入层仍未实现。

## 3. Python：函数、默认值与关键字参数

`def` 定义函数，`return` 返回结果。例如工厂最后的代码：

```python
return request_completion
```

这里返回的是函数本身，没有加括号，因此没有立刻发出请求。之后调用返回的函数，才会进入它的函数体。

model、timeout、max_tokens 带默认值。`*` 后的参数只能写成 `timeout=5.0` 这样的关键字形式，减少初学者把参数顺序放错的机会。

工厂采用以下应用侧约束：

- model：去空白后长度 1～128，默认沿用既有项目模型名，不代表本轮验证了服务可用性。
- timeout：有限正数，`0 < timeout <= 120` 秒；拒绝布尔值、NaN、Infinity 及极大整数。
- max_tokens：1～4096 的整数，拒绝布尔值。
- client.max_retries：必须为整数 0，False 虽然等于 0，也会被拒绝。

配置错误在创建回调时抛出固定 ValueError，不会回退创建真实客户端。

## 4. Python：闭包和依赖注入

真实代码在工厂内部定义函数：

```python
def request_completion(*, messages, tools, tool_choice):
    create = _check_client(client)
    # 随后调用 create(...)
```

这个内部函数记住外部的 client、model、timeout 和 max_tokens，称为闭包。`client` 指向调用者提供的对象，而不是一个自动创建的新连接。

把对象从参数传入称为依赖注入。测试提供 Mock，就能验证请求参数和次数；未来真实接入必须另行确认授权与隔离边界。依赖注入本身不是沙箱：如果调用者主动传入真实客户端并调用回调，就可能联网。本轮没有这样做。

`_check_client()` 在工厂和每次请求前都检查重试设置。如果调用者在两轮响应之间把 max_retries 改为 2，第二次 create 不会发生。它同时拒绝异步 create，避免在同步流程里制造未等待的协程。

## 5. Python：对象属性、dict 与 list

SDK 形状对象通过点号访问属性：

```python
choice = response.choices[0]
message = choice.message
```

本模块实际使用带默认值的 `getattr()` 检查这些属性，缺失或类型不正确就拒绝响应。

转换后的 dict 按名字访问值：

```python
{"role": "assistant", "content": "虚构回答"}
```

工具调用集合是 list，按顺序包含多个 dict。适配器保留全部工具建议，由原流程拒绝超过一个的请求，不能静默只拿第一项。

`arguments` 仍是 JSON 字符串；本模块不 eval、不执行它，原有分发器才会 json.loads、验证白名单与字段。

## 6. 请求与响应边界

本模块显式发送：

```python
stream=False,
n=1,
timeout=float(timeout),
max_tokens=max_tokens,
extra_body={"thinking": {"type": "disabled"}},
```

不设置原 llm.py 的 JSON 输出模式，因为此处需要模型返回工具调用消息。messages 和 tools 先复制并检查标准 JSON，避免模拟 SDK 改动调用者保存的消息或 Schema。

SDK 自动重试关闭与 timeout 的通用行为参考 [OpenAI Python SDK 官方文档](https://developers.openai.com/api/reference/python)；DeepSeek 的非思考参数参考 [DeepSeek Tool Calls 官方示例](https://api-docs.deepseek.com/guides/tool_calls/)。本地 SDK 3.19.2 的默认重试数为 2，默认超时配置为 600 秒，已通过静态源码核对。Mock 只验证应用发出了所需参数，不证明真实服务接受参数。

超时是请求超时配置，不是整个流程的绝对墙钟截止时间；客户端 transport 可能还有自己的行为。本模块只检查 SDK 层 max_retries=0，不承诺约束任意自定义传输。

响应必须有且只有一个 choice，finish_reason 为 stop 或 tool_calls，字段一致。length、content_filter、未知原因、旧 function_call、拒绝内容、非空 reasoning_content、畸形调用均拒绝。

stop 必须有非空回答且没有工具调用；tool_calls 必须有非空调用列表。工具 id/name/arguments 按类型检查后完整保留，其他无关 SDK 字段不进入消息。

## 7. Python：try/except 与错误如何传回

```python
try:
    # 检查客户端、发送请求、转换响应
except Exception:
    raise RuntimeError("模型 SDK 请求或响应无效。") from None
```

try 中的失败交给 except。对外异常文本固定，不拼接 SDK 异常里的路径、认证信息或请求正文；`from None` 抑制向外展示原异常链。

原 `run_single_tool_turn()` 会把回调异常转为 MODEL_REQUEST_ERROR，保持已有错误体系。如果第二次模型响应失败，结果仍保留第一次成功检索的 tool_result，answer 为 None，不会包装成成功。

工厂配置错误与运行期错误分开：前者为 ValueError；后者为固定 RuntimeError。原始异常可能仍被 Python 保存在内部上下文中，不能把整个 traceback 或异常对象原样写入用户日志。本轮对外只使用固定消息，未输出原 SDK 错误内容。

## 8. Agent：本轮仍是单次闭环

适配器不是 Agent Loop。最多两次模型响应、一次工具执行仍由原 V7.2 代码控制；没有 while、自动重试、多 Agent、记忆或新框架。

第二次请求使用 tool_choice="none"。即使 Mock 仍给出工具调用，原流程也会返回 TOOL_CALL_LIMIT，不执行第二个工具。

来源与 tool_call_id 原样传递。工具为空结果时保留空列表；失败立即停止。distance 仍是距离，不是概率或置信度。系统提示和 tool 角色不构成回答真实性或抗提示注入保证。

## 9. 本轮实际验收

| 组 | 实际运行 PASS | FAIL / ERROR / SKIP |
|---|---:|---|
| 新适配器测试 | 41 | 0 / 0 / 0 |
| 既有 V7.2 Mock 回归 | 35 | 0 / 0 / 0 |
| 既有 V7.1/V6 Mock 回归 | 47 | 0 / 0 / 0 |
| 合计 | 123 | 0 / 0 / 0 |

每组独立进程、固定测试类和源码哈希启动；不是把历史 82 PASS 直接累加。本轮确实重跑了 35+47。安全事件为空，未替换的 Chroma 客户端工厂调用为 0。

新测试的 SDK 响应为 SimpleNamespace，客户端是 Mock；超时/认证/限流等错误为模拟异常，不是服务商真实错误。Chroma 依赖由模块替身隔离，未加载真实 SDK 或 Chroma。因此 **真实 SDK 类型、真实 API、真实数据库组合及产品流程均未验收**。123 PASS 只覆盖上述离线 Mock 范围。

`return_value` 设置固定响应，`side_effect` 设置两轮不同响应或抛出异常；`assert_called_once_with()` 校验请求参数，`assert_not_called()` 验证失败后没有继续执行，`call_count` 检查两次响应/一次工具上限。

不要直接 unittest discover：目录里还有真实 Chroma 集成测试。本轮使用项目外新建的固定类启动器，先静态审查，再隔离运行；没有修改或使用旧验收启动器覆盖历史日志。

## 10. 三个 5～10 分钟练习

以下示例只使用 Mock 和虚构数据，导入适配器和 Schema 不会构造真实客户端：

```python
from types import SimpleNamespace as NS
from unittest.mock import Mock
from agent_tools import get_tool_definitions
from llm_tool_adapter import make_request_completion

client = Mock()
client.max_retries = 0
client.chat.completions.create.return_value = NS(choices=[NS(
    finish_reason="stop",
    message=NS(role="assistant", content="【Mock】本次未检索。", tool_calls=None),
)])
request = make_request_completion(client)
result = request(
    messages=[{"role": "user", "content": "虚构问题"}],
    tools=get_tool_definitions(),
    tool_choice="auto",
)
print(result)
```

1. **改变请求超时。** 把工厂调用改为 `make_request_completion(client, timeout=5.0)`，再查看 `client.chat.completions.create.call_args.kwargs["timeout"]`。预期为 5.0；改为 True 或 0，预期工厂 ValueError，create 不应因配置错误新增调用。解释为什么 True 不能当作 1 秒。
2. **观察对象到字典的转换。** 把返回的 message.content 改为另一句虚构文本，再重新请求，比较 SDK 形状对象属性和 result["content"]。增加一个无关属性 annotations，确认它没有被放入 result。解释这里 list、dict 和对象属性的区别。
3. **拒绝截断回答。** 把 finish_reason 改成 length，再调用 request，预期固定 RuntimeError。捕获异常并只打印 str(error)，解释为什么不能把看似完整的 content 当作成功。使用新的 Mock 或 reset_mock 后检查 create 仅调用一次，没有自动重试。

练习不使用真实客户端、不运行产品入口、不改原始数据库、历史工作日志或已发布源码；建议使用交互式环境或项目外练习副本。

## 11. 当前停止点

本轮适配器仅在 `codex/v7.2-sdk-adapter` 分支以未跟踪新增文件形式存在，main 仍为已发布提交。等待代码审查，不暂存、提交、合并或推送，不进入真实 API 测试或 FastAPI/MySQL/React 开发。
