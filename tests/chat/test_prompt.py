from landrag.chat.prompt import build_messages, build_system_prompt
from landrag.models.enums import DocumentType, ProjectType, Topic
from landrag.models.schemas import ChatMessage, ChunkResult


def _make_chunk(ref: int) -> ChunkResult:
    return ChunkResult(
        chunk_id=f"chunk-{ref}",
        content=f"Content for source {ref}. Important planning details here.",
        score=0.9,
        highlight=f"Content for source {ref}",
        document_title=f"Document {ref}",
        document_type=DocumentType.DECISION_LETTER,
        project_name="Test Project",
        project_reference="EN010099",
        project_type=ProjectType.ONSHORE_WIND,
        topic=Topic.NOISE,
        source_url="https://example.com/doc.pdf",
        page_start=ref * 10,
        page_end=ref * 10 + 5,
    )


def test_build_system_prompt_includes_sources():
    chunks = [_make_chunk(1), _make_chunk(2)]
    prompt = build_system_prompt(chunks)
    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "Document 1" in prompt
    assert "Document 2" in prompt
    assert "EN010099" in prompt
    assert "Content for source 1" in prompt


def test_build_system_prompt_includes_rules():
    chunks = [_make_chunk(1)]
    prompt = build_system_prompt(chunks)
    assert "ONLY the source documents" in prompt
    assert "Cite every factual claim" in prompt


def test_build_system_prompt_empty_sources():
    prompt = build_system_prompt([])
    assert "No source documents" in prompt


def test_build_messages_structures_conversation():
    history = [
        ChatMessage(role="user", content="Hi"),
        ChatMessage(role="assistant", content="Hello"),
    ]
    messages = build_messages(history, "What about noise?")
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hi"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "What about noise?"


def test_build_messages_empty_history():
    messages = build_messages([], "First question")
    assert len(messages) == 1
    assert messages[0]["content"] == "First question"
