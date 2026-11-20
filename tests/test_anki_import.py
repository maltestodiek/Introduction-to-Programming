import io
from pathlib import Path
import json
import sqlite3
import tempfile
import zipfile

import zstandard as zstd

import pytest

from anki_import import AnkiImportError, parse_basic_apkg


def apkg(notes, models):
    """Build a tiny .apkg archive with only the database parts the importer reads."""
    with tempfile.NamedTemporaryFile(suffix=".anki") as database:
        with sqlite3.connect(database.name) as connection:
            connection.execute("create table col (models text)")
            connection.execute("create table notes (id integer, mid integer, flds text)")
            connection.execute("insert into col values (?)", (json.dumps(models),))
            connection.executemany("insert into notes values (?, ?, ?)", notes)
        database.seek(0)
        collection = database.read()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("collection.anki2", collection)
    return archive.getvalue()


BASIC = {"1": {"type": 0, "name": "Basic", "flds": [{"name": "Front"}, {"name": "Back"}]}}
CLOZE = {"2": {"type": 1, "name": "Cloze", "flds": [{"name": "Text"}, {"name": "Extra"}]}}


def test_imports_basic_text_cards_and_strips_safe_html():
    data = apkg([(1, 1, "<b>Capital structure</b>\x1fDebt and equity")], BASIC)
    result = parse_basic_apkg(data)
    assert result["cards"] == [{"front": "Capital structure", "back": "Debt and equity"}]
    assert result["skipped"] == []


def test_reports_cloze_and_image_cards_without_importing_them():
    models = {**BASIC, **CLOZE}
    data = apkg(
        [
            (1, 1, "<img src=\"formula.png\">\x1fAnswer"),
            (2, 2, "{{c1::WACC}}\x1fFormula"),
        ],
        models,
    )
    result = parse_basic_apkg(data)
    assert result["cards"] == []
    assert [entry["reason"] for entry in result["skipped"]] == ["image", "cloze"]


def test_rejects_invalid_archives_and_keeps_rejection_specific():
    with pytest.raises(AnkiImportError, match="valid Anki package"):
        parse_basic_apkg(b"not an archive")


def test_only_first_hundred_valid_cards_are_accepted():
    notes = [(index, 1, f"Question {index}\x1fAnswer {index}") for index in range(101)]
    result = parse_basic_apkg(apkg(notes, BASIC))
    assert len(result["cards"]) == 100
    assert result["skipped"][-1]["reason"] == "limit"


def modern_apkg(notes):
    """Build a current Anki archive with a compressed .anki21b collection."""
    with tempfile.NamedTemporaryFile(suffix=".anki") as database:
        with sqlite3.connect(database.name) as connection:
            connection.execute("create table col (models text)")
            connection.execute("create table notes (id integer, mid integer, flds text)")
            connection.execute("create table notetypes (id integer, name text)")
            connection.execute("insert into col values ('')")
            connection.execute("insert into notetypes values (1, 'Basic+')")
            connection.executemany("insert into notes values (?, ?, ?)", notes)
        database.seek(0)
        modern_collection = database.read()

    with zipfile.ZipFile(io.BytesIO(apkg([(99, 1, "Upgrade Anki\\x1f")], BASIC))) as legacy:
        legacy_collection = legacy.read("collection.anki2")

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("collection.anki21b", zstd.ZstdCompressor().compress(modern_collection))
        bundle.writestr("collection.anki2", legacy_collection)
    return archive.getvalue()


def test_imports_current_anki21b_basic_cards_instead_of_legacy_placeholder():
    # Anki separates fields with the real unit separator \x1f, not a literal backslash sequence.
    data = modern_apkg([(1, 1, "What is WACC?\x1fWeighted average cost of capital")])
    result = parse_basic_apkg(data)
    assert result["cards"] == [
        {"front": "What is WACC?", "back": "Weighted average cost of capital"}
    ]
    assert result["skipped"] == []


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def legacy_media_apkg(notes, files, models=BASIC):
    """Older export: a JSON media map and media files stored under their index."""
    archive = io.BytesIO(apkg(notes, models))
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("media", json.dumps({str(index): name for index, name in enumerate(files)}))
        for index, data in enumerate(files.values()):
            bundle.writestr(str(index), data)
    return archive.getvalue()


