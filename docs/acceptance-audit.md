# Final acceptance audit — 2026-09-26

The existing ASENT workspace was preserved and extended. Backend starts, the TypeScript/React frontend builds, and the integrated system is runnable. This is a completed **bounded InvoiceHub PoC**, with the external backends and out-of-scope research capabilities listed separately below.

## Executed checks

- **59 pytest tests passed**, zero failures, in 67.12 seconds. One upstream Starlette TestClient deprecation warning is retained in the output; it did not affect results.
- **15 running-HTTP acceptance checks passed.** Safe → ACCEPT; weak security oracle → BLOCK; ambiguous Terraform successor → REVIEW. All three runs finished without errors.
- A clean ZIP extraction passed every manifest hash and independently reached ACCEPT with exact reconstruction. The real `setup.sh` installed a fresh environment and the real `start.sh` served a fresh safe ACCEPT run.
- **Production frontend build passed:** TypeScript + Vite. Backend syntax compilation/import/start passed.
- **Headless Chromium/Playwright checks passed:** module pages, rule search/provenance, safe acceptance, actual PDF login/upload, knowledge toggle revoking ACCEPT, restored knowledge, SSE receipt and responsive view. Zero page errors and no desktop horizontal overflow.
- The canary, mutation, HCL and repair checks use actual execution/parsing. No external verdict fixture substitutes for an analyzer's final decision.

## Acceptance matrix

| Requirement | Result | Evidence / implementation |
|---|---|---|
| Existing repository preserved | PASS | Existing backend/modules/frontend extended; no replacement architecture |
| Backend starts and frontend builds | PASS | `acceptance-server.log`, `frontend-build.txt` |
| SQLite initializes | PASS | HTTP harness verifies both databases |
| SRS text/PDF intake | PASS | Real PDF and UTF-8 extraction; FR-03/HTTP 403 retained; invalid formats rejected |
| InvoiceHub PDF upload and ownership | PASS | HTTP + browser upload, real pypdf extraction, independent pytest ownership tests |
| Threat Repository populated/versioned | PASS | 49 records across all nine categories, snapshot/version/digests/provenance |
| Threat Repository UI/import/export | PASS | Browser search/inspect/toggle; API schema/import/export validation |
| SRS/plan/policy and RunContext | PASS | API intake + serialization, independent requirement/route contract |
| Git candidate, snapshot, diff, reconstruction | PASS | Actual worktrees; reconstructed manifest equals accepted snapshot |
| CAVR safe path and cache | PASS | Exact registry-confirmed wheel, disabled optional subprocess proof, reused artifact evidence |
| CAVR controlled activation | PASS — degraded monitor | Real normal/activated executions; only activated run sends fake canary to loopback; Python audit records |
| SATRA real pytest | PASS | JUnit from trusted baseline, candidate, ordinary suite and counterfactuals |
| Strong / weak test discrimination | PASS | Strong tests kill valid ownership bypass; weak oracle survives while ordinary pytest is green |
| SATRA repair | PASS | Isolated deterministic repair, actual differential tests, reverified ACCEPT |
| SABLE actual HCL parsing | PASS | Baseline and module-refactor graphs from files |
| SABLE PRESERVED | PASS | Unique successor and exact modeled authorization |
| SABLE REGRESSED | PASS | Wrong target and widened action fixtures |
| SABLE UNKNOWN | PASS | Ambiguous successor, malformed/unsupported input paths |
| Evidence Store / Experiment Library | PASS | Separate logical records, hashes, provenance, integrity/tamper checks and persisted run metadata |
| Cross-module invalidation | PASS | CAVR replacement makes SATRA evidence stale, reruns it, then reaches ACCEPT |
| Dependency edit routes to CAVR | PASS | Changed manifest from repair context invalidates CAVR + SATRA |
| Threat update invalidates relevant evidence | PASS | CAVR rule change revokes current acceptance/cache; SATRA/SABLE records remain compatible |
| Stale evidence refuses ACCEPT | PASS | Explicit stale/input/snapshot/integrity matrix and running API |
| Safe integrated ACCEPT | PASS | `safe-assurance.json`, reconstructed commit |
| Blocking integrated BLOCK | PASS | `block-assurance.json`, SATRA REJECT |
| Uncertain integrated REVIEW | PASS | `review-assurance.json`, SABLE UNKNOWN |
| Knowledge re-enable + fresh verification | PASS | `knowledge-reverified-assurance.json`; no automatic resurrection of stale evidence |
| SSE and report download | PASS | Actual `run.created` event and downloadable assurance JSON |
| Replay / gateway | PASS | Hash-checked file replay; exact-pin proposal authorization, npm fail-closed; CLI report |
| No paid API dependency | PASS | Deterministic core runs without hosted models |
| No frontend timer verdicts | PASS | Source inspection + actual HTTP and browser outcomes |

