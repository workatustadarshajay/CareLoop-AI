"""Poll a folder for .txt messages, classify each one's urgency with laya, and store the result."""

import json
import logging
import os
import ssl
import time
from pathlib import Path

import httpx
import psycopg
from huggingface_hub import set_client_factory
from laya import Router

logger = logging.getLogger("urgency_watcher")

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://careloop:careloop@localhost:5432/careloop")
WATCH_DIR = Path(os.environ.get("WATCH_DIR", "inbox"))
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "10"))
# Skip files modified this recently; they may still be being written.
SETTLE_SECONDS = 2

QUESTIONS = {
    "urgency": {
        "type": "choice",
        "instructions": "How urgent is this message for the care team?",
        "criteria": {
            "urgent": "needs action today: severe or worsening symptoms, a safety risk, or an emergency",
            "medium": "needs follow-up within a few days: new but stable symptoms, medication or test questions",
            "not_urgent": "routine or informational: scheduling, refills, thanks, general questions",
        },
    }
}

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS urgency;
CREATE TABLE IF NOT EXISTS urgency.messages (
    id            bigserial PRIMARY KEY,
    file_name     text NOT NULL,
    content       text NOT NULL,
    urgency       text NOT NULL CHECK (urgency IN ('urgent', 'medium', 'not_urgent')),
    confidence    double precision,
    routed_model  text,
    answer        jsonb NOT NULL,
    processed_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS messages_urgency_idx ON urgency.messages (urgency, processed_at DESC);
"""

INSERT_SQL = """
INSERT INTO urgency.messages (file_name, content, urgency, confidence, routed_model, answer)
VALUES (%s, %s, %s, %s, %s, %s)
RETURNING id
"""


def configure_hub_tls() -> None:
    """Python 3.13's strict X.509 checks reject some proxy root CAs; opt out of only that flag."""
    if os.environ.get("RELAX_X509_STRICT") != "1":
        return
    context = ssl.create_default_context(cafile=os.environ.get("SSL_CERT_FILE"))
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    set_client_factory(lambda: httpx.Client(verify=context, follow_redirects=True, timeout=None))


def classify(router: Router, text: str) -> tuple[str, float | None, str | None, dict]:
    result = router.predict(text, QUESTIONS)
    answer = result["answers"]["urgency"]
    choice = answer["choice"]
    return choice, answer.get("probabilities", {}).get(choice), result.get("routing", {}).get("model"), answer


def move(path: Path, folder: str) -> None:
    target_dir = WATCH_DIR / folder
    target_dir.mkdir(exist_ok=True)
    path.rename(target_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{path.name}")


def ready_files() -> list[Path]:
    now = time.time()
    return sorted(
        path
        for path in WATCH_DIR.glob("*.txt")
        if path.is_file() and now - path.stat().st_mtime >= SETTLE_SECONDS
    )


def process_batch(router: Router) -> None:
    files = ready_files()
    if not files:
        return
    with psycopg.connect(DATABASE_URL) as conn:
        for path in files:
            try:
                text = path.read_text(encoding="utf-8").strip()
                if not text:
                    raise ValueError("file is empty")
                urgency, confidence, model, answer = classify(router, text)
                with conn.transaction():
                    row_id = conn.execute(
                        INSERT_SQL,
                        (path.name, text, urgency, confidence, model, json.dumps(answer, default=float)),
                    ).fetchone()[0]
                move(path, "processed")
                confidence_text = f"{confidence:.2f}" if confidence is not None else "n/a"
                logger.info("%s -> %s (confidence %s, row %s)", path.name, urgency, confidence_text, row_id)
            except Exception:
                logger.exception("Failed to process %s; moved to failed/", path.name)
                move(path, "failed")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    WATCH_DIR.mkdir(parents=True, exist_ok=True)
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(SCHEMA_SQL)

    logger.info("Loading laya (the first run downloads the model checkpoint)...")
    configure_hub_tls()
    router = Router()
    classify(router, "Warm-up message.")
    logger.info("Watching %s every %s s for .txt files", WATCH_DIR.resolve(), POLL_SECONDS)

    while True:
        try:
            process_batch(router)
        except Exception:
            logger.exception("Poll cycle failed; retrying next cycle")
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopped")
