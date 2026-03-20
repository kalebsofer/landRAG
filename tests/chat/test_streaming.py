from landrag.chat.streaming import format_sse_event


def test_format_sources_event():
    sources = [{"ref": 1, "document_title": "Doc A"}]
    event = format_sse_event("sources", sources)
    assert event.startswith("event: sources\n")
    assert "data: " in event
    assert '"ref": 1' in event
    assert event.endswith("\n\n")


def test_format_token_event():
    event = format_sse_event("token", {"text": "Hello"})
    assert event == 'event: token\ndata: {"text": "Hello"}\n\n'


def test_format_done_event():
    event = format_sse_event("done", {"suggested_filters": {}})
    assert event.startswith("event: done\n")
    assert event.endswith("\n\n")


def test_format_error_event():
    event = format_sse_event("error", {"message": "Something went wrong"})
    assert event.startswith("event: error\n")
    assert "Something went wrong" in event
