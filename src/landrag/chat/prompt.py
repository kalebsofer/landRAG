from landrag.models.schemas import ChatMessage, ChunkResult

SYSTEM_PROMPT_TEMPLATE = """You are landRAG, a research assistant for UK planning \
and environmental permitting documents. You answer questions using ONLY the \
source documents provided below.

Rules:
- Cite every factual claim using [n] references matching the source numbers
- If the sources don't contain enough information to answer, say so explicitly
- Never fabricate planning conditions, decisions, or document references
- When sources conflict, present both positions with their citations
- Use precise planning terminology (DCO, NSIP, NPS, EIA, etc.)
- For direct questions: be concise and specific
- For exploratory questions: synthesise across sources and highlight patterns

{sources_block}"""

NO_SOURCES_BLOCK = """Sources:
No source documents were found for this query. Inform the user that you \
couldn't find relevant documents and suggest they try different search \
terms or adjust their filters."""


def build_system_prompt(chunks: list[ChunkResult]) -> str:
    if not chunks:
        return SYSTEM_PROMPT_TEMPLATE.format(sources_block=NO_SOURCES_BLOCK)

    source_lines = ["Sources:"]
    for i, chunk in enumerate(chunks, 1):
        page_range = ""
        if chunk.page_start is not None and chunk.page_end is not None:
            page_range = f", pp. {chunk.page_start}-{chunk.page_end}"
        elif chunk.page_start is not None:
            page_range = f", p. {chunk.page_start}"

        header = (
            f"[{i}] {chunk.document_title} "
            f"({chunk.project_reference}, {chunk.document_type}{page_range})"
        )
        source_lines.append(header)
        source_lines.append(chunk.content)
        source_lines.append("")

    return SYSTEM_PROMPT_TEMPLATE.format(sources_block="\n".join(source_lines))


def build_messages(history: list[ChatMessage], current_message: str) -> list[dict]:
    messages = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": current_message})
    return messages
