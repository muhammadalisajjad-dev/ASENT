"""Opt-in LOCAL research-case intake. No sample downloads and no verdicts in manifests."""
import json
from pathlib import Path
from backend.integrations.tooling import availability
from backend.orchestrator.hashing import snapshot

def load(path,opt_in=False):
    if not opt_in:raise ValueError('Research sample intake requires explicit --opt-in')
    p=Path(path).resolve();body=json.loads(p.read_text())
    if body.get('schema')!='asent.research-case.v1':raise ValueError('Unsupported research manifest schema')
    if not body.get('reference') or not body.get('usage_note'):raise ValueError('Research provenance and usage note required')
    candidate=(p.parent/body['repository']).resolve()
    if not candidate.is_relative_to(p.parent) or not candidate.is_dir():raise ValueError('Supply a local repository inside the case folder')
    if snapshot(candidate)!=body.get('snapshot_sha256'):raise ValueError('Research snapshot hash mismatch')
    tools=availability()
    if not any(tools[e]['available'] for e in ('docker','podman')):raise ValueError('Research execution requires Docker/Podman; no hostile-code host fallback')
    return {'repository':str(candidate),'mode':'research','agent_metadata':{'research_reference':body['reference'],'usage_note':body['usage_note'],'snapshot_sha256':body['snapshot_sha256'],'source_type':'PUBLISHED / RESEARCH CASE'}}