## Implemented but not executed with the external backend

| Path | Host condition | Local verification |
|---|---|---|
| Docker/Podman execution | Engines absent | Build `docker/sandbox.Dockerfile`; run module/integration tests with engine available |
| Native/container strace monitoring | Binary installed; PTRACE denied | Successful `strace ... true` probe; run canary test and inspect monitor field |
| Terraform CLI formatting evidence | Binary absent | `terraform fmt -check -recursive demo_project/InvoiceHub/infra` |
| Checkov scanning | Binary absent | Install Checkov; run documented Terraform scan and inspect real output |
| Ollama generated candidate tests | Endpoint/model absent | Local model + sandbox image; generated tests still require deterministic validation |
| Live OSV query | Network calls timed out | Refresh script or Research query UI on a host where OSV is reachable |
| Native Windows / rootless/SELinux containers | Not available here | Local platform setup and same acceptance suite |

Exact setup and commands: [external-tool-checks.md](external-tool-checks.md). The executed monitor is explicitly labeled Python audit and is restricted to the shipped inert sources. Bandit ran through the active Python interpreter; capability detection was corrected to account for a module installed outside PATH.

## Genuine scope limits

- General npm verification, broad framework coverage, generic API migrations and arbitrary dependency repair are not implemented. Z3 ranks supported candidates; automatic CAVR replacement is limited to the explicitly mapped adapter.
- SATRA's executable core is the listed InvoiceHub security subset and ownership counterfactual, not dynamic coverage for every knowledge family. Optional Ollama-generated repairs are not implemented; deterministic repairs are.
- eBPF, Semgrep and Trivy execution pipelines are not implemented. Do not present their absence as a tested backend. bpftrace/Semgrep executable detection alone is not integration coverage.
- SABLE supports the defined inline role-policy/S3 model; IAM conditions, managed/bucket-policy composition and deployed AWS semantics are not established. Correspondence scores are transparent fixed hypotheses, not calibrated ground-truth certainty.
- PDF SRS intake extracts text; OCR is not implemented. Sample archival uses a local S3 representation. No cloud resources are deployed.
- Watch/PATH integration is cooperative, not mandatory OS enforcement. No real proprietary-agent unsafe selection or prevalence/superiority result is claimed.

## Source audit and retained artifacts

The requested TODO/FIXME/placeholder/mock/fake/demo-only/hardcoded-verdict/timer search was completed. `reports/source-audit.json` lists the inspected matches. Remaining mentions are HTML form hints, inert canary/loopback terminology, fixture metadata, socket timeouts and explicit research limitations. No critical placeholder security verdict remains. A final targeted module recheck also verifies that causal edges join observed event nodes and that only exact fake-marker receipt is described as a canary flow.

`reports/acceptance-artifacts/` contains actual JUnit, logs and evidence envelopes from the HTTP runs. Report fields retain the original execution paths; these are historical provenance, not portable links. To inspect a retained file, use the matching run ID and relative evidence directory under this folder. The archive does not preload historical runs into a new dashboard.

Before presenting: install prerequisites, run the safe case once, refresh advisories if older than 30 days, and identify your actual runtime backend. No source fix is required for the verified Linux/WSL2 builtin demonstration. Optional backends require local execution before you claim that they work on your machine.
