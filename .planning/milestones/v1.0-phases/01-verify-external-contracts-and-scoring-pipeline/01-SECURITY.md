# Phase 01 Security Verification

**Phase:** 01 - verify-external-contracts-and-scoring-pipeline
**ASVS Level:** 1
**Config:** block_on=open threats
**Result:** SECURED
**Threats Open:** 0
**Threats Closed:** 4/4

## Scope

This audit verifies only the threats declared in the Phase 01
`<threat_model>` block. Implementation files were treated as read-only; this
document is the only file written by the audit.

Required reading loaded:

- `.planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-01-PLAN.md`
- `.planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-01-SUMMARY.md`
- `.planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-RESEARCH.md`
- `.planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-VALIDATION.md`
- `.planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-VERIFICATION.md`
- `docs/verified-contracts.md`
- `docs/phase-1-manual-check.md`
- `scripts/lab_probe.py`

No project-local `.codex/skills` or `.agents/skills` directory exists.

## Threat Verification

| Threat ID | Category | Disposition | Status | Evidence |
|-----------|----------|-------------|--------|----------|
| T-01-01 | Path confinement | mitigate | CLOSED | `scripts/lab_probe.py:117` resolves `--harvey-root`; `scripts/lab_probe.py:126-128` constructs and creates only `<harvey-root>/results/<run-id>/output`; `scripts/lab_probe.py:134` writes `metrics.json` only in that run directory. |
| T-01-02 | Path traversal | mitigate | CLOSED | `scripts/lab_probe.py:13-19` rejects absolute paths plus empty, `.`, and `..` segments; `scripts/lab_probe.py:118-119` applies this to `--task` and `--run-id`; `scripts/lab_probe.py:130-132` also applies it to deliverable filenames before writing. |
| T-01-03 | External checkout mutation | mitigate | CLOSED | `docs/verified-contracts.md:175-179` documents the Phase 1 boundary and no nanoclaw mutation; `scripts/lab_probe.py:121-134` reads LAB task metadata and writes only LAB result output plus metrics; no nanoclaw write path appears in `scripts/lab_probe.py`. |
| T-01-04 | Unexpected paid judge call | mitigate | CLOSED | `scripts/lab_probe.py:136-146` only prints the evaluator command and states dry-run does not invoke it; no subprocess, `os.system`, `Popen`, or network call exists in `scripts/lab_probe.py`; `docs/phase-1-manual-check.md:3-11` documents live scoring as optional/manual and credential-dependent. |

## Plan-Time Evidence Checks

| Check | Status | Evidence |
|-------|--------|----------|
| External LAB/nanoclaw contract evidence is based on live source paths rather than stale brief assumptions. | CLOSED | `docs/verified-contracts.md:28-34`, `docs/verified-contracts.md:61-65`, `docs/verified-contracts.md:82-87`, `docs/verified-contracts.md:122-129`, `docs/verified-contracts.md:145-152`, and `docs/verified-contracts.md:165-169` cite concrete local source files and line numbers. |
| Manual proof output and evaluator evidence do not claim more than was run. | CLOSED | `01-VERIFICATION.md:21-25` says the live evaluator run was intentionally not performed; `01-VERIFICATION.md:59-67` limits evidence to the dry-run skeleton, dummy deliverable, metrics file, and file type check. |
| Credentialed, judge-backed, or external environment checks are documented as manual/environment-dependent. | CLOSED | `docs/phase-1-manual-check.md:3-11` states the live scorer is optional, external-judge backed, and may require credentials from Harvey LAB `.env`; `01-VERIFICATION.md:8` records that live judge scoring was not run. |
| Evidence docs cite local verification paths without exposing secrets or credentials. | CLOSED | Secret-pattern scan across Phase 1 docs, phase artifacts, and `scripts/lab_probe.py` found no API keys, secret access keys, private keys, or credential assignments; docs mention only the `.env` location generically at `docs/phase-1-manual-check.md:3-5`. |

## Threat Flags

`01-01-SUMMARY.md` contains no `## Threat Flags` section. No unregistered flags
were recorded.

## Commands Used

```bash
rg -n "Threat Flags|T-01-|threat_model|judge|external|credentials|dry-run|scores\.json|report\.html|secret|credential|\.env|/Users/houfu/Projects/harvey-labs|/Users/houfu/Projects/nanoclaw-lq|live|Evidence|Phase 1 Boundary" .planning/phases/01-verify-external-contracts-and-scoring-pipeline docs scripts
rg -n "(sk-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET|SECRET_ACCESS_KEY|password\s*=|token\s*=|api[_-]?key\s*=|BEGIN (RSA|OPENSSH|PRIVATE) KEY)" docs/verified-contracts.md docs/phase-1-manual-check.md .planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-*.md scripts/lab_probe.py
rg -n "subprocess|os\.system|Popen|run\(|call\(|evaluation\.run_eval" scripts/lab_probe.py
rg -n "^## Threat Flags|Threat Flags" .planning/phases/01-verify-external-contracts-and-scoring-pipeline/01-01-SUMMARY.md
```

