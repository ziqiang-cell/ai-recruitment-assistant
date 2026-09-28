import json

from analysis_parser import parse_analysis_response
from llm import get_ai_response
from pdf_parser import extract_text_from_pdf
from prompt import build_prompt
from rag import build_or_update_knowledge_base, retrieve_context


def read_text(title):
    print(f"请输入{title}，输入空行后结束：")
    lines = []

    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    return "\n".join(lines)


def main():
    jd = read_text("岗位 JD")
    pdf_path = input("请输入 PDF 简历文件路径：").strip().strip('"') #.strip() 去掉前后的空格  .steip('"'")去掉路径前后的双引号

    if not jd.strip():
        print("错误：岗位 JD 不能为空。")
        return
    if not pdf_path:
        print("错误：PDF 简历路径不能为空。")
        return

    try:
        resume_text = extract_text_from_pdf(pdf_path)
    except (FileNotFoundError, ValueError) as error:
        print(f"错误：{error}")
        return

    try:
        build_or_update_knowledge_base()
        retrieved_chunks = retrieve_context(jd, top_k=4)
    except Exception as error:
        print(f"错误：知识库构建或检索失败：{error}")
        return

    final_prompt = build_prompt(jd, resume_text, retrieved_chunks)
    try:
        answer = get_ai_response(final_prompt)
    except (ValueError, RuntimeError) as error:
        print(f"错误：{error}")
        return

    try:
        allowed_sources = {chunk["source"] for chunk in retrieved_chunks}
        analysis = parse_analysis_response(answer, allowed_sources)
    except ValueError as error:
        print(f"错误：{error}")
        return

    print("\n===== 招聘分析结果 =====\n")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    print("\n【知识库参考依据】")
    for reference in analysis["knowledge_references"]:
        print(f"source：{reference['source']}")
        print(f"evidence：{reference['evidence']}")
    if not analysis["knowledge_references"]:
        print("暂无。")


if __name__ == "__main__":
    main()
