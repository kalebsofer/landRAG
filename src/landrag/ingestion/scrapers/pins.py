from dataclasses import dataclass

from bs4 import BeautifulSoup

from landrag.ingestion.classifier import extract_pins_reference


@dataclass
class NsipProject:
    reference: str
    name: str
    project_type: str
    local_authority: str
    decision: str
    url_path: str


@dataclass
class DocumentLink:
    title: str
    url_path: str
    category: str
    date_str: str
    project_reference: str


def parse_nsip_project_list_page(html: str) -> list[NsipProject]:
    soup = BeautifulSoup(html, "html.parser")
    projects: list[NsipProject] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        url_path = link.get("href", "")
        name = link.get_text(strip=True)
        reference = extract_pins_reference(url_path) or extract_pins_reference(name) or ""

        projects.append(
            NsipProject(
                reference=reference,
                name=name,
                project_type=cells[1].get_text(strip=True),
                local_authority=cells[2].get_text(strip=True),
                decision=cells[3].get_text(strip=True),
                url_path=url_path,
            )
        )

    return projects


def parse_document_library_page(html: str, project_reference: str) -> list[DocumentLink]:
    soup = BeautifulSoup(html, "html.parser")
    docs: list[DocumentLink] = []

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        link = cells[0].find("a")
        if not link:
            continue

        docs.append(
            DocumentLink(
                title=link.get_text(strip=True),
                url_path=link.get("href", ""),
                category=cells[1].get_text(strip=True),
                date_str=cells[2].get_text(strip=True),
                project_reference=project_reference,
            )
        )

    return docs
