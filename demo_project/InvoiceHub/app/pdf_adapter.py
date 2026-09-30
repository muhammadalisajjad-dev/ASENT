from io import BytesIO
from pypdf import PdfReader, apply_configuration


def extract_invoice_text(content: bytes) -> str:
    # The optional JBIG2 decoder executes a binary. Disable it for PDF-only extraction.
    with apply_configuration(jbig2dec_binary=None):
        reader = PdfReader(BytesIO(content))
        if len(reader.pages) > 100:
            raise ValueError("Maximum 100 PDF pages")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
