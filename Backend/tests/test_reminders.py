from datetime import date, timedelta
from unittest import IsolatedAsyncioTestCase, TestCase

from app.models.card import Card, CardStatus, CardType
from app.services.reminders import REMINDER_WINDOW_DAYS, ReminderService, reminder_message


class ReminderMessageTests(TestCase):
    def make_card(self, due_date: date | None) -> Card:
        return Card(
            id=1,
            note_id=1,
            type=CardType.TEST,
            description="Get the blood test",
            due_date=due_date,
            status=CardStatus.OPEN,
        )

    def test_due_today(self) -> None:
        today = date(2026, 9, 28)
        self.assertEqual(
            reminder_message(self.make_card(today), today),
            "Get the blood test is due today.",
        )

    def test_due_tomorrow(self) -> None:
        today = date(2026, 9, 28)
        self.assertEqual(
            reminder_message(self.make_card(today + timedelta(days=1)), today),
            "Get the blood test is due tomorrow.",
        )

    def test_due_later(self) -> None:
        today = date(2026, 9, 28)
        self.assertEqual(
            reminder_message(self.make_card(today + timedelta(days=4)), today),
            "Get the blood test is due Oct 2.",
        )

    def test_overdue(self) -> None:
        today = date(2026, 9, 28)
        self.assertEqual(
            reminder_message(self.make_card(today - timedelta(days=1)), today),
            "Get the blood test was due Sep 27.",
        )

    def test_requires_due_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires a due date"):
            reminder_message(self.make_card(None), date(2026, 9, 28))


class FakeCardRepository:
    def __init__(self, cards: list[Card]) -> None:
        self.cards = cards
        self.cutoff: date | None = None

    async def list_due_through(self, cutoff: date) -> list[Card]:
        self.cutoff = cutoff
        return self.cards


class ReminderServiceTests(IsolatedAsyncioTestCase):
    async def test_returns_messages_for_repository_results(self) -> None:
        today = date(2026, 9, 28)
        card = Card(
            id=7,
            note_id=1,
            type=CardType.NEXT_VISIT,
            description="Attend the follow-up visit",
            due_date=today + timedelta(days=3),
            status=CardStatus.OPEN,
        )
        repository = FakeCardRepository([card])

        reminders = await ReminderService(repository).list_upcoming(today)

        self.assertEqual(
            repository.cutoff,
            today + timedelta(days=REMINDER_WINDOW_DAYS),
        )
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0].card_id, 7)
        self.assertEqual(
            reminders[0].message,
            "Attend the follow-up visit is due Oct 1.",
        )
