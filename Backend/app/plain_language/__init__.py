"""Plain-language card descriptions.

Adds a patient-friendly rewrite of each card's clinical description
without touching any existing creation flow. See listener.py for how
it hooks in after a Card row is inserted.
"""

from app.plain_language.listener import register_listeners

register_listeners()

__all__ = ["register_listeners"]
