"""Read Basic cards from an Anki .apkg archive.

The parser deliberately accepts a narrow, reviewable subset: two-field Basic
notes. Text cards are returned directly. Cards with images are returned with
their image files so the text on the images can be read and reviewed before
anything is stored. Cloze, audio and video cards remain in the source file and
are reported to the user rather than silently converted into incomplete cards.
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

import zstandard as zstd


MAX_IMPORTED_CARDS = 100
MAX_IMAGE_BYTES = 4 * 1024 * 1024
MAX_IMAGES_PER_CARD = 3
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
_AUDIO_VIDEO = re.compile(r"<(?:audio|video)\b|\[sound:[^\]]+\]", re.IGNORECASE)
_IMAGE = re.compile(r"""<img\b[^>]*?\bsrc\s*=\s*(?:"([^"]+)"|'([^']+)'|([^\s>]+))[^>]*>""", re.IGNORECASE)
_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
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


def _unzstd(data: bytes) -> bytes:
    if not data.startswith(_ZSTD_MAGIC):
        return data
    with zstd.ZstdDecompressor().stream_reader(io.BytesIO(data)) as reader:
        return reader.read()


def _varint(data: bytes, position: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[position]
        position += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, position
        shift += 7


def _media_entry_names(data: bytes) -> dict[str, str]:
    """Media map of current exports: protobuf MediaEntries, files stored as 0, 1, 2 ..."""
    names: dict[str, str] = {}
    position = index = 0
    while position < len(data):
        key, position = _varint(data, position)
        if key & 7 != 2:
            raise ValueError("unexpected media entry")
        length, position = _varint(data, position)
        entry, position = data[position:position + length], position + length
        name, zip_name, inner = None, str(index), 0
        while inner < len(entry):
            field, inner = _varint(entry, inner)
            kind = field & 7
            if kind == 0:
                value, inner = _varint(entry, inner)
                if field >> 3 == 255:
                    zip_name = str(value)
            elif kind == 2:
                size, inner = _varint(entry, inner)
                if field >> 3 == 1:
                    name = entry[inner:inner + size].decode("utf-8", "replace")
                inner += size
            else:
                raise ValueError("unexpected media field")
        if name:
            names[name] = zip_name
        index += 1
    return names


def _media_files(archive: zipfile.ZipFile) -> dict[str, str]:
    """Return {media file name: archive member} for old (JSON) and current (protobuf) exports."""
    if "media" not in archive.namelist():
        return {}
    raw = _unzstd(archive.read("media"))
    try:
        return {name: member for member, name in json.loads(raw.decode("utf-8")).items()}
    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
        try:
            return _media_entry_names(raw)
        except (ValueError, IndexError):
            return {}


def _card_images(archive: zipfile.ZipFile, media: dict[str, str], side: str, field: str):
    """Images referenced in one field, or None when one cannot be used."""
    images = []
    for match in _IMAGE.finditer(field):
        name = unescape(next(group for group in match.groups() if group))
        mime = IMAGE_TYPES.get(os.path.splitext(name)[1].lower())
        member = media.get(name)
        if not mime or not member or member not in archive.namelist():
            return None
        try:
            data = _unzstd(archive.read(member))
        except zstd.ZstdError:
            return None
        if not data or len(data) > MAX_IMAGE_BYTES:
            return None
        images.append({"side": side, "name": name, "mime": mime, "data": data})
    return images


def _database_bytes(package: bytes) -> bytes:
    try:
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            names = set(archive.namelist())
            if "collection.anki21b" in names:
                try:
                    with zstd.ZstdDecompressor().stream_reader(
                        io.BytesIO(archive.read("collection.anki21b"))
                    ) as reader:
                        return reader.read()
                except zstd.ZstdError as exc:
                    raise AnkiImportError("This Anki package's collection could not be decompressed.") from exc
            name = next(
                (candidate for candidate in ("collection.anki21", "collection.anki2") if candidate in names),
                None,
            )
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
            if row[0]:
                models = json.loads(row[0])
            else:
                models = {
                    str(model_id): {
                        "name": name,
                        "type": 1 if name.casefold().startswith("cloze") else 0 if name.casefold().startswith("basic") else -1,
                    }
                    for model_id, name in connection.execute("select id, name from notetypes").fetchall()
                }
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
    """Return up to 100 Basic cards: text cards, image cards with their images, and rejection reasons.

    Reasons: cloze, media (audio/video), image (an image is missing, not PNG/JPEG/GIF/WebP,
    larger than 4 MB or more than three per card), unsupported, incomplete and limit.
    """
    if not isinstance(package, bytes) or not package:
        raise AnkiImportError("Choose a valid Anki package (.apkg).")
    models, notes = _read_notes(_database_bytes(package))
    try:
        archive = zipfile.ZipFile(io.BytesIO(package))
    except zipfile.BadZipFile as exc:
        raise AnkiImportError("Choose a valid Anki package (.apkg).") from exc
    with archive:
        return _parse_notes(archive, models, notes)


def _parse_notes(archive: zipfile.ZipFile, models: dict, notes) -> dict:
    media = _media_files(archive)
    cards: list[dict] = []
    image_cards: list[dict] = []
    skipped: list[dict] = []
    for note_id, model_id, fields in notes:
        model = models.get(str(model_id), {})
        raw_fields = str(fields).split("\x1f")
        joined = "\n".join(raw_fields)
        if model.get("type") == 1 or _CLOZE.search(joined):
            skipped.append({"note_id": str(note_id), "reason": "cloze"})
            continue
        if _AUDIO_VIDEO.search(joined):
            skipped.append({"note_id": str(note_id), "reason": "media"})
            continue
        if model.get("type") != 0 or len(raw_fields) != 2:
            skipped.append({"note_id": str(note_id), "reason": "unsupported"})
            continue
        images = []
        if _IMAGE.search(joined):
            sides = [_card_images(archive, media, side, field) for side, field in zip(("front", "back"), raw_fields)]
            if any(found is None for found in sides) or sum(len(found) for found in sides) > MAX_IMAGES_PER_CARD:
                skipped.append({"note_id": str(note_id), "reason": "image"})
                continue
            images = sides[0] + sides[1]
        front, back = (_plain_text(_IMAGE.sub(" ", field)) for field in raw_fields)
        sides_ok = [bool(front) or any(image["side"] == "front" for image in images),
                    bool(back) or any(image["side"] == "back" for image in images)]
        if not all(sides_ok):
            skipped.append({"note_id": str(note_id), "reason": "incomplete"})
            continue
        if len(cards) + len(image_cards) >= MAX_IMPORTED_CARDS:
            skipped.append({"note_id": str(note_id), "reason": "limit"})
            continue
        if images:
            image_cards.append({"front": front, "back": back, "images": images})
        else:
            cards.append({"front": front, "back": back})
    return {"cards": cards, "image_cards": image_cards, "skipped": skipped}
