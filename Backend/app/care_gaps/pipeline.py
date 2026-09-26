import asyncio
import logging
from collections.abc import Sequence

from app.care_gaps.checklist import Diagnosis, ExpectedItem, load_checklist
from app.care_gaps.coverage import build_coverage_model, is_item_covered
from app.care_gaps.diagnosis import detect_diagnoses
from app.core.config import get_settings
from app.db.session import async_session_factory
from app.models.card import Card
from app.models.review_flag import ReviewFlag, ReviewFlagKind
from app.repositories.review_flags import ReviewFlagRepository

logger = logging.getLogger(__name__)


def missing_item_reason(diagnosis: Diagnosis, item: ExpectedItem) -> str:
    name = diagnosis.name[0].upper() + diagnosis.name[1:]
    return f"{name} care plans usually include {item.label}, but no card from this note covers it."


async def run_care_gap_check(note_id: int, note_text: str, cards: Sequence[Card]) -> list[ReviewFlag]:
    """Runs after a note's cards are saved. Never raises, so note submission is unaffected."""
    try:
        matched = detect_diagnoses(note_text, load_checklist().diagnoses)
        if not matched:
            return []

        descriptions = [card.description for card in cards]
        model = build_coverage_model(get_settings())
        expected = [(diagnosis, item) for diagnosis in matched for item in diagnosis.expected_items]
        covered = await asyncio.gather(
            *(is_item_covered(item.label, descriptions, model) for _, item in expected)
        )

        flags = [
            ReviewFlag(
                note_id=note_id,
                kind=ReviewFlagKind.MISSING_ITEM,
                reason=missing_item_reason(diagnosis, item),
                diagnosis=diagnosis.name,
                item_label=item.label,
                card_type=item.card_type,
                card_description=item.card_description,
            )
            for (diagnosis, item), is_covered in zip(expected, covered)
            if not is_covered
        ]
        if flags:
            async with async_session_factory() as session, session.begin():
                await ReviewFlagRepository(session).add_all(flags)

        logger.info(
            "Note %s matched %s; %d missing item(s) flagged",
            note_id,
            ", ".join(diagnosis.name for diagnosis in matched),
            len(flags),
        )
        return flags
    except Exception:
        logger.exception("Care-gap check failed for note %s", note_id)
        return []
