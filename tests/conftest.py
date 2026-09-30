import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.orchestrator.service import Service
from backend.orchestrator.context_service import ContextService

@pytest.fixture
def service(tmp_path):return Service(tmp_path/'runtime')

@pytest.fixture
def scenario(service):
    def create(name='safe'):
        run=service.create(name)
        return run,ContextService(run.candidate_workspace,run.baseline_workspace,service.threats.snapshot())
    return create

@pytest.fixture(scope='session')
def integration_runs(tmp_path_factory):
    svc=Service(tmp_path_factory.mktemp('integration')/'runtime');runs={}
    for name in ('safe','satra_weak','satra_bypass','cross_module'):
        run=svc.create(name);svc.analyze(run.run_id,auto_repair=name=='cross_module');runs[name]=svc.store.run(run.run_id)
    yield svc,runs
    import json
    report={'note':'Actual executions from pytest; historical validation only, never dashboard seed data.','runs':{name:svc.report(run.run_id) for name,run in runs.items()}}
    (Path(__file__).resolve().parents[1]/'reports/scenario-validation.json').write_text(json.dumps(report,indent=2))
