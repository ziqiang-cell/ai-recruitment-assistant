def build_prompt(jd, resume, retrieved_context):
    knowledge_text = "\n\n".join(
        f"来源：{chunk['source']}（片段 {chunk['chunk_index']}）\n{chunk['text']}"
        for chunk in retrieved_context
    )
    if not knowledge_text:
        knowledge_text = "没有检索到相关资料。"

    json_example = """{
  "match_score": 0,
  "matched_requirements": [
    {"requirement": "", "evidence": ""}
  ],
  "missing_requirements": [
    {"requirement": "", "reason": ""}
  ],
  "strengths": [""],
  "risks": [""],
  "interview_questions": ["", "", ""],
  "knowledge_references": [
    {"source": "", "evidence": ""}
  ],
  "summary": ""
}"""

    return f"""你是一名招聘助手。请根据岗位 JD、候选人简历和企业招聘知识库参考资料进行分析。
只依据下面提供的内容，不得编造候选人能力或经历。
候选人的能力和经历只能根据【候选人简历】判断；知识库不是候选人的个人经历。
知识库只用于提供招聘标准、评价标准和面试要求，不能据此虚构候选人事实。
即使知识库要求某项能力，简历未体现时也不能认为候选人具备；与当前岗位无关的检索资料可以忽略。
简历未提及的要求应写为“未体现”或“需要确认”，不要将未知直接判断为能力差。
match_score 是 0 到 100 的整数，仅表示基于 JD 和简历明确证据估算的岗位匹配度，不是录用结论。
matched_requirements 的 evidence 必须引用或概括简历中的实际证据。
missing_requirements 的 reason 应说明简历中未体现或明显不足的地方。
strengths 只能根据简历实际内容总结；risks 写需要进一步确认的风险或信息缺口。
interview_questions 请给出 3 到 5 个针对岗位要求和信息缺口的具体问题。
knowledge_references 只列出本次实际使用的知识库资料；source 必须与下方检索结果中的文件名完全一致，evidence 简述对应资料的依据。没有使用时返回 []。
summary 请用 2 到 4 句话总结，不要直接给出“录用”或“淘汰”的绝对决定。

只返回一个 JSON 对象，字段名和字段类型严格按下面的示例结构填写。
没有对应内容的数组可以是 []，不要为了填充字段而编造内容。
不要返回 Markdown、```json 代码块，也不要在 JSON 前后添加解释文字。

JSON 示例结构（空字符串只是占位符，请按实际证据填写）：
{json_example}

【岗位 JD】
{jd}

【候选人简历】
{resume}

【企业招聘知识库参考资料】
{knowledge_text}"""
