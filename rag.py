from pathlib import Path

import chromadb


PROJECT_DIR = Path(__file__).resolve().parent   #PROJECT_DIR就代表这个项目根目录
KNOWLEDGE_DIR = PROJECT_DIR / "knowledge_base"
DATABASE_DIR = PROJECT_DIR / "chroma_db"       #Chroma 建立向量数据库以后产生的本地数据  chroma_db/是机器为了检索而生成的数据
COLLECTION_NAME = "recruitment_standards"


def load_knowledge_documents():
    """读取知识库中的 Markdown 和文本文件。"""
    documents = []
    for path in sorted(KNOWLEDGE_DIR.iterdir()):     #把 knowledge_base/ 里的文件一个一个拿出来
        if path.is_file() and path.suffix.lower() in (".md", ".txt"):  #suffix后缀
            text = path.read_text(encoding="utf-8").strip()         #把文件内容读成 Python 字符串
            if text:
                documents.append({"text": text, "source": path.name})
    return documents


def chunk_text(text, chunk_size=400, chunk_overlap=80):
    """把长文档切开 按固定字符数切分文本，相邻片段保留少量重叠。"""
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_size 必须大于 0，chunk_overlap 必须小于 chunk_size。")

    chunks = []
    step = chunk_size - chunk_overlap
    for start in range(0, len(text), step):
        chunk = text[start:start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def _get_collection():         #连接 Chroma
    client = chromadb.PersistentClient(path=str(DATABASE_DIR))   #创建一个可以持久保存到硬盘的 Chroma 客户端
    return client.get_or_create_collection(name=COLLECTION_NAME)  #找一个叫 recruitment_standards 的集合；没有就创建


def build_or_update_knowledge_base():
    """切分文档，并用稳定 ID 写入本地 Chroma。"""
    documents = load_knowledge_documents()
    if not documents:
        raise ValueError("knowledge_base 中没有可用的 .md 或 .txt 文档。")

    collection = _get_collection()
    for document in documents:
        chunks = chunk_text(document["text"])
        ids = []
        metadatas = []
        for index in range(len(chunks)):
            ids.append(f"{document['source']}:{index}")
            metadatas.append({"source": document["source"], "chunk_index": index})

        # 未传 embeddings 时，Chroma 使用本地默认模型为文本生成向量。
        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
        '''collection.upsert(...) 可以拆成：update + insert 也就是：有这个 ID → 更新, 没这个 ID → 插入。'''
    return collection.count()


def retrieve_context(query, top_k=4):
    """ query按岗位 JD 查找最相关的知识库片段。   top_k=4 最多找 4 个最相关 Chunk"""
    collection = _get_collection()
    if not query.strip() or collection.count() == 0:
        return []

    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas"],
    )
    chunks = []
    for text, metadata in zip(result["documents"][0], result["metadatas"][0]):
        chunks.append({
            "text": text,
            "source": metadata["source"],
            "chunk_index": metadata["chunk_index"],
        })
    return chunks
