from landrag.ingestion.classifier import classify_project_type_from_path, extract_pins_reference
from landrag.models.enums import ProjectType


def test_extract_pins_reference():
    assert extract_pins_reference("EN010012 - Hornsea Project") == "EN010012"
    assert extract_pins_reference("Application EN020024 details") == "EN020024"
    assert extract_pins_reference("No reference here") is None


def test_classify_project_type_from_path():
    assert classify_project_type_from_path("wind-farm-decision.pdf") == ProjectType.ONSHORE_WIND
    assert classify_project_type_from_path("solar-park-eia.pdf") == ProjectType.SOLAR
    assert (
        classify_project_type_from_path("battery-storage-report.pdf") == ProjectType.BATTERY_STORAGE
    )
    assert classify_project_type_from_path("random-document.pdf") is None
