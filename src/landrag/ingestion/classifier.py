import re

from anthropic import Anthropic

from landrag.core.config import get_settings
from landrag.models.enums import ProjectType, Topic

_PINS_REF_PATTERN = re.compile(r"EN\d{6}")

_PROJECT_TYPE_KEYWORDS: dict[str, ProjectType] = {
    "wind": ProjectType.ONSHORE_WIND,
    "offshore-wind": ProjectType.OFFSHORE_WIND,
    "solar": ProjectType.SOLAR,
    "battery": ProjectType.BATTERY_STORAGE,
    "gas-peaker": ProjectType.GAS_PEAKER,
    "gas peaker": ProjectType.GAS_PEAKER,
    "transmission": ProjectType.TRANSMISSION,
    "hydrogen": ProjectType.HYDROGEN,
    "ccus": ProjectType.CCUS,
    "carbon capture": ProjectType.CCUS,
}


def extract_pins_reference(text: str) -> str | None:
    match = _PINS_REF_PATTERN.search(text)
    return match.group(0) if match else None


def classify_project_type_from_path(path: str) -> ProjectType | None:
    path_lower = path.lower()
    for keyword, project_type in _PROJECT_TYPE_KEYWORDS.items():
        if keyword in path_lower:
            return project_type
    return None


def classify_topic_llm(text: str) -> Topic | None:
    """Use Claude Haiku to classify the topic of a text chunk."""
    settings = get_settings()
    client = Anthropic(api_key=settings.anthropic_api_key)

    topics_list = ", ".join(t.value for t in Topic)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=50,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Classify the following planning document text into exactly one topic. "
                    f"Valid topics: {topics_list}. "
                    f"Respond with ONLY the topic value, nothing else. "
                    f"If none fit, respond with 'none'.\n\n"
                    f"Text: {text[:1000]}"
                ),
            }
        ],
    )

    result = response.content[0].text.strip().lower()
    try:
        return Topic(result)
    except ValueError:
        return None
