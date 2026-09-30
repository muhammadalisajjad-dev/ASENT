import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {SableFilm, SABLE_FRAMES} from './sable-film';
import {CAVRFilm, CAVR_FRAMES} from './cavr-film';
import {SATRAFilm, SATRA_FRAMES} from './satra-film';
import {IntegratedFilm, INTEGRATED_FRAMES} from './integrated-film';
import {FullFilm, FULL_FRAMES} from './full-film';

const Root: React.FC = () => {
  const defaultSableEvidence = {
    status: 'PRESERVED',
    successor: 'module.storage.aws_s3_bucket.data',
    runId: 'c6f6239d62b4',
    finalDecision: 'REVIEW',
    reasons: [],
    stale: false,
    integrityValid: true,
  };

  const defaultCavrEvidence = {
    status: 'VERIFIED',
    packageName: 'pypdf',
    version: '6.19.0',
    sha256: '7e5d6e730e7dae87d560a2cee218b852f6498c8be61966f3cd02ead971e48d14',
    artifact: 'artifacts/pypdf-6.19.0-py3-none-any.whl',
    ecosystem: 'PyPI',
    violations: 0,
    runId: 'c6f6239d62b4',
    stale: false,
    integrityValid: true,
    required: ['FILE_READ', 'FILE_WRITE'],
    denied: ['EXECUTE_BINARY', 'NETWORK_CONNECT', 'PERSISTENCE_WRITE', 'PROCESS_CREATE', 'SECRET_ACCESS'],
  };

  const defaultSatraEvidence = {
    status: 'INCONCLUSIVE',
    route: 'GET /invoices/{invoice_id}',
    subject: 'authenticated normal user',
    expectedStatus: 403,
    dockerExit: 125,
    dockerBackend: 'docker',
    ollamaAvailable: false,
    oracleDiagnosis: 'INCONCLUSIVE',
    oracleReason: 'Counterfactual not independently shown to violate the contract',
    ruleId: 'AUTHZ.IDOR.001',
    action: 'GET invoice',
    counterfactual: 'bypass can_access_invoice ownership guard',
    mutantOperator: 'AST replace can_access_invoice body with return True',
    runId: 'c6f6239d62b4',
    stale: false,
    integrityValid: true,
  };

  const defaultIntegratedEvidence = {
    runId: 'c6f6239d62b4',
    finalDecision: 'REVIEW',
    reasons: ['SATRA application change verification was INCONCLUSIVE'],
    applicable: ['CAVR', 'SATRA', 'SABLE'],
    modules: {
      CAVR: {status: 'VERIFIED', stale: false, integrityValid: true},
      SATRA: {status: 'INCONCLUSIVE', stale: false, integrityValid: true},
      SABLE: {status: 'PRESERVED', stale: false, integrityValid: true},
    },
  };

  return (
    <>
      <Composition
        id="SABLE"
        component={SableFilm}
        durationInFrames={SABLE_FRAMES}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          evidence: defaultSableEvidence,
        }}
      />
      <Composition
        id="CAVR"
        component={CAVRFilm}
        durationInFrames={CAVR_FRAMES}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          evidence: defaultCavrEvidence,
        }}
      />
      <Composition
        id="SATRA"
        component={SATRAFilm}
        durationInFrames={SATRA_FRAMES}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          evidence: defaultSatraEvidence,
        }}
      />
      <Composition
        id="INTEGRATED"
        component={IntegratedFilm}
        durationInFrames={INTEGRATED_FRAMES}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          evidence: defaultIntegratedEvidence,
        }}
      />
      <Composition
        id="FULL"
        component={FullFilm}
        durationInFrames={FULL_FRAMES}
        fps={30}
        width={1280}
        height={720}
        defaultProps={{
          evidence: {
            cavr: defaultCavrEvidence,
            satra: defaultSatraEvidence,
            sable: defaultSableEvidence,
            integrated: defaultIntegratedEvidence,
          },
        }}
      />
    </>
  );
};

registerRoot(Root);
