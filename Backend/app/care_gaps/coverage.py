from collections.abc import Sequence

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.prompts import load_prompt


class CoverageAnswer(BaseModel):
    covered_labels: list[str] = Field(
        default_factory=list,
        description="Exact labels of the expected items that at least one card already covers.",
    )


def build_coverage_model(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.api_key,
        temperature=0,
        max_retries=2,
    )


async def covered_items(
    item_labels: Sequence[str],
    card_descriptions: Sequence[str],
    model: BaseChatModel,
) -> set[str]:
    """One model call per diagnosis: which expected items do the note's cards already cover?"""
    if not card_descriptions or not item_labels:
        return set()
    items = "\n".join(f"- {label}" for label in item_labels)
    cards = "\n".join(f"- {description}" for description in card_descriptions)
    result = await model.with_structured_output(CoverageAnswer).ainvoke(
        [
            ("system", load_prompt("coverage")),
            ("human", f"Expected items:\n{items}\n\nCards:\n{cards}"),
        ]
    )
    wanted = {label.lower(): label for label in item_labels}
    return {wanted[label.lower()] for label in result.covered_labels if label.lower() in wanted}
