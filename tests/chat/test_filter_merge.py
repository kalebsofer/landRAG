from landrag.chat.rewriter import merge_filters


def test_explicit_wins_over_suggested():
    explicit = {"project_type": ["onshore_wind"]}
    suggested = {"project_type": ["offshore_wind"], "topic": ["noise"]}
    result = merge_filters(explicit, suggested)
    assert result["project_type"] == ["onshore_wind"]
    assert result["topic"] == ["noise"]


def test_suggested_fills_empty_fields():
    explicit = {}
    suggested = {"topic": ["ecology"]}
    result = merge_filters(explicit, suggested)
    assert result["topic"] == ["ecology"]


def test_empty_explicit_list_not_treated_as_set():
    explicit = {"project_type": []}
    suggested = {"project_type": ["solar"]}
    result = merge_filters(explicit, suggested)
    assert result["project_type"] == ["solar"]


def test_both_empty_returns_empty():
    result = merge_filters({}, {})
    assert result == {}


def test_none_values_ignored():
    explicit = {"project_type": None}
    suggested = {"topic": None}
    result = merge_filters(explicit, suggested)
    assert result == {}
