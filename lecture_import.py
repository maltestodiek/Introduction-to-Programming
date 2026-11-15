"""Private PDF lecture text extraction. Uploaded PDFs are never persisted."""
from io import BytesIO
from pypdf import PdfReader

MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_PAGES = 100
MAX_SECTION_CHARS = 12_000

class LectureImportError(ValueError):
    pass

def _normalise(value):
    return " ".join((value or "").split())

def parse_lecture_pdf(raw):
    if not raw or len(raw) > MAX_FILE_BYTES:
        raise LectureImportError("Choose a PDF smaller than 50 MB.")
    if not raw.startswith(b"%PDF-"):
        raise LectureImportError("The uploaded file is not a valid PDF.")

    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as exc:
        raise LectureImportError("This PDF could not be read. Export it again and retry.") from exc

    if not reader.pages:
        raise LectureImportError("This PDF has no pages.")
    if len(reader.pages) > MAX_PAGES:
        raise LectureImportError("A lecture may contain at most 100 pages.")

    sections = []
    empty_pages = []
    for number, page in enumerate(reader.pages, start=1):
        try:
            text = _normalise(page.extract_text())
        except Exception:
            text = ""
        if not text:
            empty_pages.append(number)
            continue
        sections.append({
            "position": len(sections) + 1,
            "title": f"Page {number}",
            "page_start": number,
            "page_end": number,
            "content": text[:MAX_SECTION_CHARS],
        })

    if not sections:
        raise LectureImportError(
            "No selectable text was found. Scanned PDFs need OCR, which is not supported yet."
        )

    return {
        "sections": sections,
        "page_count": len(reader.pages),
        "empty_pages": empty_pages,
    }
