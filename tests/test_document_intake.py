import io
import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
from backend.integrations.document_intake import extract_document
from backend.config import DEMO

def make_srs_pdf():
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    lines=(DEMO/'SRS.md').read_text().splitlines();ops=['BT /F1 9 Tf 25 765 Td 14 TL']
    for line in lines:
        escaped=line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        ops.append('('+escaped+') Tj T*')
    ops.append('ET');stream=DecodedStreamObject();stream.set_data('\n'.join(ops).encode())
    page[NameObject('/Contents')]=writer._add_object(stream)
    out=io.BytesIO();writer.write(out);return out.getvalue()

def test_pdf_srs_extraction():
    pdf=make_srs_pdf();result=extract_document('SRS.pdf',pdf)
    assert 'FR-03' in result['text'] and 'HTTP 403' in result['text']
    assert result['pages']==1 and result['review_required']

def test_text_srs_and_invoice_pdf():
    assert extract_document('SRS.md',(DEMO/'SRS.md').read_bytes())['text'].startswith('# InvoiceHub')
    assert 'Invoice IH-' in extract_document('invoice.pdf',(DEMO/'fixtures/invoice.pdf').read_bytes())['text']

@pytest.mark.parametrize('name,body',[('bad.pdf',b'notpdf'),('bad.txt',b'\xff'),('program.py',b'print(1)'),('empty.md',b'')])
def test_invalid_document_fails_closed(name,body):
    with pytest.raises(ValueError):extract_document(name,body)
