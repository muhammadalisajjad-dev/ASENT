"""Build the portable source/artifact ZIP without runtime state or installed environments."""
import argparse
import hashlib
import os
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',default=str(root.parent/'ASENT_PoC.zip'));args=p.parse_args()
excluded={'.git','.venv','node_modules','__pycache__','.pytest_cache','.mypy_cache','qa'}
paths=[]
for base,dirs,names in os.walk(root):
    dirs[:]=sorted(d for d in dirs if d not in excluded and not d.startswith('runtime'))
    # Include the project-authored scripts/qa tools, despite ignoring any optional root qa npm environment.
    if Path(base)==root/'scripts' and (root/'scripts/qa').is_dir() and 'qa' not in dirs:dirs.append('qa')
    for name in sorted(names):
        path=Path(base)/name
        if name=='setup-validation.log' or path.is_symlink() or name.startswith('.env') or name.endswith(('.pyc','.tsbuildinfo','.sqlite3','.sqlite3-wal','.sqlite3-shm','.zip')):continue
        paths.append(path)
required=['README.md','requirements.lock.txt','frontend/dist/index.html','docs/acceptance-audit.md','reports/acceptance-summary.json','backend/main.py','scripts/setup.sh','scripts/start.sh']
assert all(root/name in paths for name in required),'Required deliverable missing'
manifest=''.join(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+path.relative_to(root).as_posix()+'\n' for path in sorted(paths) if path.name!='SHA256SUMS')
(root/'SHA256SUMS').write_text(manifest)
if root/'SHA256SUMS' not in paths:paths.append(root/'SHA256SUMS')
out=Path(args.output).resolve();out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for path in sorted(paths):archive.write(path,'ASENT/'+path.relative_to(root).as_posix())
with zipfile.ZipFile(out) as archive:
    assert archive.testzip() is None
    assert all('node_modules' not in Path(name).parts and not Path(name).parts[1].startswith('runtime') for name in archive.namelist())
print(out);print(f'{len(paths)} files; {out.stat().st_size:,} bytes; SHA-256 {hashlib.sha256(out.read_bytes()).hexdigest()}')
