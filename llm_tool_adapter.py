"""SDK 对象到 V7.2 字典回调的薄适配层；不构造客户端或读取凭据。"""

from copy import deepcopy
import inspect
import json
import math


def _check_client(client):
    """客户端归调用者所有；不修改配置，不复制或关闭它。"""
    try:
        retries = client.max_retries
        create = client.chat.completions.create
    except AttributeError:
        raise ValueError("必须显式传入兼容的客户端。") from None
    if type(retries) is not int or retries != 0:
        raise ValueError("客户端必须预先设置 max_retries=0。")
    if not callable(create) or inspect.iscoroutinefunction(create):
        raise ValueError("客户端必须提供同步的 chat.completions.create。")
    return create


def _normalise_completion(response):
    """只接受一项完整、非思考、非流式的 SDK 形状响应。"""
    choices = getattr(response, "choices", None)
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("响应必须恰好包含一个 choice。")
    choice = choices[0]
    reason = getattr(choice, "finish_reason", None)
    if reason not in ("stop", "tool_calls"):
        raise ValueError("响应未正常完成。")
    message = getattr(choice, "message", None)
    if getattr(message, "role", None) != "assistant":
        raise ValueError("消息角色无效。")
    for field in ("refusal", "reasoning_content"):
        if getattr(message, field, None) not in (None, ""):
            raise ValueError("不支持拒绝或思考模式消息。")
    if getattr(message, "function_call", None) is not None:
        raise ValueError("不支持旧 function_call 格式。")
    content = getattr(message, "content", None)
    if content is not None and not isinstance(content, str):
        raise ValueError("消息正文类型无效。")
    calls = getattr(message, "tool_calls", None)
    if calls is None:
        calls = []
    if not isinstance(calls, list):
        raise ValueError("工具调用列表类型无效。")
    if reason == "stop":
        if calls or not isinstance(content, str) or not content.strip():
            raise ValueError("回答未完整结束。")
        return {"role": "assistant", "content": content}
    if not calls:
        raise ValueError("工具调用消息缺少调用。")

    converted = []
    for call in calls:
        call_id = getattr(call, "id", None)
        function = getattr(call, "function", None)
        name = getattr(function, "name", None)
        arguments = getattr(function, "arguments", None)
        if (getattr(call, "type", None) != "function"
                or not isinstance(call_id, str) or not call_id.strip() or len(call_id) > 200
                or not isinstance(name, str) or not isinstance(arguments, str)):
            raise ValueError("工具调用字段无效。")
        converted.append({"id": call_id, "type": "function",
                          "function": {"name": name, "arguments": arguments}})
    # 保留全部建议，由原 V7.2 流程拒绝多工具；不能静默只取第一个。
    return {"role": "assistant", "content": content, "tool_calls": converted}


def make_request_completion(client, *, model="deepseek-flash", timeout=30.0, max_tokens=1024):
    """返回兼容 run_single_tool_turn 的回调；本轮只传入 Mock 客户端验收。"""
    _check_client(client)
    if not isinstance(model, str) or not 1 <= len(model.strip()) <= 128:
        raise ValueError("model 必须是长度为 1～128 的非空字符串。")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not 0 < timeout <= 120):
        raise ValueError("timeout 必须是 0～120 秒内的有限正数，不能是布尔值。")
    if not math.isfinite(timeout):
        raise ValueError("timeout 必须是有限正数。")
    if type(max_tokens) is not int or not 1 <= max_tokens <= 4096:
        raise ValueError("max_tokens 必须是 1～4096 的整数，不能是布尔值。")
    model = model.strip()

    def request_completion(*, messages, tools, tool_choice):
        try:
            # 每次都复查，拒绝工厂返回后又被调用者启用的 SDK 重试。
            create = _check_client(client)
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages 必须是非空列表。")
            if not isinstance(tools, list) or not tools:
                raise ValueError("tools 必须是非空列表。")
            if tool_choice not in ("auto", "none"):
                raise ValueError("本轮只支持 auto 或 none。")
            request_messages = deepcopy(messages)
            request_tools = deepcopy(tools)
            json.dumps([request_messages, request_tools], allow_nan=False)
            response = create(
                model=model,
                messages=request_messages,
                tools=request_tools,
                tool_choice=tool_choice,
                stream=False,
                n=1,
                timeout=float(timeout),
                max_tokens=max_tokens,
                extra_body={"thinking": {"type": "disabled"}},
            )
            return _normalise_completion(response)
        except Exception:
            # 上层沿用 MODEL_REQUEST_ERROR；不输出 SDK 异常正文或 HTTP 请求体。
            raise RuntimeError("模型 SDK 请求或响应无效。") from None

    return request_completion
