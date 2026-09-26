from shared.model import build_project
from sable.obligation import load_obligation, bind_baseline, validate_baseline, derive_boundary
from sable.policy import build_policy_model

project = build_project("poc/case01_legitimate_move/baseline")
model = build_policy_model(project)
print("providers:")
for p in model.providers:
    print("  ", p.address, p.kind, "principal=", p.inline_principal, "doc=", p.document,
          "stmts=", [(s.effect, s.actions, len(s.resource_values)) for s in p.statements],
          "unsupported=", p.unsupported)
print("attachments:", model.attachments)
print("model unsupported:", model.unsupported)

obligation = load_obligation("poc/case01_legitimate_move/obligation.json")
obligation = bind_baseline(project, obligation)
print("obligation:", obligation.as_dict())
derived = derive_boundary(project, model)
print("derived:", derived.as_dict())
baseline = validate_baseline(project, model, obligation)
print("validated:", baseline.validated)
for check in baseline.checks:
    print("   ", check["id"], check["status"], "-", check["detail"])
print("supporting:", baseline.supporting_nodes)
print("auth status:", baseline.authorization.status)
