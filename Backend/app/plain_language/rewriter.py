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

logger = logging.getLogger(__name__)

MAX_PLAIN_LENGTH = 1000  # matches cards.description_plain column length

SYSTEM_PROMPT = """\
You rewrite ONE instruction from a doctor's note so a worried family member \
can understand it. This is only a language simplification, never a new \
interpretation.

Non-negotiable rules:
- Preserve the original meaning EXACTLY. Only simplify the language.
- Add nothing: no new medical claims, no new treatments, no new urgency, \
no new advice, no timelines, and no dosages that are not in the original.
- The ONLY addition allowed is one short sentence explaining why this kind \
of instruction matters in everyday terms, phrased generically (for example: \
"This helps the care team catch problems early"). It must not state any \
fact that is not already in the original.
- Write at roughly an eighth-grade reading level: short sentences, \
everyday words. If a medical word must be kept, keep it exactly as written \
in the original.
- Do not diagnose, do not reassure about outcomes, do not speculate, and \
do not fill in gaps if the original is vague — stay just as general.
- Do not soften or strengthen the instruction: if the original says "may", \
"should", or "must", keep that same strength.

Output only the rewritten text: 1 to 3 short sentences, no headings, \
no quotation marks, no notes about what you changed.\
"""

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
                ("system", SYSTEM_PROMPT),
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
