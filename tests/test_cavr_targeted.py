import json
from pathlib import Path

from backend.cavr.causal_graph import build
from backend.cavr.repair import rank_repairs
from backend.cavr.sandbox import run_counterfactual
from backend.cavr.trigger_discovery import scan
from backend.orchestrator.context_service import ContextService
from backend.orchestrator.scenarios import apply_scenario
from backend.orchestrator.hashing import digest


def test_safe_adapter_import_attribution_and_unrelated_import(tmp_path):
    from backend.config import ROOT
    from backend.orchestrator.hashing import copy_tree
    project=tmp_path/'project';copy_tree(ROOT/'demo_project'/'InvoiceHub',project)
    (project/'app'/'pdf_adapter.py').write_text('from vendor.invoice_pdf_safe import extract_invoice_text as extract\n\ndef run(data): return extract(data)\n')
    (project/'app'/'unrelated.py').write_text('import unrelated_vendor\ndef run(): return unrelated_vendor.go()\n')
    lock=json.loads((project/'dependencies.lock.json').read_text())
    lock['packages'].append({'name':'invoice-pdf-safe','version':'1.0.0','ecosystem':'LOCAL','artifact':'vendor/invoice_pdf_safe.py','sha256':'0'*64})
    (project/'dependencies.lock.json').write_text(json.dumps(lock))
    ctx=ContextService(project,project)
    attrs=ctx.dependency_context()['dependency_attributions']
    assert any(a['package']=='invoice-pdf-safe' and a['imported_name']=='extract_invoice_text' and a['import_evidence']['module']=='vendor.invoice_pdf_safe' and a['call_site']['file']=='app/pdf_adapter.py' for a in attrs)
    assert not any(a['package']=='invoice-pdf-safe' and a['call_site']['file']=='app/unrelated.py' for a in attrs)


def test_trigger_scanner_records_supported_if_else_file_and_unknown_helper():
    src='''import os\nfrom pathlib import Path\ndef f():\n if os.getenv("CAVR_CANARY_AWS_SECRET"):\n  open("canary.txt").read()\n else:\n  socket.create_connection(("host", 80))\n if Path("feature.flag").exists():\n  subprocess.Popen(["x"])\n if helper():\n  requests.get("https://example.invalid")\n'''
    result=scan({'x.py':src});records=result['triggers']
    assert any(t['trigger_type']==['environment-variable'] and t['activation_known'] for t in records)
    assert any(t['reachability'].endswith('else-branch containment') and t['reachable_sinks'][0]['sink']=='socket.create_connection' for t in records)
    file_trigger=next(t for t in records if 'file-existence' in t['trigger_type'])
    assert file_trigger['supported_activation'] and file_trigger['inputs']==["Path('feature.flag')"]
    unknown=next(t for t in records if 'helper()' in t['predicate'])
    assert not unknown['supported_activation'] and unknown['unsupported_reason']


def test_causal_graph_requires_exact_fixture_marker_and_endpoint():
    events=[{'type':'SECRET_ACCESS','resource':'canary.txt','source':'PYTHON_AUDIT'}, {'type':'NETWORK_CONNECT','resource':'127.0.0.1:18765','source':'HARNESS_INTERCEPT'}]
    good=build('fixture',[],events,['CAVR_FAKE_SECRET_NOT_A_CREDENTIAL'])
    bad=build('fixture',[],events,['CAVR_FAKE_SECRET_NOT_A_CREDENTIAL-extra'])
    assert any(e['relation']=='fixture-linked source-to-sink' for e in good['edges'])
    assert not any(e['relation']=='fixture-linked source-to-sink' for e in bad['edges'])


def test_repair_rank_ignores_caller_security_functionality_booleans():
    current={'name':'invoice-pdf-lab','version':'1.0.0'}
    supplied={'name':'invoice-pdf-safe','version':'1.0.0','level':3,'artifact_verified':True,'security_verified':True,'functional_verified':True,'api_slice':'extract_invoice_text(bytes) -> str'}
    assert rank_repairs(current,[supplied])==[]
    supplied['candidate_id']='safe'
    assert rank_repairs(current,[supplied],verified_candidate_ids=['safe'])


def test_pinned_fixture_runtime_modes_and_counterfactual(tmp_path):
    from backend.config import ROOT
    events=[]
    result=run_counterfactual(ROOT/'scenarios/cavr_controlled/invoice_pdf_lab.py',ROOT/'demo_project/InvoiceHub/fixtures/invoice.pdf',tmp_path,lambda k,d:events.append((k,d)))
    assert result['available'],result
    normal,cf=result['runs']
    assert normal['facts']['canary_received'] is False
    assert cf['facts']['canary_received'] is True
    assert normal['facts']['functional_text']==cf['facts']['functional_text']
    for run in result['runs']:
        modes=run['execution_modes']
        assert {'containerized','kernel_strace_observation','python_audit_only_fallback','receiver_interception'} <= modes.keys()
        assert modes['kernel_strace_observation'] is (run['monitor']=='strace')
        assert modes['python_audit_only_fallback'] is (run['monitor']!='strace')
        assert modes['receiver_interception'] in ('loopback receiver','harness/mock receiver interception')


def test_pinned_repair_candidate_functionality_and_security(tmp_path):
    from backend.config import ROOT
    events=[]
    result=run_counterfactual(ROOT/'scenarios/cavr_controlled/invoice_pdf_safe.py',ROOT/'demo_project/InvoiceHub/fixtures/invoice.pdf',tmp_path,lambda k,d:events.append((k,d)))
    assert result['available'],result
    assert all(r['facts']['functional_text'] for r in result['runs'])
    assert result['runs'][0]['facts']['functional_text']==result['runs'][1]['facts']['functional_text']
    assert all(not r['facts']['canary_received'] for r in result['runs'])
    assert not any(e['type'] in ('SECRET_ACCESS','NETWORK_CONNECT') for r in result['runs'] for e in r['events'])
