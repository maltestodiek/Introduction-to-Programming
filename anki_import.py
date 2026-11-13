"""Read text-only Basic cards from an Anki .apkg archive.

The parser deliberately accepts a narrow, reviewable subset: two-field Basic
notes. Cloze and media cards remain in the source file and are reported to the
user rather than silently converted into incomplete StudyDuel cards.
"""
from __future__ import annotations

from html import unescape
from html.parser import HTMLParser
import io
import json
import os
import re
import sqlite3
import tempfile
import zipfile


MAX_IMPORTED_CARDS = 100
_MEDIA = re.compile(r"<(?:img|audio|video)\b|\[sound:[^\]]+\]", re.IGNORECASE)
_CLOZE = re.compile(r"\{\{c\d+::", re.IGNORECASE)


class AnkiImportError(ValueError):
    """A package cannot be read as an Anki export."""


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data):
        self.parts.append(data)

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"br", "div", "p", "li"}:
            self.parts.append(" ")


def _plain_text(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(unescape(value))
    parser.close()
    return " ".join("".join(parser.parts).split())


def _database_bytes(package: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            names = set(archive.namelist())
            name = next((candidate for candidate in ("collection.anki21", "collection.anki2") if candidate in names), None)
            if not name:
                raise AnkiImportError("This is not a valid Anki package with a collection database.")
            return archive.read(name)
    except (zipfile.BadZipFile, OSError) as exc:
        raise AnkiImportError("Choose a valid Anki package (.apkg).") from exc


def _read_notes(database: bytes):
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".anki", delete=False) as temporary:
            temporary.write(database)
            path = temporary.name
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as connection:
            row = connection.execute("select models from col limit 1").fetchone()
            if not row:
                raise AnkiImportError("This Anki package has no card models.")
            models = json.loads(row[0])
            notes = connection.execute("select id, mid, flds from notes order by id").fetchall()
            return models, notes
    except (sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        raise AnkiImportError("This Anki package could not be read.") from exc
    finally:
        if path:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass


def parse_basic_apkg(package: bytes) -> dict:
    """Return up to 100 valid Basic text cards and explicit rejection reasons."""
    if not isinstance(package, bytes) or not package:
        raise AnkiImportError("Choose a valid Anki package (.apkg).")
    models, notes = _read_notes(_database_bytes(package))
    cards: list[dict] = []
    skipped: list[dict] = []
    for note_id, model_id, fields in notes:
        model = models.get(str(model_id), {})
        raw_fields = str(fields).split("\x1f")
        joined = "\n".join(raw_fields)
        if model.get("type") == 1 or _CLOZE.search(joined):
            skipped.append({"note_id": str(note_id), "reason": "cloze"})
            continue
        if _MEDIA.search(joined):
            skipped.append({"note_id": str(note_id), "reason": "image"})
            continue
        if model.get("type") != 0 or len(raw_fields) != 2:
            skipped.append({"note_id": str(note_id), "reason": "unsupported"})
            continue
        front, back = (_plain_text(field) for field in raw_fields)
        if not front or not back:
            skipped.append({"note_id": str(note_id), "reason": "incomplete"})
            continue
        if len(cards) >= MAX_IMPORTED_CARDS:
            skipped.append({"note_id": str(note_id), "reason": "limit"})
            continue
        cards.append({"front": front, "back": back})
    return {"cards": cards, "skipped": skipped}
