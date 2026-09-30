# Five-minute defense demonstration

Use the live POC evidence as the authority. The generated videos are short,
deterministic explanations of the module reasoning; they do not execute a new
analysis or replace the evidence shown in the UI. The recorder in
`scripts/record_demo_browser.py` remains an optional raw screen-capture path.

## Replay generation

From the repository root, generate all module narratives and the combined
sequence with:

```sh
/usr/bin/python3 scripts/generate_defense_replays.py --mode all
```

The generator reads the latest completed local run and its evidence records
from `runtime/asent.sqlite3`, plus the checked-in scenario catalog and SABLE
rule model. It renders deterministic Pillow frames and encodes them with local
ffmpeg, validates the MP4 metadata with ffprobe, then atomically replaces the
assets and manifest under `frontend/public/defense-replays/`. Use
`--mode cavr`, `satra`, `sable`, `integrated`, or `full` to render one asset.
Firefox, X11, Docker, Terraform, Checkov, Ollama, AWS, and network access are
not prerequisites for rendering.

## Five-minute sequence

| Time | Show | Explain |
|---|---|---|
| 0:00–0:35 | Project intake, then start the real **Run safe scenario** action. | InvoiceHub's project context and current run. The generator selects stored completed evidence; it does not create results. |
| 0:35–1:25 | Open **CAVR** and play its Defense Replay; then point to the live evidence above it. | Locked dependency artifact → capability contract → selected trigger → normal and controlled lanes → observed events and causal graph → decision and uncertainty. State clearly when the selected run has no runtime activation evidence. |
| 1:25–2:15 | Open **SATRA-RV** and play its Defense Replay; inspect the differential execution evidence. | Trusted baseline and change contract → deterministic tests → conditional adaptive-test stage → validated test and repair candidate → before/after comparison. Ollama is only a conditional stage unless the evidence records a run. |
| 2:15–3:05 | Open **SABLE** and play its Defense Replay; inspect correspondence and projected authorization. | HCL graphs and successor evidence → encryption, Block Public Access, and server access logging shown as UNKNOWN because they are outside the supported model → bounded IAM decision. Terraform/Checkov and deployed AWS results appear as executed only when evidence proves that. |
| 3:05–4:10 | Open **Integrated evidence** and **Final trust gate**; play the integrated replay. | CAVR, SATRA-RV, and SABLE evidence objects → hash/stale validity → applicable boundaries → actual ASENT final decision. Missing, stale, invalid, or inconclusive evidence is not silently converted to ACCEPT. |
| 4:10–5:00 | Return to live module evidence or open **Experiment library** for a controlled case if already prepared. | Distinguish a live newly computed result from a stored run and from a controlled conceptual replay. Mention infrastructure limits relevant to this machine. |

Each module screen keeps the embedded local MP4 player and missing-file
message. A replay footer identifies its source run/evidence timestamp and says
`local controlled replay`. If no runtime run/evidence is present, the narrative
is explicitly model-based. The current selected completed run may differ from
the most recent attempt if that attempt errored; the manifest records the exact
run id and evidence timestamp used.
