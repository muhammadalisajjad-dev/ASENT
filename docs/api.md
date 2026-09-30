# Local API

Base: `http://127.0.0.1:8000`. Interactive OpenAPI: `/docs`.

| Method / path | Purpose |
|---|---|
| `GET /api/health`, `/api/capabilities`, `/api/project`, `/api/scenarios` | Runtime, real tool capabilities and intake defaults |
| `POST /api/intake/document` | Multipart `file`: UTF-8 TXT/MD or text PDF, 5 MiB / 50 pages / 200k characters; returns reviewable text + source digest |
| `POST /api/runs` | `{scenario, repository?, srs?, plan?, policy?, mode?, agent_metadata?, auto_repair?}` → 202 + RunContext |
| `GET /api/runs`, `/api/runs/{id}` | Actual runs; selected run checks current inputs |
| `GET /api/runs/{id}/evidence`, `/events` | Persisted module records and ordered hash-linked events |
| `GET /api/runs/{id}/stream` | SSE, `id:` and JSON `data:`; supports Last-Event-ID / `?after=` |
| `POST /api/runs/{id}/rerun?repair=true` | Fresh evidence, optionally bounded repair |
| `POST /api/runs/{id}/revise` | `{scenario:"sable_preserved"}` applies a supplied developer revision |
| `POST /api/runs/{id}/dependency` | `{command:"pip install pypdf==6.19.0"}` → held proposal + deterministic authorization; no shell execution |
| `POST /api/runs/{id}/events` | `{kind, paths, metadata}`; sensor hints only; starts independent analysis |
| `GET /api/runs/{id}/report/download` | JSON assurance report |
| `GET /api/runs/{id}/artifact?path=...` | Download existing run artifact; path containment enforced |
| `GET /api/experiments` | Reproduction/provenance records |
| `POST /api/replay` | `{bundle:"/absolute/path/bundle.json",auto_repair:false}` |
| `GET /api/threat-repository`, `/history`, `/export` | Current immutable knowledge snapshot, change history and importable JSON |
| `POST /api/threat-repository/import` | Schema-validated records with registered source IDs |
| `POST /api/threat-repository/records/{id}/enabled` | `{enabled:false}`; invalidates affected evidence/cache |
| `POST /api/threat-repository/osv/import` | `{response:{id,affected,...}}` or query response |
| `POST /api/threat-repository/osv/query` | `{package,version,ecosystem:"PyPI"}`; genuine external query, explicit 503 if unavailable |

`mode` is manual, watch, replay or research. Unrecognized repositories/frameworks are not silently generalized into the InvoiceHub model. External source is copied, with Git metadata, environments, runtime output, credential directories and symlinks excluded/rejected. Keep the service on localhost. SSE events are facts about execution; event payloads and imported knowledge are never shell commands.

Research manifest schema:

```json
{
  "schema": "asent.research-case.v1",
  "repository": "candidate",
  "snapshot_sha256": "SHA256_FROM_backend.orchestrator.hashing.snapshot",
  "reference": "published source URL or citation",
  "usage_note": "license and approved research use"
}
```

Use `.venv/bin/python -m backend.cli research path/to/manifest.json --opt-in --wait`. The local case directory and container requirement are validated before registration.
