import io
import json
import sqlite3
import tempfile
import zipfile

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
