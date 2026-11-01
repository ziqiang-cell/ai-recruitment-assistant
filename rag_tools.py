"""为将来的 Function Calling 提供 Python 检索入口；本模块不运行 Agent。"""

import json
import math

from rag import KnowledgeBaseNotReadyError, retrieve_existing_context


def _error(code, message):
    return {
        "ok": False,
        "results": [],
        "count": 0,
        "error": {"code": code, "message": message},
    }


def search_recruitment_knowledge(query, top_k=4, max_distance=None):
    """验证参数并查询已有招聘集合，不建库、重建或写入知识片段。"""
    if not isinstance(query, str):
        return _error("INVALID_QUERY", "query 必须是长度为 1～2000 的非空字符串。")
    query = query.strip()
    if not 1 <= len(query) <= 2000:
        return _error("INVALID_QUERY", "query 必须是长度为 1～2000 的非空字符串。")

    # bool 是 int 的子类，所以必须额外拒绝 True/False。
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= 8:
        return _error("INVALID_TOP_K", "top_k 必须是 1～8 的整数，不能是布尔值。")

    if max_distance is not None:
        if (
            isinstance(max_distance, bool)
            or not isinstance(max_distance, (int, float))
            or max_distance < 0
            or (isinstance(max_distance, float) and not math.isfinite(max_distance))
        ):
            return _error("INVALID_DISTANCE", "max_distance 必须为 None 或有限的非负数字。")

    #异常判断
    try:
        results = retrieve_existing_context(query, top_k, max_distance)
        # 不把 NaN、Infinity 或其他不能用于标准 JSON 的值交给未来的模型。
        json.dumps(results, allow_nan=False)
    except KnowledgeBaseNotReadyError:
        return _error("KNOWLEDGE_BASE_NOT_READY", "招聘知识库尚未准备好，请联系维护者。")
    except Exception:
        # 不转发内部异常，避免泄露路径、凭证、隐私数据或堆栈。
        return _error("RETRIEVAL_ERROR", "知识库检索失败，请稍后重试或联系维护者。")

    return {"ok": True, "results": results, "count": len(results), "error": None}
