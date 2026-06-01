---
phase: "03"
slug: implement-nanoclaw-lq-adapter
status: verified
threats_open: 0
asvs_level: 1
created: 2026-06-01
---

# Phase 03 — Security

Per-phase security contract: threat register, accepted risks, and audit trail for
the nanoclaw-lq adapter implementation.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| caller -> NanoclawAdapter constructor | Caller-supplied `group_id` is used to select nanoclaw session/config records. | Group identifier, local DB lookup key |
| nanoclaw container -> adapter | Adapter reads `outbound.db` written by the container. | SQLite rows containing agent messages/status |
| Python adapter -> Node shim | Adapter passes group id, message id, and task content to `send-lab-message.ts`. | CLI argv, task instructions, required deliverable names |
| adapter -> nanoclaw container_configs DB | Adapter writes Docker bind-mount source paths consumed by nanoclaw. | Host paths for LAB documents/output |
| caller -> nanoclaw daemon/container | LAB task instructions are delivered into an agent container. | Prompt text and task metadata |
| human -> mount-allowlist.json | Human-scoped allowlist root controls which host paths nanoclaw may mount. | Local filesystem mount policy |
| nanoclaw container -> Harvey LAB results dir | Agent writes deliverables into the host run output directory. | Generated `.docx` and future output artifacts |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-03-01 | Tampering | `group_id` used in DB path/config selection | mitigate | `NanoclawAdapter.__init__()` calls `_reject_unsafe_relative_path(group_id, "group_id")`; tests cover traversal rejection. | closed |
| T-03-02 | Denial of Service | Persistent SQLite connection across virtiofs/container mount | mitigate | `_poll_for_status()` opens, reads, and closes the DB on each poll iteration and never holds a connection across sleep. | closed |
| T-03-03 | Information Disclosure | Malformed/non-JSON `messages_out` content | accept | JSON parse fallback is local-only and same-machine container scoped; accepted as low value/low risk. | closed |
| T-03-04 | Tampering | `additional_mounts` hostPath values | mitigate | `_configure_additional_mounts()` writes only `task_spec.documents_dir.resolve()` and `output_dir.resolve()`; nanoclaw mount allowlist provides the second gate. | closed |
| T-03-05 | Elevation of Privilege | Node shim subprocess invocation | mitigate | Adapter uses explicit list-form `subprocess.run([...])`, never `shell=True`; `group_id` is prevalidated and `message_id` is UUID4-generated. | closed |
| T-03-06 | Tampering | `containerPath` in `additional_mounts` | mitigate | Adapter hardcodes relative names `lab-documents` and `lab-output`; no caller-controlled container path is accepted. | closed |
| T-03-07 | Denial of Service | SQLite write/read locking | mitigate | Mount config uses open/update/commit/close before wake; status polling opens/closes per read. | closed |
| T-03-08 | Elevation of Privilege | mount-allowlist `allowedRoots` scope | mitigate | Verified allowlist root is scoped to `/Users/houfu/Projects/harvey-labs` with `allowReadWrite: true`, not `/` or the home directory. | closed |
| T-03-09 | Tampering | Container write access to LAB output mount | accept | Accepted for single-task proof: writeable mount is the run's own `results/<run-id>/output` under the LAB tree; same-machine sandboxed container scope. | closed |
| T-03-10 | Spoofing | Reused LAB group session context | accept | Accepted for single-task proof per Phase 3 research; multi-run/session isolation is a Phase 4 concern. | closed |
| T-03-SC | Tampering | Supply-chain/package installs | mitigate | Phase 3 added no Python packages; Node shim uses existing nanoclaw-lq modules and dependencies. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-03 | Malformed message fallback handles local same-machine container output only; no external data disclosure channel introduced by Phase 3. | GSD security review | 2026-06-01 |
| AR-03-02 | T-03-09 | The writable mount is limited to the proof run output directory under the LAB tree; acceptable for the single-task proof run. | GSD security review | 2026-06-01 |
| AR-03-03 | T-03-10 | Agent-shared session reuse is acceptable for Phase 3's single-task proof; isolation and repeated-run semantics are explicitly deferred to Phase 4. | GSD security review | 2026-06-01 |

Accepted risks do not resurface in future audit runs unless the relevant scope
changes, such as moving from single-task proof to repeated benchmark execution.

---

## Evidence

- `lab_harness_runner/task_reader.py` rejects absolute, empty, `.`, and `..` path segments.
- `lab_harness_runner/nanoclaw_adapter.py` validates `group_id`, uses list-form subprocess invocation, hardcodes container paths, configures only documents/output host mounts, and opens/closes SQLite connections per operation.
- `tests/test_nanoclaw_adapter.py` covers `STATUS: DONE`, non-DONE status, timeout, missing DB retry behavior, footer contract, unsafe `group_id`, and dispatch/mount wiring.
- `/Users/houfu/.config/nanoclaw/mount-allowlist.json` contains only `/Users/houfu/Projects/harvey-labs` for this project root.
- Phase 3 UAT passed 3/3 checks, including proof deliverable existence and honest timeout metric reporting.

## Verification Commands

```bash
uv run pytest tests/test_nanoclaw_adapter.py -q
test -s /Users/houfu/Projects/harvey-labs/results/69f75ee0-84e2-44ca-a906-0bca7da7baae/output/discrepancy-analysis-memo.docx
grep -R "shell=True" -n lab_harness_runner scripts tests
```

Notes:
- Pytest result: `8 passed`.
- Deliverable check: passed.
- `shell=True` grep found only an explanatory mitigation comment in `nanoclaw_adapter.py`; no executable use was found.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-06-01 | 11 | 11 | 0 | Codex / gsd-secure-phase |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-06-01
