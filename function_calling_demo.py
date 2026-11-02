"""直接运行的离线演示：两个模型响应和检索结果全部使用虚构数据。"""

import json
from unittest.mock import Mock, patch

from agent_tools import TOOL_NAME
from function_calling import run_single_tool_turn


def run_demo():
    requester = Mock(side_effect=[
        {"role": "assistant", "content": None, "tool_calls": [{
            "id": "demo_call_001", "type": "function", "function": {
                "name": TOOL_NAME, "arguments": '{"query":"Python 基础","top_k":1}',
            },
        }]},
        {"role": "assistant", "content": "【Mock 演示】虚构标准要求掌握 Python 基础，来源 fictional_standard.md。"},
    ])
    fictional_result = {"ok": True, "results": [{
        "text": "虚构标准：掌握 Python 函数、字典和异常处理。",
        "source": "fictional_standard.md", "chunk_index": 0, "distance": 0.25,
    }], "count": 1, "error": None}
    # 演示始终替换执行边界，不会导入 rag_tools 或打开数据库。
    with patch("agent_tools._execute_search", return_value=fictional_result):
        return run_single_tool_turn("Python 岗位需要什么基础？", requester)


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=True, indent=2, allow_nan=False))
