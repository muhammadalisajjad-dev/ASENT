from backend.threat_repo.repository import active

def rule(knowledge,rule_id):return next((r for r in active(knowledge,'capability_rules') if r['id']==rule_id),None)
