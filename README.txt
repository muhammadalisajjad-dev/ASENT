ASENT generated defense replays
===============================

The primary defense assets are deterministic visual narratives generated from
local ASENT run/evidence data and the checked-in module and scenario models.
Generate all five assets with:

    /usr/bin/python3 scripts/generate_defense_replays.py --mode all

This creates `cavr.mp4`, `satra.mp4`, `sable.mp4`, `integrated.mp4`, and
`full.mp4` under `frontend/public/defense-replays/`, then atomically updates
`manifest.json`. Use `--mode cavr|satra|sable|integrated|full` for one video.
The local Python/Pillow renderer pipes deterministic frames to ffmpeg and
checks MP4 metadata with ffprobe. It does not use Firefox, X11, or cloud
services. It selects the latest completed local run when available, takes
module/final states from stored evidence, and labels each asset as a controlled
defense replay. If no run exists, it uses checked-in definitions and identifies
the replay as model-only. Live POC evidence remains authoritative.

The module frames animate evidence paths and decision states (not browser
navigation). The combined `full.mp4` is a 105-second sequence. The manifest
records the run id and latest evidence timestamp used; the current runtime may
contain newer failed attempts, so the selected completed run can be older.

The visuals label infrastructure limits explicitly. Ollama is only a
conditional SATRA stage unless run evidence confirms execution. Terraform and
Checkov are not represented as executed without supporting evidence. Current
SABLE implementation covers inline IAM role-to-S3 least privilege and
successor mapping; encryption-at-rest, Block Public Access, and server access
logging are shown as unknown/outside the current model. The integrated replay
shows the actual validity, applicability, and final decision from its source
run rather than assuming acceptance.

The existing Firefox/X11 screen recorder is retained as an optional raw UI
capture path (`./RECORD_DEMO.sh --mode full`). It is not needed to generate or
serve the primary defense assets.

Exact automated workflow
------------------------
1. Open Project intake and show the bundled InvoiceHub SRS, approved plan, and
   policy that the UI loaded from the actual project.
2. Open Live development and click the real Run safe scenario action. This
   creates the bundled Normal first build. Wait for its actual analysis and
   final decision to complete.
3. Open CAVR, SATRA-RV, SABLE, Integrated evidence, and Final trust gate in the
   real UI, pausing on each screen.
4. Open Experiment library and click Run scenario on the bundled Dormant
   capability violation card. This is the catalog's actual controlled
   reproduction. Wait for analysis to complete, then revisit CAVR, SATRA-RV,
   SABLE, Integrated evidence, and Final trust gate for that run.

The workflow does not manually edit the project or seed any analysis result.
Analysis may take several minutes on a slower machine. The final decision shown
is the decision ASENT computed for the run; the recorder does not promise a
specific result.

Short capture check
-------------------
    ./RECORD_DEMO.sh --smoke 12

Smoke mode launches and controls Firefox, waits for the actual ASENT frontend
to load, records the desktop for the requested seconds, and applies the same
ffprobe MP4 checks. It does not start an analysis run.

Dependencies and limits
-----------------------
- Python 3 with Pillow, ffmpeg with libx264, and ffprobe are required for
  generated replays. No graphical session is used.
- The optional raw screen recorder additionally needs Firefox and a working
  X11 session.
- Firefox 83's built-in Marionette protocol is used directly by the separate
  helper in scripts/record_demo_browser.py. No geckodriver, Playwright,
  Selenium, paid service, or cloud API is required. The helper creates and
  removes a temporary Firefox profile. It selects a free localhost port
  (preferring 2828), waits for that exact port across wrapper/child startup,
  and confirms WebDriver:NewSession before UI automation.
- The recorder automates browser navigation and scenario selection. It does
  not automate operating-system setup, install system packages, or guarantee
  the outcome or runtime of analysis. Docker/Podman, strace, Terraform,
  Checkov, and Ollama remain optional according to the current POC.
- The workflow records the desktop, including any unrelated visible desktop
  content. Close private windows and notifications before recording.

Ownership and cleanup
---------------------
If ASENT is healthy at 127.0.0.1:8000, it is reused and left running. Otherwise
the script starts it with the existing START_ASENT.sh flow and stops that
backend on success, failure, or Ctrl-C. It does not call STOP_ASENT.sh or kill
processes based only on a port number. Firefox uses an isolated profile, which
is removed when the helper exits.
