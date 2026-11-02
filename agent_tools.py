"""V7.2 工具描述和固定白名单；导入本模块不会导入 Chroma 或创建客户端。"""

from copy import deepcopy
import json


TOOL_NAME = "search_recruitment_knowledge"
_TOOL_DEFINITIONS = [{
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "查询已有的招聘标准知识库。返回文本、来源、片段序号和距离；"
            "距离不是概率或置信度。无结果或失败时不得编造证据。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 2000},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 8, "default": 4},
                "max_distance": {
                    "anyOf": [{"type": "number", "minimum": 0}, {"type": "null"}],
                    "description": "可省略；仅接受有限非负数或 null。",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}]


def get_tool_definitions():
    """每次返回独立副本，避免调用者改坏下一次请求的 Schema。"""
    return deepcopy(_TOOL_DEFINITIONS)


def _error(code, message):
    return {"ok": False, "results": [], "count": 0,
            "error": {"code": code, "message": message}}


def _reject_constant(value):
    raise ValueError("Non-standard JSON number")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _execute_search(arguments):
    # 延迟导入：只有白名单、JSON 和字段检查通过才进入 V7.1。
    # 参数的类型、范围、strip 和数据库未就绪错误仍由 V7.1 入口处理。
    from rag_tools import search_recruitment_knowledge

    return search_recruitment_knowledge(**arguments)


def _valid_result(result):
    if not isinstance(result, dict) or set(result) != {"ok", "results", "count", "error"}:
        return False
    if type(result["ok"]) is not bool or not isinstance(result["results"], list):
        return False
    if type(result["count"]) is not int or result["count"] != len(result["results"]):
        return False
    if result["ok"]:
        return result["error"] is None
    error = result["error"]
    return (not result["results"] and isinstance(error, dict)
            and set(error) == {"code", "message"}
            and isinstance(error["code"], str) and isinstance(error["message"], str))


def dispatch_tool_call(name, arguments_json):
    """解析模型提供的 JSON 字符串；只允许一个固定的招聘检索工具。"""
    if not isinstance(name, str) or name != TOOL_NAME:
        return _error("UNKNOWN_TOOL", "请求的工具不在允许列表中。")
    if not isinstance(arguments_json, str) or not 1 <= len(arguments_json) <= 16000:
        return _error("INVALID_ARGUMENTS", "工具参数必须是有效的 JSON 对象字符串。")

    try:
        arguments = json.loads(arguments_json, parse_constant=_reject_constant,
                               object_pairs_hook=_unique_object)
        # 同时拒绝 1e400 这类解析后溢出为 Infinity 的数字。
        json.dumps(arguments, allow_nan=False)
    except (ValueError, TypeError, RecursionError):
        return _error("INVALID_ARGUMENTS", "工具参数必须是有效的标准 JSON 对象。")

    if (not isinstance(arguments, dict) or "query" not in arguments
            or set(arguments) - {"query", "top_k", "max_distance"}):
        return _error("INVALID_ARGUMENTS", "工具参数只能包含 query、top_k、max_distance，且必须提供 query。")

    try:
        result = _execute_search(arguments)
        if not _valid_result(result):
            return _error("TOOL_EXECUTION_ERROR", "工具未能返回有效结果。")
        json.dumps(result, allow_nan=False)
        return result
    except Exception:
        return _error("TOOL_EXECUTION_ERROR", "工具执行失败，请联系维护者。")
