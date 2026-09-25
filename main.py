from llm import get_ai_response
from prompt import build_prompt


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
    resume = read_text("候选人简历")

    if not jd.strip() or not resume.strip():
        print("岗位 JD 和候选人简历都不能为空。")
        return

    final_prompt = build_prompt(jd, resume)
    try:
        answer = get_ai_response(final_prompt)
    except (ValueError, RuntimeError) as error:
        print(f"错误：{error}")
        return

    print("\n===== 招聘分析结果 =====\n")
    print(answer)


if __name__ == "__main__":
    main()
