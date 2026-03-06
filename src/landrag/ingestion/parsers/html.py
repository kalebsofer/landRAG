from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ParsedSection:
    heading: str
    content: str


@dataclass
class ParsedDocument:
    text: str
    sections: list[ParsedSection] = field(default_factory=list)
    page_count: int | None = None


def extract_html(html_content: str) -> ParsedDocument:
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    sections: list[ParsedSection] = []
    headings = soup.find_all(["h1", "h2", "h3", "h4"])

    for heading in headings:
        heading_text = heading.get_text(strip=True)
        content_parts: list[str] = []
        for sibling in heading.find_next_siblings():
            if sibling.name in ["h1", "h2", "h3", "h4"]:
                break
            content_parts.append(sibling.get_text(strip=True))
        sections.append(ParsedSection(heading=heading_text, content="\n".join(content_parts)))

    full_text = soup.get_text(separator="\n", strip=True)

    return ParsedDocument(text=full_text, sections=sections)
