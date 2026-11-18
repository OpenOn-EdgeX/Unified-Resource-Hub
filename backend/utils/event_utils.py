from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

from utils.time_utils import format_relative_time

NONE_DISPLAY = "-"

def build_event_summary(
    events: Optional[Iterable],
    *,
    predicate: Optional[Callable] = None,
    include_namespace: bool = False,
    namespace_fallback: Optional[str] = None,
):
    warning = 0
    normal = 0
    event_list = []

    for ev in events or []:
        if predicate and not predicate(ev):
            continue

        raw_type = getattr(ev, "type", None)
        ev_type = "Normal" if raw_type == "Normal" else "Warning"

        normal += ev_type == "Normal"
        warning += ev_type == "Warning"

        last_time = getattr(ev, "last_timestamp", None) or getattr(
            ev, "event_time", None
        )
        involved = getattr(ev, "involved_object", None)
        meta = getattr(ev, "metadata", None)

        ev_name = (getattr(meta, "name", None) or "") if meta else ""

        kind = (getattr(involved, "kind", None) or "unknown") if involved else "unknown"
        name = (getattr(involved, "name", None) or "unknown") if involved else "unknown"

        item = {
            "object": (
                f"{str(kind).lower()}/{name}"
                if name != "unknown"
                else str(kind).lower()
            ),
            "message": getattr(ev, "message", None) or NONE_DISPLAY,
            "reason": getattr(ev, "reason", None) or NONE_DISPLAY,
            "type": ev_type,
            "last_seen": format_relative_time(last_time) if last_time else NONE_DISPLAY,
            "_sort_time": last_time,
            "_sort_name": ev_name,
        }

        if include_namespace:
            namespace = (
                getattr(meta, "namespace", None) or namespace_fallback or NONE_DISPLAY
            )
            item["namespace"] = namespace

        event_list.append(item)

    event_list.sort(
        key=lambda e: (
            e["_sort_time"] or datetime.min.replace(tzinfo=timezone.utc),
            e["_sort_name"],
        ),
        reverse=True,
    )

    for e in event_list:
        e.pop("_sort_time", None)
        e.pop("_sort_name", None)

    return {
        "warning_events": warning,
        "normal_events": normal,
        "events": event_list,
    }
