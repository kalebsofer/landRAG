from dataclasses import dataclass

import tiktoken

from landrag.ingestion.parsers.html import ParsedDocument


@dataclass
class ChunkConfig:
    max_tokens: int = 512
    overlap_tokens: int = 64


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    section_heading: str | None = None


_encoder = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_encoder.encode(text))


def _split_into_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    return paragraphs if paragraphs else [text]


def _split_large_paragraph(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split a single oversized paragraph into word-boundary pieces."""
    words = text.split()
    pieces: list[str] = []
    current_words: list[str] = []
    current_tokens = 0

    for word in words:
        word_tokens = _count_tokens(word)
        if current_tokens + word_tokens > max_tokens and current_words:
            pieces.append(" ".join(current_words))

            # Overlap: keep trailing words up to overlap_tokens
            overlap_words: list[str] = []
            ov_tokens = 0
            for w in reversed(current_words):
                wt = _count_tokens(w)
                if ov_tokens + wt > overlap_tokens:
                    break
                overlap_words.insert(0, w)
                ov_tokens += wt

            current_words = overlap_words
            current_tokens = ov_tokens

        current_words.append(word)
        current_tokens += word_tokens

    if current_words:
        pieces.append(" ".join(current_words))

    return pieces


def _chunk_text(text: str, config: ChunkConfig, start_index: int, heading: str | None = None) -> list[TextChunk]:
    if _count_tokens(text) <= config.max_tokens:
        return [TextChunk(text=text, chunk_index=start_index, section_heading=heading)]

    paragraphs = _split_into_paragraphs(text)

    # Expand any oversized paragraphs into smaller word-boundary pieces
    expanded: list[str] = []
    for para in paragraphs:
        if _count_tokens(para) > config.max_tokens:
            expanded.extend(_split_large_paragraph(para, config.max_tokens, config.overlap_tokens))
        else:
            expanded.append(para)
    paragraphs = expanded

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_tokens = 0
    idx = start_index

    for para in paragraphs:
        para_tokens = _count_tokens(para)

        if current_tokens + para_tokens > config.max_tokens and current_parts:
            chunks.append(TextChunk(
                text="\n\n".join(current_parts),
                chunk_index=idx,
                section_heading=heading,
            ))
            idx += 1

            # Overlap: keep last paragraph(s) up to overlap_tokens
            overlap_parts: list[str] = []
            overlap_tokens = 0
            for p in reversed(current_parts):
                p_tokens = _count_tokens(p)
                if overlap_tokens + p_tokens > config.overlap_tokens:
                    break
                overlap_parts.insert(0, p)
                overlap_tokens += p_tokens

            current_parts = overlap_parts
            current_tokens = overlap_tokens

        current_parts.append(para)
        current_tokens += para_tokens

    if current_parts:
        chunks.append(TextChunk(
            text="\n\n".join(current_parts),
            chunk_index=idx,
            section_heading=heading,
        ))

    return chunks


def chunk_document(doc: ParsedDocument, config: ChunkConfig | None = None) -> list[TextChunk]:
    if config is None:
        config = ChunkConfig()

    # If sections are available, chunk by section
    if doc.sections:
        chunks: list[TextChunk] = []
        idx = 0
        for section in doc.sections:
            section_text = f"{section.heading}\n\n{section.content}" if section.content else section.heading
            section_chunks = _chunk_text(section_text, config, idx, heading=section.heading)
            chunks.extend(section_chunks)
            idx += len(section_chunks)
        return chunks

    # Fallback: fixed-size chunking on full text
    return _chunk_text(doc.text, config, start_index=0)
