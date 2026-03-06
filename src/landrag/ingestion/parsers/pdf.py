from dataclasses import dataclass
from enum import StrEnum

from pypdf import PdfReader

from landrag.ingestion.parsers.html import ParsedDocument


class PdfQualityResult(StrEnum):
    GOOD = "good"
    LOW = "low"


@dataclass
class PdfExtractResult(ParsedDocument):
    quality: PdfQualityResult = PdfQualityResult.GOOD


MIN_CHARS_PER_PAGE = 50


def extract_pdf(file_path: str) -> PdfExtractResult:
    reader = PdfReader(file_path)
    pages_text: list[str] = []

    for page in reader.pages:
        text = page.extract_text() or ""
        pages_text.append(text)

    full_text = "\n".join(pages_text)
    page_count = len(reader.pages)

    non_empty_pages = sum(1 for t in pages_text if len(t.strip()) >= MIN_CHARS_PER_PAGE)
    quality = (
        PdfQualityResult.GOOD
        if page_count == 0 or non_empty_pages / page_count > 0.5
        else PdfQualityResult.LOW
    )

    return PdfExtractResult(text=full_text, page_count=page_count, quality=quality)
