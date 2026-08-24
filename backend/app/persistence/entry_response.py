"""Map ORM entries to API responses including tags."""

from __future__ import annotations

from app.persistence.models import Entry
from app.persistence.schemas import EntryResponse, TagResponse


def entry_to_response(entry: Entry) -> EntryResponse:
    base = EntryResponse.model_validate(entry)
    tags = [
        TagResponse.model_validate(et.tag)
        for et in entry.entry_tags
        if et.tag is not None
    ]
    return base.model_copy(update={"tags": tags})
