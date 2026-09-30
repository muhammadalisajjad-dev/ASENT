import shutil
from pathlib import Path
from backend.config import DEMO
from backend.orchestrator.hashing import copy_tree,snapshot,files
from backend.integrations.git_adapter import git,init_repo

class WorkspaceManager:
    def __init__(self,root):self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
    def create(self,run,source=None):
        home=self.root/run.run_id;home.mkdir(parents=True)
        base=copy_tree(source or DEMO,home/'baseline')
        # Never inherit hooks, Git config, credentials, or symlinks from an external repository.
        commit=init_repo(base)
        candidate=home/'candidate'
        git(base,'worktree','add','-b','candidate-'+run.run_id,str(candidate),commit)
        run.baseline_commit=commit;run.baseline_workspace=str(base);run.candidate_workspace=str(candidate)
        return candidate
    def freeze(self,run):
        dest=self.root/run.run_id/('snapshot-'+str(run.revision))
        copy_tree(run.candidate_workspace,dest)
        frozen=snapshot(dest)
        if frozen!=snapshot(run.candidate_workspace):raise RuntimeError('Candidate changed while snapshot was captured')
        return dest,frozen
    def reconstruct(self,run):
        source=Path(run.candidate_workspace)
        if snapshot(source)!=run.candidate_snapshot:raise RuntimeError('Candidate changed after verification; cannot reconstruct')
        dest=self.root/run.run_id/('trusted-'+str(run.revision))
        git(self.root/run.run_id,'clone','--no-hardlinks',run.baseline_workspace,str(dest))
        for p in files(dest):(dest/p).unlink()
        copy_tree(source,dest)
        if snapshot(dest)!=run.candidate_snapshot:raise RuntimeError('Reconstruction digest mismatch')
        git(dest,'config','user.name','ASENT Local');git(dest,'config','user.email','asent@localhost')
        git(dest,'add','--all');git(dest,'commit','--allow-empty','-m','ASENT accepted '+run.run_id+' revision '+str(run.revision))
        run.clean_workspace=str(dest);run.clean_commit=git(dest,'rev-parse','HEAD')
        return run.clean_commit
