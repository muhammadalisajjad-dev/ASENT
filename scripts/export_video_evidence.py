#!/usr/bin/env python3
"""Export the dynamically selected ASENT run for the isolated motion renderer."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import generate_defense_replays as source

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', type=Path, default=source.DB)
    p.add_argument('--output', type=Path, default=ROOT / 'video-renderer/data/selected-run.json')
    a = p.parse_args()
    source.DB = a.db.resolve()
    run, evidence, _ = source.load_data()
    if run:
        sys.path.insert(0, str(ROOT))
        try:
            from backend.orchestrator.hashing import digest
            con = sqlite3.connect(source.DB)
            for ev in evidence.values():
                row = con.execute('SELECT content_hash FROM evidence WHERE id=?', (ev['evidence_id'],)).fetchone()
                ev['integrity_valid'] = bool(row and digest({k: v for k, v in ev.items() if k not in ('content_hash', 'integrity_valid', 'stale')}) == row[0])
            con.close()
        except Exception:
            pass

    def status(m):
        return evidence.get(m, {}).get('status', 'MISSING')

    sable = evidence.get('SABLE', {}).get('details', {})
    cavr_det = evidence.get('CAVR', {}).get('details', {})
    cavr_node = next(iter(cavr_det.get('nodes', [])), {})
    satra_det = evidence.get('SATRA', {}).get('details', {})
    satra_contract = satra_det.get('contract', {})
    satra_execs = satra_det.get('executions', {})
    satra_base = satra_execs.get('trusted_baseline', {})
    satra_oracle = satra_det.get('oracle', {})
    satra_adaptive = satra_det.get('adaptive', {})

    output = {
        'run': {
            'id': run.get('run_id') if run else None,
            'finalDecision': (run or {}).get('final_decision', 'REVIEW'),
            'reasons': (run or {}).get('reasons', []),
            'applicable': (run or {}).get('applicable', []),
        },
        'evidenceTimestamp': max((e.get('created_at', '') for e in evidence.values()), default=None) or None,
        'modules': {
            m: {
                'status': status(m),
                'stale': bool(evidence.get(m, {}).get('stale', False)),
                'integrityValid': bool(evidence.get(m, {}).get('integrity_valid', False)),
                'evidenceId': evidence.get(m, {}).get('evidence_id'),
            }
            for m in ('CAVR', 'SATRA', 'SABLE')
        },
        'cavr': {
            'packageName': cavr_node.get('name', 'pypdf'),
            'version': cavr_node.get('version', '6.19.0'),
            'sha256': cavr_node.get('sha256', ''),
            'artifact': cavr_node.get('artifact', ''),
            'ecosystem': cavr_node.get('ecosystem', 'PyPI'),
            'violations': len(cavr_node.get('violations', [])),
            'required': [x.get('capability') for x in cavr_node.get('contract', {}).get('required', [])],
            'denied': cavr_node.get('contract', {}).get('denied', []),
        },
        'satra': {
            'route': satra_contract.get('route', 'GET /invoices/{invoice_id}'),
            'subject': satra_contract.get('subject', 'authenticated normal user'),
            'expectedStatus': satra_contract.get('expected_status', 403),
            'dockerExit': satra_base.get('exit_code'),
            'dockerBackend': satra_base.get('backend', 'docker'),
            'ollamaAvailable': bool(satra_adaptive.get('available', False)),
            'oracleDiagnosis': satra_oracle.get('diagnosis', 'INCONCLUSIVE'),
            'oracleReason': satra_oracle.get('reason', ''),
            'ruleId': satra_contract.get('rule_id', 'AUTHZ.IDOR.001'),
            'action': satra_contract.get('action', 'GET invoice'),
            'counterfactual': satra_contract.get('counterfactual', 'bypass can_access_invoice ownership guard'),
            'mutantOperator': satra_oracle.get('mutant_operator', 'AST replace can_access_invoice body with return True'),
        },
        'sable': {
            'successor': sable.get('successor'),
            'correspondenceReason': sable.get('correspondence_reason'),
            'optionalTools': sable.get('optional_tools', []),
        },
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(output, indent=2) + '\n')
    print(f"Exported selected completed run {output['run']['id'] or '(none)'} → {a.output}")

if __name__ == '__main__':
    main()
