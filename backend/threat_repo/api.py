import json
from fastapi import APIRouter,HTTPException
from fastapi.responses import Response
from pydantic import BaseModel,Field
from backend.threat_repo.models import ThreatImport
from backend.threat_repo.osv_importer import records,query

class Toggle(BaseModel):enabled:bool
class OSVInput(BaseModel):response:dict
class OSVQuery(BaseModel):
    package:str=Field(pattern=r'^[a-zA-Z0-9._-]+$',max_length=160)
    version:str=Field(max_length=80)
    ecosystem:str='PyPI'

def router(service):
    r=APIRouter(prefix='/api/threat-repository',tags=['Threat Repository'])
    @r.get('')
    def snapshot():return service.threats.snapshot()
    @r.get('/history')
    def history():return service.threats.history()
    @r.get('/export')
    def export():return Response(json.dumps(service.threats.export(),indent=2),media_type='application/json',headers={'Content-Disposition':'attachment; filename="asent-threat-repository.json"'})
    @r.post('/import')
    def ingest(body:ThreatImport):
        try:return service.change_threats(body.model_dump(mode='json'))
        except (ValueError,KeyError) as e:raise HTTPException(400,str(e))
    @r.post('/records/{record_id}/enabled')
    def enable(record_id:str,body:Toggle):
        try:return service.change_threats(record_id=record_id,enabled=body.enabled)
        except KeyError:raise HTTPException(404,'Threat record not found')
    @r.post('/osv/import')
    def import_osv(body:OSVInput):
        try:return service.change_threats(records(body.response),reason='Explicit OSV JSON response import')
        except (ValueError,KeyError,TypeError) as e:raise HTTPException(400,str(e))
    @r.post('/osv/query')
    def query_osv(body:OSVQuery):
        try:
            bundle,result=query(body.package,body.version,body.ecosystem)
            return {'change':service.change_threats(bundle,reason='Live OSV query'),'query_evidence':result}
        except ValueError as e:raise HTTPException(503,str(e))
    return r
