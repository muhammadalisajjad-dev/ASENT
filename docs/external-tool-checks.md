# Local checks for paths unavailable on the validation host

Run in Linux / WSL2, from `ASENT`, after setup. These are **commands to execute locally**, not claims that these backends ran during validation. Start ASENT again after changing tools or environment variables. The capability response and each evidence record identify the backend actually used.

## Docker or Podman — implemented, unexecuted here

```bash
docker info
docker build -f docker/sandbox.Dockerfile -t asent-sandbox:local .
docker run --rm --network none --cap-drop ALL --cap-add SYS_PTRACE \
  --security-opt no-new-privileges --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  asent-sandbox:local strace -o /tmp/probe.log true
.venv/bin/python -m pytest tests/test_modules.py -k controlled_dormant -q
.venv/bin/python -m pytest tests/test_integration.py -q
```

Substitute `podman` throughout to test Podman. Review returned JUnit, runtime stderr and the `backend` field. If the image cannot execute, ASENT returns unavailable/inconclusive evidence. It never reports a container result from the fallback. Do not use a privileged container or mount a host credential directory to make a test pass.

## Native strace — implemented; installed but tracing denied here

```bash
sudo apt-get update
sudo apt-get install -y strace
strace -o /tmp/asent-trace-probe.log true
.venv/bin/python -m pytest tests/test_modules.py -k controlled_dormant -q
```

On a host with no container, the second command should select `PINNED_INERT_LAB_STRACE` if the probe succeeds. If it fails, the bundled inert case uses `PINNED_INERT_LAB_PYTHON_AUDIT` and reports the operational error. Python audit tracing was executed during validation. It is not a syscall trace and does not authorize arbitrary-code execution.

## Terraform / Checkov — implemented adapters, unexecuted here

Install Terraform using https://developer.hashicorp.com/terraform/install. Install Checkov with `pipx install checkov` and add its executable to PATH.

```bash
terraform version
terraform fmt -check -recursive demo_project/InvoiceHub/infra
checkov -d demo_project/InvoiceHub/infra --framework terraform --output json --quiet --skip-download
.venv/bin/python -m pytest tests/test_modules.py -k sable -q
```

Terraform formatting can report noncanonical formatting; Checkov can report findings outside SABLE's modeled historical obligation. Retained exit status/output are evidence, not a fabricated SABLE verdict. This PoC does not execute `terraform apply`, deploy AWS, or claim full Terraform validation. The HCL/S3/IAM analyzer was tested independently of these tools. Checkov flags follow its [CLI reference](https://www.checkov.io/2.Basics/CLI%20Command%20Reference.html).

## Ollama — implemented untrusted test generator, unexecuted here

```bash
ollama serve
# In another terminal, after installing a supported local code model:
ollama pull qwen2.5-coder:3b
export ASENT_OLLAMA_MODEL=qwen2.5-coder:3b
bash scripts/start.sh
```

Build the container image first: newly generated Python is refused by the host's builtin-only fallback. Run a SATRA scenario, inspect **Research → Static & adaptive evidence**, and check each candidate's validation outcome. A generated test may be rejected; this is a valid result. The core deterministic test path does not need Ollama. No LLM determines ACCEPT.

## Live OSV — API implemented; live requests timed out here

```bash
.venv/bin/python scripts/refresh_advisories.py
```

Or use **Threat Repository → Public advisory query**. Confirm `LIVE` query metadata if the service is reachable. The delivered pypdf metadata was retrieved from PyPI and has a checked digest and retrieval date. The reviewed historical OSV seed retains its web provenance. Neither is mislabeled as a successful live OSV query.

## Explicitly outside the implemented slice

Semgrep and bpftrace are detected only. There is no executed eBPF backend, general npm analyzer, generic API migration, broad framework verifier or full IAM-condition evaluator. Native Windows execution and rootless/SELinux container configurations are untested. These limitations are separate from the fully tested bounded flows.
