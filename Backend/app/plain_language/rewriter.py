"""Rewrite a card's clinical description in plain language.

Step 3 guarantee: this is a REWORDING, not a reinterpretation. The prompt
and the output validation below exist to make sure the plain version says
exactly what the original said — only simpler — plus one generic
"why it matters" sentence. Nothing more.
"""

import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import get_settings
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

MAX_PLAIN_LENGTH = 1000  # matches cards.description_plain column length


_WHITESPACE_RE = re.compile(r"\s+")
_WRAPPED_IN_QUOTES_RE = re.compile(r'^["“”\'\s]+|["“”\'\s]+$')


def _clean_output(text: str) -> str | None:
    """Normalize model output; return None if unusable."""
    cleaned = _WHITESPACE_RE.sub(" ", text).strip()
    cleaned = _WRAPPED_IN_QUOTES_RE.sub("", cleaned).strip()
    if not cleaned:
        return None
    if cleaned.lower().startswith(("plain language:", "rewrite:", "simplified:")):
        cleaned = cleaned.split(":", 1)[1].strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_PLAIN_LENGTH:
        cleaned = cleaned[: MAX_PLAIN_LENGTH - 3].rstrip() + "..."
    return cleaned


async def rewrite_card_description(description: str, card_type: str) -> str | None:
    """Return the plain-language version of a clinical description.

    Returns None (and logs) on any failure — callers must treat the plain
    text as optional and fall back to the clinical description.
    """
    settings = get_settings()
    if not settings.api_key:
        logger.info("plain-language rewrite skipped: no Gemini API key configured")
        return None

    model = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=settings.api_key,
        temperature=0,
        max_retries=2,
    )

    try:
        response = await model.ainvoke(
            [
                ("system", load_prompt("plain_language")),
                (
                    "human",
                    f"Card type: {card_type}\nOriginal instruction: {description}",
                ),
            ]
        )
    except Exception:
        logger.exception("plain-language rewrite failed for card type %s", card_type)
        return None

    return _clean_output(str(response.text or ""))
