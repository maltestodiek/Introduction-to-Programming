"""Extract private, text-based PDF lecture slides into bounded AI sources."""
from io import BytesIO
from pypdf import PdfReader

MAX_SOURCES=100
MAX_CHARS=3000

class SlideImportError(ValueError): pass

def parse_pdf_slides(payload:bytes)->dict:
    if not payload:raise SlideImportError('Choose a PDF lecture file.')
    try:reader=PdfReader(BytesIO(payload))
    except Exception as exc:raise SlideImportError('Choose a readable PDF lecture file.') from exc
    if reader.is_encrypted:raise SlideImportError('Encrypted PDFs are not supported.')
    cards=[];skipped=0
    try:
        for page_number,page in enumerate(reader.pages,1):
            text=' '.join((page.extract_text() or '').split())
            if not text:skipped+=1;continue
            for part in (text[index:index+MAX_CHARS] for index in range(0,len(text),MAX_CHARS)):
                if len(cards)==MAX_SOURCES:return {'cards':cards,'skipped':skipped,'limited':True}
                cards.append({'front':f'Lecture slide {page_number}','back':part})
    except Exception as exc:raise SlideImportError('This PDF could not be read.') from exc
    if not cards:raise SlideImportError('This PDF has no selectable text. Scanned slides are not supported yet.')
    return {'cards':cards,'skipped':skipped,'limited':False}
