"""Archive only ASENT runtime. Never remove the user's external repository."""
import argparse
import shutil
from datetime import datetime,timezone
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--yes',action='store_true',help='Confirm server is stopped and archive runtime');args=parser.parse_args()
root=Path(__file__).resolve().parents[1];target=root/'runtime'
if not args.yes:parser.error('Stop the server, then pass --yes. Existing state is archived, not erased.')
if target.exists():
    dest=root/'runtime-backups'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S');dest.parent.mkdir(exist_ok=True)
    shutil.move(str(target),dest);print('Archived runtime to',dest)
else:print('No runtime to reset')
