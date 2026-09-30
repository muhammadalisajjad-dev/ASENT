from backend.threat_repo.repository import active

def rules(knowledge):
    rows={r['id']:r for r in active(knowledge,'sable_rules')}
    missing=[k for k in ('SABLE-S3IAM-001','SABLE-SUCCESSOR-001') if k not in rows]
    model=rows.get('SABLE-S3IAM-001',{}).get('data',{})
    if model.get('unsupported_semantics')!='UNKNOWN' or not model.get('wrong_binding') or not model.get('privilege_widening'):missing.append('unsupported relation semantics')
    return rows,missing
