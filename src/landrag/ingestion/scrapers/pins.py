import csv
import io
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from landrag.ingestion.classifier import extract_pins_reference

logger = logging.getLogger(__name__)

PINS_BASE_URL = "https://national-infrastructure-consenting.planninginspectorate.gov.uk"
PINS_DOCS_CDN = "https://nsip-documents.planninginspectorate.gov.uk"
REQUEST_DELAY = 2  # seconds between requests


@dataclass
class NsipProject:
    reference: str
    name: str
    project_type: str
    local_authority: str
    decision: str
    url_path: str
    region: str = ""
    date_of_decision: str = ""


@dataclass
class DocumentLink:
    title: str
    url: str
    category: str
    date_str: str
    project_reference: str
    file_format: str = "pdf"


def fetch_project_list() -> list[NsipProject]:
    """Fetch all NSIP projects from the PINS CSV API."""
    url = f"{PINS_BASE_URL}/api/applications-download"
    logger.info("Fetching project list from %s", url)

    response = httpx.get(url, timeout=60, follow_redirects=True)
    response.raise_for_status()

    reader = csv.DictReader(io.StringIO(response.text))
    projects: list[NsipProject] = []

    for row in reader:
        ref = row.get("Project reference", "").strip()
        if not ref:
            continue

        stage = row.get("Stage", "").strip().lower()
        decision = "pending"
        if "decided" in stage or "post-decision" in stage:
            decision = "granted"  # simplified; real logic would check decision letter

        projects.append(
            NsipProject(
                reference=ref,
                name=row.get("Project name", "").strip(),
                project_type=row.get("Application type", "").strip(),
                local_authority=row.get("Location", "").strip(),
                region=row.get("Region", "").strip(),
                decision=decision,
                date_of_decision=row.get("Date of decision", "").strip(),
                url_path=f"/projects/{ref}",
            )
        )

    logger.info("Found %d projects", len(projects))
    return projects


def fetch_document_library_page(
    project_reference: str, page: int = 1, items_per_page: int = 100
) -> tuple[list[DocumentLink], int]:
    """Fetch one page of documents from a project's document library.

    Returns (documents, total_count).
    """
    url = (
        f"{PINS_BASE_URL}/projects/{project_reference}/documents"
        f"?page={page}&itemsPerPage={items_per_page}"
    )
    logger.info("Fetching documents page %d for %s", page, project_reference)

    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    docs: list[DocumentLink] = []

    # Parse document entries from the page
    # Each document is typically in a list item or article with a link to the PDF
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Document links point to the CDN or contain the project reference
        if not (href.endswith(".pdf") or f"{project_reference}" in href and "document" in href.lower()):
            continue
        if href.endswith(".pdf"):
            title = link.get_text(strip=True)
            if not title:
                continue

            # Build full URL
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = f"{PINS_BASE_URL}{href}"
            else:
                full_url = f"{PINS_DOCS_CDN}/{href}"

            docs.append(
                DocumentLink(
                    title=title,
                    url=full_url,
                    category="",
                    date_str="",
                    project_reference=project_reference,
                    file_format="pdf",
                )
            )

    # Try to extract total count from the page
    total_count = 0
    count_text = soup.find(string=lambda t: t and "document" in t.lower() and any(c.isdigit() for c in t))
    if count_text:
        import re
        match = re.search(r"(\d+)\s*document", count_text.lower())
        if match:
            total_count = int(match.group(1))

    return docs, total_count


def fetch_all_documents(project_reference: str) -> list[DocumentLink]:
    """Fetch all documents for a project, handling pagination."""
    all_docs: list[DocumentLink] = []
    page = 1

    first_page_docs, total_count = fetch_document_library_page(project_reference, page=1)
    all_docs.extend(first_page_docs)
    logger.info(
        "Project %s: found %d docs on page 1 (total: %d)",
        project_reference,
        len(first_page_docs),
        total_count,
    )

    if total_count > 100:
        total_pages = (total_count + 99) // 100
        for page in range(2, total_pages + 1):
            time.sleep(REQUEST_DELAY)
            page_docs, _ = fetch_document_library_page(project_reference, page=page)
            all_docs.extend(page_docs)
            logger.info(
                "Project %s: fetched %d docs from page %d",
                project_reference,
                len(page_docs),
                page,
            )

    # Deduplicate by URL
    seen: set[str] = set()
    unique_docs: list[DocumentLink] = []
    for doc in all_docs:
        if doc.url not in seen:
            seen.add(doc.url)
            unique_docs.append(doc)

    return unique_docs


def download_document(url: str, save_path: Path) -> bool:
    """Download a document to local storage. Returns True on success."""
    save_path.parent.mkdir(parents=True, exist_ok=True)

    if save_path.exists():
        logger.debug("Already downloaded: %s", save_path)
        return True

    try:
        with httpx.stream("GET", url, timeout=120, follow_redirects=True) as response:
            response.raise_for_status()
            with open(save_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
        logger.info("Downloaded: %s", save_path.name)
        return True
    except httpx.HTTPError as e:
        logger.error("Failed to download %s: %s", url, e)
        return False


# Keep the HTML parsing functions for testing
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
                url=link.get("href", ""),
                category=cells[1].get_text(strip=True),
                date_str=cells[2].get_text(strip=True),
                project_reference=project_reference,
            )
        )

    return docs
