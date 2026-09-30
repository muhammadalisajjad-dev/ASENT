from backend.orchestrator.run_context import Evidence

class EvidenceBus:
    def __init__(self,store,run):self.store=store;self.run=run
    def emit(self,kind,data):return self.store.event(self.run.run_id,kind,data)
    def publish(self,evidence:Evidence):
        self.store.put_evidence(evidence)
        self.run.module_evidence_ids[evidence.analyzer]=evidence.evidence_id
        self.emit(evidence.analyzer.lower()+'.decision',{'module':evidence.analyzer,'status':evidence.status,'evidence_id':evidence.evidence_id,'duration_ms':evidence.duration_ms,'candidate_snapshot':evidence.candidate_snapshot})
