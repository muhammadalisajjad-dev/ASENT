#!/usr/bin/env python3
"""Render motion compositions and update only their compatible manifest entries."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / 'video-renderer'
OUT = ROOT / 'frontend/public/defense-replays'
DIST_OUT = ROOT / 'frontend/dist/defense-replays'
DATA = VIDEO / 'data/selected-run.json'

def render_composition(comp_id, out_name, props_dict, title, desc, duration=20):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / out_name
    tmp = OUT / f'{out_name}.remotion.tmp.mp4'
    props_path = VIDEO / f'data/{comp_id.lower()}-props.json'
    props_path.write_text(json.dumps(props_dict, indent=2))

    env = os.environ.copy()
    env['PATH'] = str(Path('/home/seed/.local/node22/bin')) + os.pathsep + env.get('PATH', '')

    cmd = [
        str(VIDEO / 'node_modules/.bin/remotion'),
        'render',
        'src/index.tsx',
        comp_id,
        str(tmp),
        '--props',
        str(props_path),
        '--codec',
        'h264',
        '--pixel-format',
        'yuv420p',
        '--concurrency',
        '2',
    ]
    subprocess.run(cmd, cwd=VIDEO, env=env, check=True)
    subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration,size', '-of', 'json', str(tmp)], check=True, capture_output=True, text=True)
    os.replace(tmp, target)

    if DIST_OUT.exists():
        import shutil
        shutil.copy2(target, DIST_OUT / out_name)

    manifest_path = OUT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {'version': 1, 'replays': {}}
    run_id = (
        props_dict.get('evidence', {}).get('runId')
        or props_dict.get('evidence', {}).get('integrated', {}).get('runId')
        or props_dict.get('evidence', {}).get('sable', {}).get('runId')
    )
    manifest.setdefault('replays', {})[comp_id.lower()] = {
        'file': out_name,
        'title': title,
        'description': desc,
        'duration_seconds': duration,
        'run_id': run_id,
        'source': 'local controlled visualization',
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    if DIST_OUT.exists():
        import shutil
        shutil.copy2(manifest_path, DIST_OUT / 'manifest.json')
    print(f'Rendered {comp_id} -> {target}')

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--mode', choices=['sable', 'cavr', 'satra', 'integrated', 'full', 'all'], default='sable')
    p.add_argument('--db', type=Path, default=ROOT / 'runtime/asent.sqlite3')
    a = p.parse_args()

    subprocess.run([sys.executable, str(ROOT / 'scripts/export_video_evidence.py'), '--db', str(a.db), '--output', str(DATA)], check=True)
    data = json.loads(DATA.read_text())

    modes = ['sable', 'cavr', 'satra', 'integrated', 'full'] if a.mode == 'all' else [a.mode]

    for mode in modes:
        if mode == 'sable':
            sable_props = {
                'evidence': {
                    'status': data['modules']['SABLE']['status'],
                    'successor': data['sable']['successor'],
                    'runId': data['run']['id'],
                    'finalDecision': data['run']['finalDecision'],
                    'reasons': data['run']['reasons'],
                    'stale': data['modules']['SABLE']['stale'],
                    'integrityValid': data['modules']['SABLE']['integrityValid'],
                }
            }
            render_composition(
                'SABLE',
                'sable.mp4',
                sable_props,
                'SABLE · Resource continuity',
                'Visualized security workflow from the selected ASENT run and evidence objects; live evidence remains authoritative.',
                20,
            )
        elif mode == 'cavr':
            cavr_data = data.get('cavr', {})
            cavr_props = {
                'evidence': {
                    'status': data['modules']['CAVR']['status'],
                    'packageName': cavr_data.get('packageName', 'pypdf'),
                    'version': cavr_data.get('version', '6.19.0'),
                    'sha256': cavr_data.get('sha256', ''),
                    'artifact': cavr_data.get('artifact', ''),
                    'ecosystem': cavr_data.get('ecosystem', 'PyPI'),
                    'violations': cavr_data.get('violations', 0),
                    'runId': data['run']['id'],
                    'stale': data['modules']['CAVR']['stale'],
                    'integrityValid': data['modules']['CAVR']['integrityValid'],
                    'required': cavr_data.get('required', ['FILE_READ', 'FILE_WRITE']),
                    'denied': cavr_data.get('denied', ['NETWORK_CONNECT', 'PROCESS_CREATE']),
                }
            }
            render_composition(
                'CAVR',
                'cavr.mp4',
                cavr_props,
                'CAVR · Capability assurance',
                'Visualized security workflow from the selected ASENT run and evidence objects; live evidence remains authoritative.',
                20,
            )
        elif mode == 'satra':
            satra_data = data.get('satra', {})
            satra_props = {
                'evidence': {
                    'status': data['modules']['SATRA']['status'],
                    'route': satra_data.get('route', 'GET /invoices/{invoice_id}'),
                    'subject': satra_data.get('subject', 'authenticated normal user'),
                    'expectedStatus': satra_data.get('expectedStatus', 403),
                    'dockerExit': satra_data.get('dockerExit', 125),
                    'dockerBackend': satra_data.get('dockerBackend', 'docker'),
                    'ollamaAvailable': satra_data.get('ollamaAvailable', False),
                    'oracleDiagnosis': satra_data.get('oracleDiagnosis', 'INCONCLUSIVE'),
                    'oracleReason': satra_data.get('oracleReason', ''),
                    'ruleId': satra_data.get('ruleId', 'AUTHZ.IDOR.001'),
                    'action': satra_data.get('action', 'GET invoice'),
                    'counterfactual': satra_data.get('counterfactual', 'bypass can_access_invoice ownership guard'),
                    'mutantOperator': satra_data.get('mutantOperator', 'AST replace can_access_invoice body with return True'),
                    'runId': data['run']['id'],
                    'stale': data['modules']['SATRA']['stale'],
                    'integrityValid': data['modules']['SATRA']['integrityValid'],
                }
            }
            render_composition(
                'SATRA',
                'satra.mp4',
                satra_props,
                'SATRA-RV · Change assurance',
                'Visualized security workflow from the selected ASENT run and evidence objects; live evidence remains authoritative.',
                20,
            )
        elif mode == 'integrated':
            integrated_props = {
                'evidence': {
                    'runId': data['run']['id'],
                    'finalDecision': data['run']['finalDecision'],
                    'reasons': data['run']['reasons'],
                    'applicable': data['run'].get('applicable', ['CAVR', 'SATRA', 'SABLE']),
                    'modules': {
                        'CAVR': {
                            'status': data['modules']['CAVR']['status'],
                            'stale': data['modules']['CAVR']['stale'],
                            'integrityValid': data['modules']['CAVR']['integrityValid'],
                        },
                        'SATRA': {
                            'status': data['modules']['SATRA']['status'],
                            'stale': data['modules']['SATRA']['stale'],
                            'integrityValid': data['modules']['SATRA']['integrityValid'],
                        },
                        'SABLE': {
                            'status': data['modules']['SABLE']['status'],
                            'stale': data['modules']['SABLE']['stale'],
                            'integrityValid': data['modules']['SABLE']['integrityValid'],
                        },
                    },
                }
            }
            render_composition(
                'INTEGRATED',
                'integrated.mp4',
                integrated_props,
                'Cross-module convergence · evidence to trust gate',
                'Visualized security workflow from the selected ASENT run and evidence objects; live evidence remains authoritative.',
                15,
            )
        elif mode == 'full':
            cavr_data = data.get('cavr', {})
            satra_data = data.get('satra', {})
            full_props = {
                'evidence': {
                    'cavr': {
                        'status': data['modules']['CAVR']['status'],
                        'packageName': cavr_data.get('packageName', 'pypdf'),
                        'version': cavr_data.get('version', '6.19.0'),
                        'sha256': cavr_data.get('sha256', ''),
                        'artifact': cavr_data.get('artifact', ''),
                        'ecosystem': cavr_data.get('ecosystem', 'PyPI'),
                        'violations': cavr_data.get('violations', 0),
                        'runId': data['run']['id'],
                        'stale': data['modules']['CAVR']['stale'],
                        'integrityValid': data['modules']['CAVR']['integrityValid'],
                        'required': cavr_data.get('required', ['FILE_READ', 'FILE_WRITE']),
                        'denied': cavr_data.get('denied', ['NETWORK_CONNECT', 'PROCESS_CREATE']),
                    },
                    'satra': {
                        'status': data['modules']['SATRA']['status'],
                        'route': satra_data.get('route', 'GET /invoices/{invoice_id}'),
                        'subject': satra_data.get('subject', 'authenticated normal user'),
                        'expectedStatus': satra_data.get('expectedStatus', 403),
                        'dockerExit': satra_data.get('dockerExit', 125),
                        'dockerBackend': satra_data.get('dockerBackend', 'docker'),
                        'ollamaAvailable': satra_data.get('ollamaAvailable', False),
                        'oracleDiagnosis': satra_data.get('oracleDiagnosis', 'INCONCLUSIVE'),
                        'oracleReason': satra_data.get('oracleReason', ''),
                        'ruleId': satra_data.get('ruleId', 'AUTHZ.IDOR.001'),
                        'action': satra_data.get('action', 'GET invoice'),
                        'counterfactual': satra_data.get('counterfactual', 'bypass can_access_invoice ownership guard'),
                        'mutantOperator': satra_data.get('mutantOperator', 'AST replace can_access_invoice body with return True'),
                        'runId': data['run']['id'],
                        'stale': data['modules']['SATRA']['stale'],
                        'integrityValid': data['modules']['SATRA']['integrityValid'],
                    },
                    'sable': {
                        'status': data['modules']['SABLE']['status'],
                        'successor': data['sable']['successor'],
                        'runId': data['run']['id'],
                        'finalDecision': data['run']['finalDecision'],
                        'reasons': data['run']['reasons'],
                        'stale': data['modules']['SABLE']['stale'],
                        'integrityValid': data['modules']['SABLE']['integrityValid'],
                    },
                    'integrated': {
                        'runId': data['run']['id'],
                        'finalDecision': data['run']['finalDecision'],
                        'reasons': data['run']['reasons'],
                        'applicable': data['run'].get('applicable', ['CAVR', 'SATRA', 'SABLE']),
                        'modules': {
                            'CAVR': {
                                'status': data['modules']['CAVR']['status'],
                                'stale': data['modules']['CAVR']['stale'],
                                'integrityValid': data['modules']['CAVR']['integrityValid'],
                            },
                            'SATRA': {
                                'status': data['modules']['SATRA']['status'],
                                'stale': data['modules']['SATRA']['stale'],
                                'integrityValid': data['modules']['SATRA']['integrityValid'],
                            },
                            'SABLE': {
                                'status': data['modules']['SABLE']['status'],
                                'stale': data['modules']['SABLE']['stale'],
                                'integrityValid': data['modules']['SABLE']['integrityValid'],
                            },
                        },
                    },
                }
            }
            render_composition(
                'FULL',
                'full.mp4',
                full_props,
                'Security mechanism sequence · evidence through the trust gate',
                'Visualized security workflow from the selected ASENT run and evidence objects; live evidence remains authoritative.',
                75,
            )

if __name__ == '__main__':
    main()
