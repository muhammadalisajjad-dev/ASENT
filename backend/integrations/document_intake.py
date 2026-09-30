"""Bounded text/PDF requirements intake; extracted text still needs developer review."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from backend.config import ROOT
from backend.orchestrator.hashing import digest


def extract_document(filename,content):
    if not content or len(content)>5*1024*1024:raise ValueError('Provide a nonempty document up to 5 MiB')
    suffix=Path(filename).suffix.lower()
    if suffix in ('.txt','.md'):
        try:text=content.decode('utf-8-sig')
        except UnicodeDecodeError:raise ValueError('Text requirements must use UTF-8')
        pages=None
    elif suffix=='.pdf':
        if not content.startswith(b'%PDF-'):raise ValueError('Invalid PDF signature')
        with tempfile.TemporaryDirectory(prefix='asent-srs-') as d:
            path=Path(d)/'requirements.pdf';path.write_bytes(content)
            result=subprocess.run([sys.executable,'-I',str(ROOT/'backend/integrations/pdf_text_entry.py'),str(path)],capture_output=True,text=True,timeout=10)
            if result.returncode:raise ValueError('PDF extraction failed; use a text PDF with at most 50 pages, or export UTF-8 text')
            data=json.loads(result.stdout);text=data['text'];pages=data['pages']
    else:raise ValueError('Supported requirements formats: .txt, .md, .pdf')
    if not text.strip():raise ValueError('No text found. Scanned PDFs require OCR before intake')
    if len(text)>200000:raise ValueError('Extracted requirements exceed 200,000 characters')
    return {'filename':Path(filename).name,'text':text,'pages':pages,'sha256':digest(content),'characters':len(text),'review_required':True}
