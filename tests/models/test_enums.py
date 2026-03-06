from landrag.models.enums import (
    DecisionOutcome,
    DocumentType,
    JobStatus,
    ProjectType,
    SourcePortal,
    Topic,
)


def test_project_type_values():
    assert ProjectType.ONSHORE_WIND.value == "onshore_wind"
    assert ProjectType.SOLAR.value == "solar"
    assert ProjectType.BATTERY_STORAGE.value == "battery_storage"


def test_topic_values():
    assert Topic.NOISE.value == "noise"
    assert Topic.ECOLOGY.value == "ecology"
    assert Topic.LANDSCAPE.value == "landscape"


def test_document_type_values():
    assert DocumentType.DECISION_LETTER.value == "decision_letter"
    assert DocumentType.EIA_CHAPTER.value == "eia_chapter"


def test_source_portal_values():
    assert SourcePortal.PINS.value == "pins"
    assert SourcePortal.LPA.value == "lpa"


def test_decision_outcome_values():
    assert DecisionOutcome.GRANTED.value == "granted"
    assert DecisionOutcome.REFUSED.value == "refused"


def test_job_status_values():
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.COMPLETED.value == "completed"
    assert JobStatus.FAILED.value == "failed"
