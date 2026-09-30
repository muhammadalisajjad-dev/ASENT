"""Local, reviewed API-compatible PDF adapter. No network or secret access."""
from io import BytesIO
from pypdf import PdfReader, apply_configuration

def extract_invoice_text(content: bytes) -> str:
    with apply_configuration(jbig2dec_binary=None):
        return '\n'.join(page.extract_text() or '' for page in PdfReader(BytesIO(content)).pages)
