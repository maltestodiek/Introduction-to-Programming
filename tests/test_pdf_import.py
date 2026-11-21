import importlib
import sys
from types import SimpleNamespace

import pytest
from test_deck_ui import button, deck_app


@pytest.fixture
def parser(monkeypatch):
    class Reader:
        def __init__(self, _payload):
            self.is_encrypted=False
            self.pages=[]
    monkeypatch.setitem(sys.modules,'pypdf',SimpleNamespace(PdfReader=Reader))
    sys.modules.pop('pdf_import',None)
    return importlib.import_module('pdf_import')


def test_pdf_import_rejects_missing_and_oversized_uploads(parser):
    with pytest.raises(parser.SlideImportError,match='Choose a PDF lecture file'):
        parser.parse_pdf_slides(b'')
    with pytest.raises(parser.SlideImportError,match='smaller than 20 MB'):
        parser.parse_pdf_slides(b'x'*(parser.MAX_FILE_BYTES+1))


def test_pdf_import_creates_bounded_slide_sources(parser,monkeypatch):
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


def test_pdf_import_rejects_scanned_or_encrypted_sources(parser,monkeypatch):
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
