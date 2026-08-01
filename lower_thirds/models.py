from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class Participant:
    name: str
    title: str = ""
    subtitle: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "subtitle": self.subtitle,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Participant:
        return cls(
            id=data.get("id") or str(uuid4()),
            name=data.get("name", ""),
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
        )
