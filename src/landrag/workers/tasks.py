from landrag.ingestion.parsers.docx import extract_docx
from landrag.ingestion.parsers.html import ParsedDocument, extract_html
from landrag.ingestion.parsers.pdf import extract_pdf
from landrag.workers.celery_app import celery_app


@celery_app.task(name="landrag.workers.tasks.parse_document")
def parse_document(file_path: str, file_format: str) -> dict:
    if file_format == "pdf":
        result = extract_pdf(file_path)
    elif file_format == "html":
        with open(file_path) as f:
            result = extract_html(f.read())
    elif file_format == "docx":
        result = extract_docx(file_path)
    else:
        raise ValueError(f"Unsupported format: {file_format}")

    return {
        "text": result.text,
        "sections": [{"heading": s.heading, "content": s.content} for s in result.sections],
        "page_count": result.page_count,
    }


@celery_app.task(name="landrag.workers.tasks.chunk_and_embed")
def chunk_and_embed(parsed_data: dict, document_id: str) -> dict:
    from landrag.ingestion.chunker import chunk_document
    from landrag.ingestion.embedder import embed_texts
    from landrag.ingestion.parsers.html import ParsedSection

    doc = ParsedDocument(
        text=parsed_data["text"],
        sections=[
            ParsedSection(heading=s["heading"], content=s["content"])
            for s in parsed_data.get("sections", [])
        ],
        page_count=parsed_data.get("page_count"),
    )

    chunks = chunk_document(doc)
    texts = [c.text for c in chunks]
    embeddings = embed_texts(texts)

    return {
        "document_id": document_id,
        "chunk_count": len(chunks),
        "chunks": [
            {
                "text": c.text,
                "chunk_index": c.chunk_index,
                "section_heading": c.section_heading,
                "embedding": emb,
            }
            for c, emb in zip(chunks, embeddings)
        ],
    }
