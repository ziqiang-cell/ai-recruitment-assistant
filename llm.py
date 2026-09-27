import os

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError


def get_ai_response(final_prompt):
    load_dotenv()
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()

    if not api_key:
        raise ValueError("未配置 DEEPSEEK_API_KEY。请在项目目录的 .env 文件中填写，或设置同名环境变量。")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    try:
        response = client.chat.completions.create(
            model="deepseek-flash",
            messages=[{"role": "user", "content": final_prompt}],
            response_format={"type": "json_object"},
            max_tokens=4096,
            stream=False,
        )
    except OpenAIError as error:
        raise RuntimeError("DeepSeek API 调用失败，请检查 API Key、网络连接和账户状态。") from error

    return response.choices[0].message.content
