from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter

import pdf_import as parser
from test_deck_ui import button, deck_app


def test_real_slide_produces_source_text_for_question_generation():
    slide = Path(__file__).with_name('fixtures') / 'lecture-slide.pdf'
    assert parser.parse_pdf_slides(slide.read_bytes()) == {
        'cards': [{'front': 'Lecture slide 1', 'back': 'Capital budgeting'}],
        'skipped': 0,
        'limited': False,
    }


def test_real_reader_rejects_unreadable_and_encrypted_files():
    with pytest.raises(parser.SlideImportError, match='readable PDF'):
        parser.parse_pdf_slides(b'ordinary text')

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=100)
    writer.encrypt('fixture-only')
    encrypted = BytesIO()
    writer.write(encrypted)
    with pytest.raises(parser.SlideImportError, match='Encrypted'):
        parser.parse_pdf_slides(encrypted.getvalue())


def test_pdf_import_rejects_missing_and_oversized_uploads():
    with pytest.raises(parser.SlideImportError,match='Choose a PDF lecture file'):
        parser.parse_pdf_slides(b'')
    with pytest.raises(parser.SlideImportError,match='smaller than 20 MB'):
        parser.parse_pdf_slides(b'x'*(parser.MAX_FILE_BYTES+1))


def test_pdf_import_creates_bounded_slide_sources(monkeypatch):
    class Page:
        def __init__(self,text): self.text=text
        def extract_text(self): return self.text
    class Reader:
        is_encrypted=False
        pages=[Page('  First   slide  '),Page(''),Page('x'*(parser.MAX_CHARS+1))]
        def __init__(self,_payload): pass
    monkeypatch.setattr(parser,'PdfReader',Reader)
    result=parser.parse_pdf_slides(b'%PDF')
    assert result['skipped']==1
    assert [card['front'] for card in result['cards']]==['Lecture slide 1','Lecture slide 3','Lecture slide 3']
    assert result['cards'][0]['back']=='First slide'


def test_pdf_import_rejects_scanned_or_encrypted_sources(monkeypatch):
    class Reader:
        is_encrypted=True
        pages=[]
        def __init__(self,_payload): pass
    monkeypatch.setattr(parser,'PdfReader',Reader)
    with pytest.raises(parser.SlideImportError,match='Encrypted'):
        parser.parse_pdf_slides(b'%PDF')


def test_saved_pdf_import_continues_to_question_generation(monkeypatch):
    monkeypatch.setattr('db.AnkiImportRepository.imports',lambda self:[{
        'id':'pdf-import','name':'Lecture 1','course':'Finance','language':'English',
        'cards':[{'id':'slide-1','front':'Lecture slide 1','back':'Capital budgeting'}],
        'drafts':[],
    }])
    at=deck_app(monkeypatch)
    at.session_state['pdf_import_open']=True
    at.session_state['pdf_import_saved']={'count':1}
    at.run()
    button(at,'Continue to question generation').click().run()
    assert at.session_state.get('pdf_import_open') is None
    assert at.session_state['anki_generation_open'] is True
    assert any(item.value=='Generate reviewed questions' for item in at.header)
    assert not at.exception