def _varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def modern_media_apkg(notes, files):
    """Current export: zstd-compressed protobuf media entries and zstd-compressed files."""
    entries = b""
    for name, data in files.items():
        encoded = name.encode()
        entry = b"\x0a" + _varint(len(encoded)) + encoded + b"\x10" + _varint(len(data))
        entries += b"\x0a" + _varint(len(entry)) + entry
    archive = io.BytesIO(modern_apkg(notes))
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("media", zstd.ZstdCompressor().compress(entries))
        for index, data in enumerate(files.values()):
            bundle.writestr(str(index), zstd.ZstdCompressor().compress(data))
    return archive.getvalue()


def test_image_cards_are_kept_with_their_images_for_text_reading():
    data = legacy_media_apkg(
        [(1, 1, "Formula <img src=\"wacc.png\">\x1fWeighted average"), (2, 1, "Plain\x1fText")],
        {"wacc.png": PNG},
    )
    result = parse_basic_apkg(data)
    assert result["cards"] == [{"front": "Plain", "back": "Text"}]
    assert len(result["image_cards"]) == 1
    card = result["image_cards"][0]
    assert (card["front"], card["back"]) == ("Formula", "Weighted average")
    assert [(image["side"], image["name"], image["mime"], image["data"]) for image in card["images"]] == [("front", "wacc.png", "image/png", PNG)]
    assert result["skipped"] == []


def test_current_anki_media_format_is_read():
    data = modern_media_apkg([(1, 1, "<img src=\"slide.jpg\">\x1fAnswer")], {"slide.jpg": b"\xff\xd8\xff" + b"\x00" * 20})
    card = parse_basic_apkg(data)["image_cards"][0]
    assert card["front"] == "" and card["back"] == "Answer"
    assert (card["images"][0]["mime"], card["images"][0]["data"][:3]) == ("image/jpeg", b"\xff\xd8\xff")


def test_audio_unsupported_and_oversized_images_are_skipped_with_reasons():
    data = legacy_media_apkg(
        [
            (1, 1, "[sound:intro.mp3]\x1fAnswer"),
            (2, 1, "<img src=\"vector.svg\">\x1fAnswer"),
            (3, 1, "<img src=\"huge.png\">\x1fAnswer"),
        ],
        {"vector.svg": b"<svg/>", "huge.png": PNG + b"\x00" * (4 * 1024 * 1024)},
    )
    result = parse_basic_apkg(data)
    assert result["image_cards"] == []
    assert [entry["reason"] for entry in result["skipped"]] == ["media", "image", "image"]


def test_image_cards_count_towards_the_hundred_card_limit():
    notes = [(index, 1, f"Question {index}\x1fAnswer {index}") for index in range(99)]
    notes += [(100, 1, "<img src=\"a.png\">\x1fAnswer"), (101, 1, "<img src=\"a.png\">\x1fAnswer")]
    result = parse_basic_apkg(legacy_media_apkg(notes, {"a.png": PNG}))
    assert len(result["cards"]) + len(result["image_cards"]) == 100
    assert result["skipped"][-1]["reason"] == "limit"


def test_saving_an_import_names_the_exact_missing_field():
    from logic import import_save_error
    assert import_save_error('','Corporate Finance','German')=='Import name is missing. Give this import a name.'
    assert import_save_error('   ','Corporate Finance','German')=='Import name is missing. Give this import a name.'
    assert import_save_error('CF notes',None,'German')=='Course is missing. Choose the course this import belongs to.'
    assert import_save_error('CF notes','Corporate Finance',None)=='Deck language is missing. Choose the language of these cards.'
    assert import_save_error('CF notes','Corporate Finance','German') is None


def test_both_import_screens_validate_before_calling_the_server():
    app=(Path(__file__).parents[1]/'app.py').read_text()
    assert app.count('if problem:=import_save_error(name,course,language):st.error(problem)')==2
    assert app.count('name=name.strip()')==2
