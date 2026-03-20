import json


def format_sse_event(event_type: str, data: dict | list) -> str:
    """Format data as a Server-Sent Event string."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
