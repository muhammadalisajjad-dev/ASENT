from typing import Any,Literal
from pydantic import BaseModel,Field,ConfigDict
from backend.orchestrator.run_context import now
Category=Literal['vulnerabilities','package_threats','behaviors','triggers','source_sink','capability_rules','satra_rules','sable_rules','sources']

class ThreatRecord(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(pattern=r'^[A-Za-z0-9._:-]+$',max_length=160)
    category:Category
    name:str=Field(max_length=250)
    severity:Literal['INFO','LOW','MEDIUM','HIGH','CRITICAL']='INFO'
    description:str=Field(default='',max_length=20000)
    source_id:str=Field(max_length=160)
    enabled:bool=True
    version:int=Field(default=1,ge=1)
    updated_at:str=Field(default_factory=now)
    data:dict[str,Any]=Field(default_factory=dict)

class ThreatImport(BaseModel):
    model_config=ConfigDict(extra='forbid')
    schema_version:str='asent.threat-repository.v1'
    records:list[ThreatRecord]=Field(max_length=5000)
