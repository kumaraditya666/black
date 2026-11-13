# Milestone 3B — Docker isolation validation

Date: 2026-11-05. **PARTIALLY COMPLETE / BLOCKED.** Docker execution of trusted fixtures and one real model patch was demonstrated, but a timed-out container continued to run. The existing runner was inspected and exercised without rebuilding or modifying it. Do not expand execution to untrusted repositories. No deployment, GitHub operation or autonomous fix was performed.

## Engine and image

`docker info` succeeded using `desktop-linux`: Docker Desktop server 29.9.2, Linux x86_64, WSL2 kernel `6.18.54.1-microsoft-standard-WSL2`, cgroup v2, default runc runtime and built-in seccomp advertised. WSL default version is 2. Initially no images or containers existed.

No image was configured by the project: `BLACKBOX_REPAIR_DOCKER_IMAGE` expects an image with pytest installed. For this trusted-fixture evaluation a local image `blackbox-m3b-pytest:20261105`, image ID `sha256:5c1b730d1ae3e028494c8f6fa48a67a51d5ed2090ab0ec56b79416adb79b4fe4`, was built from the following temporary Dockerfile:

```dockerfile
FROM python:3.12.12-slim@sha256:f3fa41d74a768c2fce8016b98c191ae8c1bacd8f1152870a3f9f87d350920b7c
RUN pip install --no-cache-dir pytest==8.4.2
USER 65534:65534
```

The running image reported pytest 8.4.2. Its base is digest-pinned; transitive pip dependencies are not hash-locked, so a future rebuild is not byte-reproducible. Use the recorded image ID to select the exact local image. The runner does **not** enforce a non-root user itself: non-root depends on the configured image, and the tag may be replaced. Image provenance and dependency supply-chain security were not independently audited.

## Existing runner and measured controls

`blackbox/repair/execution.py` constructs `docker run --rm` with `--network none`, `--memory 256m`, `--cpus 0.5`, `--pids-limit 64`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--read-only`, `/tmp` tmpfs, and a read-write bind mount of the disposable workspace. It supplies a small explicit environment and does not mount the Docker socket. This evaluation set `BLACKBOX_REPAIR_ISOLATION=docker`; the runner did not fall back to process mode. Default `auto` still permits a process-jail fallback when Docker is unavailable and must not be used to claim Docker isolation.

A harmless probe used the same command construction and image, replacing only the test command with Python `-S` to bypass the Python socket guard and exercise the container's network control. Full output is in `data/m3b-docker-audit.json`:

| Control | Observed |
|---|---|
| User | UID/GID 65534:65534, supplied by image configuration |
| Network | Direct connection to 1.1.1.1:53 returned `ENETUNREACH` (101); not a comprehensive network penetration test |
| Root filesystem | Creating `/blackbox-write-test` returned `EROFS` (30); `/tmp` was writable |
| Capabilities | `/proc/self/status` reported `CapEff: 0000000000000000` |
| Privilege escalation | `/proc/self/status` reported `NoNewPrivs: 1` |
| Seccomp | `/proc/self/status` reported `Seccomp: 2`; daemon advertised its built-in profile. Individual syscall restrictions were not tested |
| Limits | cgroup `memory.max=268435456`, `pids.max=64`, `cpu.max=50000 100000`; actual exhaustion behavior was not tested |
| Secrets/socket | A host-only canary environment variable was absent; `/var/run/docker.sock` did not exist. This checks the specified canary and socket, not every possible host secret or mount |
| Storage | `/tmp` tmpfs and a writable workspace were available. Workspace is deliberately writable; no explicit tmpfs size was configured. Host filesystem escape resistance was not independently established |

**Timeout failure:** A harmless named container using the same Docker command construction slept for 60 seconds; the same `subprocess.run(..., timeout=5)` pattern timed out after 5.03 seconds. `docker inspect` then reported that container still present and running. It was explicitly removed with `docker rm -f`. Thus the host client timeout does **not** terminate or clean up the container. Normal completed containers were removed: `docker ps -a` was empty after testing. The test demonstrates the runner's timeout/lifecycle pattern, not a direct invocation of `run_tests` with a pinned sleeping test. Cleanup on daemon failure or host interruption is also unverified.

## Pinned fixture checks

All registry hashes matched Git revision `b96840fef85585904c9348e213dbbec9c0ca521a`. Each original reproduction and regression was run by `run_tests` in Docker from a fresh materialization. Logs and return codes are in `data/m3b-docker-audit.json`.

| Fixture | Reproduction | Original regression |
|---|---|---|
| division_by_zero | rc 1, expected ZeroDivisionError | rc 1; 1 failed, 2 passed |
| argument_validation | rc 1, expected TypeError | rc 1; 1 failed, 2 passed |
| off_by_one | rc 1, expected IndexError | rc 1; 1 failed, 2 passed |
| missing_config | rc 1, expected KeyError | rc 0; 2 passed |
| unreproducible control | rc 0, already passes | rc 0; 1 passed |

The failures in the three original regression suites are expected on intentionally buggy unpatched code, not container failures. The negative control intentionally does not reproduce the reported exception.

## Real Proof-of-Fix

Forced Docker, `qwen3.5:4b`, context 2048, Ollama timeout 120 seconds. A SQLite backup of the prior synthetic benchmark database was used, preserving its approved argument-validation investigation and its exact evidence/hypothesis hashes; approval `2303ccd0-6d95-4ef2-b768-3728ed7383f8` was labeled `m3a-benchmark`, a fixture-level benchmark approval, **not human production review**. This is an authorized test of a trusted fixture, not evidence of a human review. The source revision and all fixture hashes matched. The existing pipeline generated the patch using Ollama; no manual patch was substituted.

`parse_port(None)` produced TypeError in the before container (rc 1, 1 failed). The generated diff adds `TypeError` to the caught exceptions. The same reproduction passed in a new Docker workspace (rc 0, 1 passed), followed by its regression suite (rc 0, 3 passed). Status was `VERIFIED_IN_TEST_ENVIRONMENT`. Generation request wall time 10,080 ms (including model load), model evaluation 2,457 ms, 1,372 input and 133 output tokens; total repair 12,958 ms. Evidence, diff, outputs and timings are in `data/m3b-docker-proof.json`; copied database `data/m3b-docker-proof.db` is Git-ignored and must be retained. This establishes only the observed behavior under these tests.

## Project regression and remaining work

Full host suite: `python -m pytest -q` produced **83 passed, 1 Starlette/httpx deprecation warning, 0 skipped, 28.14 s**. This is the complete project suite, distinct from the fixture tests run in containers. No code was changed. Existing pre-handoff files and the previous handoff documentation remain intact.

Milestone 3B is blocked until the runner guarantees termination and cleanup after timeout and validates that behavior, enforces or verifies non-root independently of image choice, and has further security review and adversarial isolation tests. Host compromise resistance, all host secret exposure paths, seccomp syscall effects, limits under exhaustion, interruption/daemon-failure cleanup, and general untrusted workload isolation remain unverified. Docker is defense in depth, not proof of safety. Keep arbitrary repositories blocked.
