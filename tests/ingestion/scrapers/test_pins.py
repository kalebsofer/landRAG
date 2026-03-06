from landrag.ingestion.scrapers.pins import (
    parse_nsip_project_list_page,
    parse_document_library_page,
    NsipProject,
    DocumentLink,
)


SAMPLE_PROJECT_HTML = """
<tr>
    <td><a href="/projects/EN010012">Hornsea Project One</a></td>
    <td>Offshore Wind</td>
    <td>East Riding of Yorkshire</td>
    <td>Granted</td>
</tr>
<tr>
    <td><a href="/projects/EN010077">Gate Burton Energy Park</a></td>
    <td>Solar</td>
    <td>West Lindsey</td>
    <td>Pending</td>
</tr>
"""


def test_parse_nsip_project_list():
    projects = parse_nsip_project_list_page(SAMPLE_PROJECT_HTML)
    assert len(projects) == 2
    assert projects[0].reference == "EN010012"
    assert projects[0].name == "Hornsea Project One"
    assert projects[1].reference == "EN010077"


SAMPLE_DOC_LIBRARY_HTML = """
<tr>
    <td><a href="/docs/EN010012-001234.pdf">Environmental Statement Chapter 7 - Noise</a></td>
    <td>Environmental Statement</td>
    <td>15/03/2019</td>
</tr>
<tr>
    <td><a href="/docs/EN010012-005678.pdf">Decision Letter</a></td>
    <td>Decision</td>
    <td>01/09/2020</td>
</tr>
"""


def test_parse_document_library_page():
    docs = parse_document_library_page(SAMPLE_DOC_LIBRARY_HTML, "EN010012")
    assert len(docs) == 2
    assert "Noise" in docs[0].title
    assert docs[1].title == "Decision Letter"
    assert docs[0].project_reference == "EN010012"
