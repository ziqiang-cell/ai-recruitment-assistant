import json   #全称：JavaScript Object Notation（JavaScript 对象表示法）
                #现在可以理解为：一种用固定格式表示数据的文本格式

def parse_analysis_response(response_text, allowed_sources=None):
    """把模型返回的 JSON 字符串解析并检查为招聘分析字典。"""
    try:
        analysis = json.loads(response_text)   #json.loads():从 JSON 字符串加载成 Python 对象。
                                                #  json.loads()JSON字符串 → Python
                                                #json.dumps()Python → JSON字符串
    except (json.JSONDecodeError, TypeError):
        # 兼容模型偶尔返回的完整 ```json ... ``` 代码块。
        lines = response_text.strip().splitlines() if isinstance(response_text, str) else []
        has_code_block = (
            len(lines) >= 3
            and lines[0].strip().lower() in ("```json", "```")
            and lines[-1].strip() == "```"
        )
        if not has_code_block:
            raise ValueError("模型返回的内容不是有效 JSON，请重试。") from None
        try:
            analysis = json.loads("\n".join(lines[1:-1]))
        except json.JSONDecodeError:
            raise ValueError("模型返回的内容不是有效 JSON，请重试。") from None

    required_fields = {
        "match_score", "matched_requirements", "missing_requirements",
        "strengths", "risks", "interview_questions", "knowledge_references", "summary",
    }
    if not isinstance(analysis, dict):
        raise ValueError("模型返回的分析必须是 JSON 对象，请重试。")
    missing_fields = required_fields - analysis.keys()
    if missing_fields:
        raise ValueError(f"模型返回的分析缺少字段：{', '.join(sorted(missing_fields))}。请重试。")

    try:
        score = int(analysis["match_score"])
    except (TypeError, ValueError, OverflowError):
        raise ValueError("模型返回的匹配度无法转换为整数，请重试。") from None
    analysis["match_score"] = max(0, min(100, score))

    for field, item_fields in (
        ("matched_requirements", {"requirement", "evidence"}),
        ("missing_requirements", {"requirement", "reason"}),
        ("knowledge_references", {"source", "evidence"}),
    ):
        items = analysis[field]
        if not isinstance(items, list):
            raise ValueError(f"模型返回的 {field} 格式不正确，请重试。")
        for item in items:
            if not isinstance(item, dict) or set(item) != item_fields:
                raise ValueError(f"模型返回的 {field} 格式不正确，请重试。")
            for value in item.values():
                if not isinstance(value, str) or not value.strip():
                    raise ValueError(f"模型返回的 {field} 格式不正确，请重试。")

    if allowed_sources is not None:
        for item in analysis["knowledge_references"]:
            if item["source"] not in allowed_sources:
                raise ValueError("模型引用了未检索到的知识库来源，请重试。")

    for field in ("strengths", "risks", "interview_questions"):
        items = analysis[field]
        if not isinstance(items, list):
            raise ValueError(f"模型返回的 {field} 格式不正确，请重试。")
        for item in items:
            if not isinstance(item, str) or not item.strip():
                raise ValueError(f"模型返回的 {field} 格式不正确，请重试。")

    if not 3 <= len(analysis["interview_questions"]) <= 5:
        raise ValueError("模型返回的面试问题应为 3 到 5 个，请重试。")
    if not isinstance(analysis["summary"], str) or not analysis["summary"].strip():
        raise ValueError("模型返回的 summary 格式不正确，请重试。")

    return analysis
