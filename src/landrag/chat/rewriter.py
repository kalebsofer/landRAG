import json
import logging

from anthropic import Anthropic

from landrag.core.config import get_settings
from landrag.models.schemas import ChatMessage

logger = logging.getLogger(__name__)

REWRITE_PROMPT = """Given this conversation context and new message, produce:
1. A standalone search query (resolving pronouns and references to previous messages)
2. Any filters implied by the query

Valid filter keys (all values are lists of strings):
- project_type: onshore_wind, offshore_wind, solar, battery_storage,
  gas_peaker, transmission, hydrogen, ccus, other
- topic: noise, ecology, landscape, traffic, cultural_heritage,
  flood_risk, air_quality, socioeconomic, grid,
  cumulative_impact, decommissioning, construction
- document_type: decision_letter, eia_chapter, inspector_report,
  consultation_response, policy_statement, guidance
- decision: granted, refused, withdrawn, pending

Conversation context:
{context}

New message: {message}

Respond with ONLY valid JSON: {{"query": "...", "filters": {{"key": ["value"]}}}}"""


def merge_filters(explicit: dict, suggested: dict) -> dict:
    """Merge explicit user filters with LLM-suggested filters. Explicit wins per-field."""
    merged = {}
    all_keys = set(list(explicit.keys()) + list(suggested.keys()))
    for key in all_keys:
        if key in explicit and explicit[key]:
            merged[key] = explicit[key]
        elif key in suggested and suggested[key]:
            merged[key] = suggested[key]
    return merged


def rewrite_query(message: str, history: list[ChatMessage]) -> dict:
    """Rewrite a user message into a standalone search query with filter suggestions."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    context_turns = history[-6:]
    context = (
        "\n".join(f"{m.role}: {m.content}" for m in context_turns)
        if context_turns
        else "(no prior context)"
    )

    prompt = REWRITE_PROMPT.format(context=context, message=message)

    response = client.messages.create(
        model=settings.rewriter_model,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    try:
        parsed = json.loads(raw)
        return {
            "query": parsed.get("query", message),
            "filters": parsed.get("filters", {}),
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Query rewriter returned malformed JSON: %s", raw)
        return {"query": message, "filters": {}}
