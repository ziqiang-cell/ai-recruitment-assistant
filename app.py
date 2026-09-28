import streamlit as st    #导入 streamlit 这个 Python 库，并且给它起一个简短的名字 st

from analysis_parser import parse_analysis_response
from llm import get_ai_response
from pdf_parser import extract_text_from_uploaded_pdf
from prompt import build_prompt
from rag import build_or_update_knowledge_base, retrieve_context


st.set_page_config(page_title="AI 招聘助手")
st.title("AI 招聘助手")
st.write("输入岗位要求并上传 PDF 简历，获取候选人与岗位的匹配分析。")
show_rag_debug = st.sidebar.checkbox("显示 RAG 检索结果")

jd = st.text_area("岗位 JD", height=200, placeholder="请粘贴岗位职责和任职要求") #CLI 的 input()，在 Web 里变成了 st.text_area()
uploaded_file = st.file_uploader(
    "上传 PDF 简历",
    type=["pdf"],
    help="仅支持包含可复制文字的 PDF；扫描件暂不支持。",
)

if st.button("开始分析", type="primary"):  #用户点击“开始分析”以后，才执行下面的代码
    if not jd.strip():                    #检查 JD 是否为空。
        st.error("请先输入岗位 JD。")      #st.error()→ 在网页显示错误
        st.stop()                         #st.stop() → 停止本次 Streamlit 执行
    if uploaded_file is None:
        st.error("请先上传 PDF 简历。")
        st.stop()

    try:
        with st.spinner("正在检索企业招聘标准，请稍候..."):
            build_or_update_knowledge_base()
            retrieved_chunks = retrieve_context(jd, top_k=4)
    except Exception as error:
        st.error(f"知识库构建或检索失败：{error}")
        st.stop()

    if show_rag_debug:
        st.sidebar.subheader("RAG 检索结果")
        for chunk in retrieved_chunks:
            st.sidebar.write(f"来源：{chunk['source']}，片段：{chunk['chunk_index']}")
            st.sidebar.write(chunk["text"])
        if not retrieved_chunks:
            st.sidebar.write("未检索到知识库内容。")

    try:
        resume_text = extract_text_from_uploaded_pdf(uploaded_file)
    except ValueError as error:          #还是捕获范围比较大
        st.error(str(error))
        st.stop()

    final_prompt = build_prompt(jd, resume_text, retrieved_chunks)
    with st.spinner("正在分析候选人简历，请稍候..."):  #作用就是模型调用期间，网页显示一个加载提示。
        try:
            answer = get_ai_response(final_prompt)
        except ValueError:
            st.error("尚未配置 DeepSeek API 密钥，请检查项目中的 .env 文件。")
            st.stop()
        except RuntimeError as error:
            st.error(str(error))
            st.stop()

    try:
        allowed_sources = {chunk["source"] for chunk in retrieved_chunks}
        analysis = parse_analysis_response(answer, allowed_sources)
    except ValueError as error:
        st.error(str(error))
        st.stop()

    st.subheader("招聘分析结果")
    st.write(f"模型估算岗位匹配度：{analysis['match_score']}/100（仅供招聘辅助参考）")

    st.subheader("已匹配的岗位要求")
    for item in analysis["matched_requirements"]:   #一个一个拿出已经匹配的岗位要求
        st.write(f"{item['requirement']}：{item['evidence']}")
    if not analysis["matched_requirements"]:
        st.write("暂无明确匹配证据。")

    st.subheader("未体现或不足的岗位要求")
    for item in analysis["missing_requirements"]:
        st.write(f"{item['requirement']}：{item['reason']}")
    if not analysis["missing_requirements"]:
        st.write("暂无。")

    for title, field in (
        ("候选人优势", "strengths"),
        ("风险与待确认事项", "risks"),
        ("建议面试问题", "interview_questions"),
    ):
        st.subheader(title)
        if analysis[field]:
            for number, text in enumerate(analysis[field], start=1):
                st.write(f"{number}. {text}")
        else:
            st.write("暂无。")

    st.subheader("总体总结")
    st.write(analysis["summary"])

    st.subheader("知识库参考依据")
    for reference in analysis["knowledge_references"]:
        st.write(f"{reference['source']}：{reference['evidence']}")
    if not analysis["knowledge_references"]:
        st.write("本次分析未引用知识库资料。")
