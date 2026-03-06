from landrag.core.pinecone import build_metadata_filter
from landrag.models.enums import ProjectType, Topic, DecisionOutcome
from landrag.models.schemas import SearchFilters, DateRange


def test_build_metadata_filter_empty():
    result = build_metadata_filter(None)
    assert result == {}


def test_build_metadata_filter_project_type():
    filters = SearchFilters(project_type=[ProjectType.ONSHORE_WIND, ProjectType.SOLAR])
    result = build_metadata_filter(filters)
    assert result["project_type"] == {"$in": ["onshore_wind", "solar"]}


def test_build_metadata_filter_topic():
    filters = SearchFilters(topic=[Topic.NOISE])
    result = build_metadata_filter(filters)
    assert result["topic"] == {"$in": ["noise"]}


def test_build_metadata_filter_decision():
    filters = SearchFilters(decision=[DecisionOutcome.GRANTED])
    result = build_metadata_filter(filters)
    assert result["decision"] == {"$in": ["granted"]}


def test_build_metadata_filter_date_range():
    filters = SearchFilters(date_range=DateRange(from_date="2022-01-01", to_date="2024-12-31"))
    result = build_metadata_filter(filters)
    assert result["date_published"]["$gte"] == "2022-01-01"
    assert result["date_published"]["$lte"] == "2024-12-31"


def test_build_metadata_filter_combined():
    filters = SearchFilters(
        project_type=[ProjectType.SOLAR],
        topic=[Topic.NOISE, Topic.ECOLOGY],
        decision=[DecisionOutcome.GRANTED],
    )
    result = build_metadata_filter(filters)
    assert "project_type" in result
    assert "topic" in result
    assert "decision" in result
