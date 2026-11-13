import io
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
    data = modern_apkg([(1, 1, "What is WACC?\\x1fWeighted average cost of capital")])
    result = parse_basic_apkg(data)
    assert result["cards"] == [
        {"front": "What is WACC?", "back": "Weighted average cost of capital"}
    ]
    assert result["skipped"] == []
