from pathlib import Path  #Python 自带的路径处理工具

from pypdf import PdfReader #创建一个 PDF 阅读器


def extract_text_from_pdf(pdf_path):
    path = Path(pdf_path)

    if not path.is_file():
        raise FileNotFoundError("找不到 PDF 文件，请检查文件路径。")
    if path.suffix.lower() != ".pdf":
        raise ValueError("所选文件不是 PDF，请提供 .pdf 文件。")

    try:
        reader = PdfReader(path)
        page_texts = []
        for page in reader.pages:
            page_texts.append(page.extract_text() or "")
    except Exception as error:
        raise ValueError("PDF 无法读取，请确认文件有效且未加密。") from error

    resume_text = "\n".join(page_texts).strip()
    if not resume_text:
        raise ValueError("PDF 中未提取到文字；目前只支持包含可复制文字的 PDF，不支持扫描件。")

    return resume_text
