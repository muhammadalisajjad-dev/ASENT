import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('ASENT_DATA',str(ROOT/'runtime'))).resolve()
DEMO=ROOT/'demo_project'/'InvoiceHub'
VERSION='1.0.0'
MODULES=('CAVR','SATRA','SABLE')
