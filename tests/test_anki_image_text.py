import base64
from types import SimpleNamespace as Obj
from unittest.mock import Mock

import pytest

from db import AnkiImportRepository
from logic import combine_card_text
from test_deck_ui import button, deck_app

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40


def test_reading_images_sends_base64_images_and_maps_the_returned_text():
    client=Mock()
    client.functions.invoke.return_value=b'{"texts":[{"id":"0-0","text":"WACC = E/V Re + D/V Rd (1 - T)"}]}'
    texts=AnkiImportRepository(client).read_image_text([{'id':'0-0','mime':'image/png','data':PNG}])
    assert texts=={'0-0':'WACC = E/V Re + D/V Rd (1 - T)'}
    client.functions.invoke.assert_called_once_with('extract-image-text',invoke_options={'body':{'images':[{'id':'0-0','mime':'image/png','data':base64.b64encode(PNG).decode()}]}})


def test_reading_images_keeps_the_safe_function_error():
    class FunctionError(Exception):pass
    response=Mock();response.json.return_value={'error':'The image could not be read. Try a clearer image.'}
    error=FunctionError();error.context=response
    client=Mock();client.functions.invoke.side_effect=error
    with pytest.raises(ValueError,match='clearer image'):
        AnkiImportRepository(client).read_image_text([{'id':'0-0','mime':'image/png','data':PNG}])


@pytest.mark.parametrize('raw',[b'not json',b'{"texts":"x"}'])
def test_unreadable_function_answer_is_an_error(raw):
    client=Mock();client.functions.invoke.return_value=raw
    with pytest.raises(ValueError,match='could not be read'):
        AnkiImportRepository(client).read_image_text([{'id':'0-0','mime':'image/png','data':PNG}])


def test_card_text_combines_written_text_and_text_from_images():
    assert combine_card_text('Formula',['WACC = E/V Re','  ']) =='Formula\nWACC = E/V Re'
    assert combine_card_text('',['Only image text'])=='Only image text'
    assert combine_card_text('Plain',[])=='Plain'


def import_screen(monkeypatch,reads,saved):
    monkeypatch.setattr('db.AnkiImportRepository.read_image_text',lambda self,images:(reads.append(images),{image['id']:'WACC = E/V Re + D/V Rd (1 - T)' for image in images})[1])
    monkeypatch.setattr('db.AnkiImportRepository.save',lambda self,**data:(saved.append(data),{'id':'import-1','count':len(data['cards'])})[1])
    at=deck_app(monkeypatch)
    at.session_state['anki_import_open']=True
    at.session_state['anki_import_result']={'cards':[{'front':'Plain','back':'Text'}],'image_cards':[{'front':'Formula','back':'','images':[{'side':'back','name':'wacc.png','mime':'image/png','data':PNG}]}],'skipped':[]}
    at.run()
    return at


def test_image_cards_are_read_reviewed_and_saved_as_text_cards(monkeypatch):
    reads,saved=[],[]
    at=import_screen(monkeypatch,reads,saved)
    assert any('1 card contains images' in item.value for item in at.info)
    assert button(at,'Save 1 source cards')
    button(at,'Read text from 1 image card').click().run()
    assert [image['id'] for image in reads[0]]==['0-0']
    back=next(field for field in at.text_area if field.label=='Image card 1 · back')
    assert back.value=='WACC = E/V Re + D/V Rd (1 - T)'
    back.set_value('WACC formula with tax shield').run()
    next(field for field in at.text_input if field.label=='Import name').set_value('Finance cards').run()
    button(at,'Save 2 source cards').click().run()
    assert saved[0]['cards']==[{'front':'Plain','back':'Text'},{'front':'Formula','back':'WACC formula with tax shield'}]
    assert not at.exception


def test_image_cards_without_readable_text_are_not_saved(monkeypatch):
    reads,saved=[],[]
    monkeypatch.setattr('db.AnkiImportRepository.save',lambda self,**data:(saved.append(data),{'id':'import-1','count':len(data['cards'])})[1])
    at=import_screen(monkeypatch,reads,saved)
    monkeypatch.setattr('db.AnkiImportRepository.read_image_text',lambda self,images:{image['id']:'' for image in images})
    button(at,'Read text from 1 image card').click().run()
    assert any('No readable text' in item.value for item in at.warning)
    assert button(at,'Save 1 source cards')
