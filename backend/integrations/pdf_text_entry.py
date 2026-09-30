"""Disposable parser process. No uploaded executable code or shell invocation."""
import json
import sys
try:
    import resource
    resource.setrlimit(resource.RLIMIT_AS,(384*1024*1024,384*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(6,6))
except ImportError:pass # Windows parent still applies a hard subprocess timeout.
from pypdf import PdfReader
from pypdf import apply_configuration
with apply_configuration(jbig2dec_binary=None):
    reader=PdfReader(sys.argv[1])
    if reader.is_encrypted or len(reader.pages)>50:raise ValueError('Unsupported PDF')
    pieces=[]
    for page in reader.pages:
        pieces.append(page.extract_text())
        if sum(map(len,pieces))>200000:raise ValueError('Text budget exceeded')
    print(json.dumps({'pages':len(reader.pages),'text':'\n'.join(pieces)}))
