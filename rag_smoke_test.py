from rag import ensure_knowledge_base, retrieve_context


def main():
    """用三个不同岗位查询观察检索结果，不调用 DeepSeek。"""
    ensure_knowledge_base()
    queries = [
        "AI 应用开发实习生，要求 Python、LLM API、Prompt Engineering、RAG、Git 和 Web 开发能力。",
        "我们希望候选人具备良好的学习能力、Debug 能力、沟通能力和项目理解能力。",
        "招聘有机化学实验研发实习生，要求有机合成、核磁共振、液相色谱和实验安全经验。",
    ]

    for query in queries:
        print("\n" + "-" * 50)
        print(f"Query：{query}")
        print("-" * 50)
        chunks = retrieve_context(query, top_k=4)
        for number, chunk in enumerate(chunks, start=1):
            preview = chunk["text"][:150].replace("\n", " ")
            print(f"检索结果 {number}：")
            print(f"source：{chunk['source']}")
            print(f"chunk_index：{chunk['chunk_index']}")
            print(f"向量检索距离：{chunk['distance']:.4f}")
            print(f"text 前 150 字：{preview}")
        if not chunks:
            print("没有检索到知识库片段。")


if __name__ == "__main__":
    main()
