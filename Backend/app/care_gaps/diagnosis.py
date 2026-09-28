import re

from app.care_gaps.checklist import Diagnosis


def _alias_pattern(alias: str) -> re.Pattern[str]:
    words = r"\s+".join(re.escape(word) for word in alias.split())
    return re.compile(rf"(?<!\w){words}(?!\w)", re.IGNORECASE)


def detect_diagnoses(note_text: str, diagnoses: list[Diagnosis]) -> list[Diagnosis]:
    """Return every checklist diagnosis whose name or an alias appears in the note as a whole phrase."""
    return [
        diagnosis
        for diagnosis in diagnoses
        if any(_alias_pattern(alias).search(note_text) for alias in [diagnosis.name, *diagnosis.aliases])
    ]
