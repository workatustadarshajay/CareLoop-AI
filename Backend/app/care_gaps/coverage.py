from collections.abc import Sequence
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import Settings

SYSTEM_PROMPT = (
    "You check whether a patient's care plan already covers one expected care item. "
    "Answer yes only if at least one card describes the same action, even if worded differently. "
    "Otherwise answer no."
)


class CoverageAnswer(BaseModel):
    answer: Literal["yes", "no"]


def build_coverage_model(settings: Settings) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.api_key,
        temperature=0,
        max_retries=2,
    )


async def is_item_covered(item_label: str, card_descriptions: Sequence[str], model: BaseChatModel) -> bool:
    if not card_descriptions:
        return False
    cards = "\n".join(f"- {description}" for description in card_descriptions)
    result = await model.with_structured_output(CoverageAnswer).ainvoke(
        [
            ("system", SYSTEM_PROMPT),
            ("human", f"Expected item: {item_label}\n\nCards:\n{cards}"),
        ]
    )
    return result.answer == "yes"
