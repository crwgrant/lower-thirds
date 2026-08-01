from __future__ import annotations

import json
from pathlib import Path

from lower_thirds.models import Participant


class DataStore:
    DEFAULT_PREVIEW_BACKGROUND = "#00ff00"
    DEFAULT_DISPLAY_DURATION_SECONDS = 5

    def __init__(self) -> None:
        self.participants: list[Participant] = []
        self.file_path: Path | None = None
        self.preview_background = self.DEFAULT_PREVIEW_BACKGROUND
        self.display_duration_seconds = self.DEFAULT_DISPLAY_DURATION_SECONDS

    def load(self, path: Path) -> None:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)

        settings = payload.get("settings", {})
        self.preview_background = settings.get(
            "preview_background",
            self.DEFAULT_PREVIEW_BACKGROUND,
        )
        self.display_duration_seconds = int(
            settings.get(
                "display_duration_seconds",
                self.DEFAULT_DISPLAY_DURATION_SECONDS,
            )
        )
        self.participants = [
            Participant.from_dict(item) for item in payload.get("participants", [])
        ]
        self.file_path = path

    def save(self, path: Path | None = None) -> Path:
        target = path or self.file_path
        if target is None:
            raise ValueError("No file path set")

        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "settings": {
                "preview_background": self.preview_background,
                "display_duration_seconds": self.display_duration_seconds,
            },
            "participants": [p.to_dict() for p in self.participants],
        }
        with target.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

        self.file_path = target
        return target

    def add_participant(self, participant: Participant) -> None:
        self.participants.append(participant)

    def remove_participant(self, participant_id: str) -> None:
        self.participants = [p for p in self.participants if p.id != participant_id]

    def update_participant(self, participant: Participant) -> None:
        for index, existing in enumerate(self.participants):
            if existing.id == participant.id:
                self.participants[index] = participant
                return

    def get_participant(self, participant_id: str) -> Participant | None:
        for participant in self.participants:
            if participant.id == participant_id:
                return participant
        return None

    def reorder_participants(self, participant_ids: list[str]) -> bool:
        by_id = {participant.id: participant for participant in self.participants}
        reordered: list[Participant] = []
        seen: set[str] = set()

        for participant_id in participant_ids:
            if participant_id in by_id and participant_id not in seen:
                reordered.append(by_id[participant_id])
                seen.add(participant_id)

        for participant in self.participants:
            if participant.id not in seen:
                reordered.append(participant)

        if len(reordered) != len(self.participants):
            return False

        self.participants = reordered
        return True

    def move_participant(self, from_index: int, to_index: int) -> bool:
        if from_index == to_index:
            return True
        if not 0 <= from_index < len(self.participants):
            return False
        if not 0 <= to_index <= len(self.participants) - 1:
            return False

        participant = self.participants.pop(from_index)
        self.participants.insert(to_index, participant)
        return True
