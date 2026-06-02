# Summary: Phase 03, Plan 01 - Nanoclaw Adapter Core Logic

## Objectives
Implement the core logic of the `NanoclawAdapter` including the STATUS: poll loop, end-state mapping (clean/agent_error/timeout), and the D-04/D-05 inbound-message footer builder. Establish test infrastructure with a synthetic `outbound.db` fixture.

## Work Completed
- **Task 1**: Added `outbound_db` pytest fixture to `tests/conftest.py`. This fixture creates a local SQLite database mirroring the nanoclaw session layout and provides the `messages_out` table for status polling tests.
- **Task 2**: Implemented `NanoclawAdapter` in `lab_harness_runner/nanoclaw_adapter.py`.
    - Added path safety validation via `_reject_unsafe_relative_path` in the constructor.
    - Implemented `_poll_for_status()` using an open/read/close per iteration pattern to handle virtiofs mounts and avoid persistent locks.
    - Implemented end-state mapping: "STATUS: DONE" -> `"clean"`, any other "STATUS: ..." -> `"agent_error"`, and wall-clock deadline -> `"timeout"`.
    - Implemented `_build_message_content()` to append the required D-04/D-05 footer containing output directories, deliverables, and signaling protocols.
- **Task 3**: Created comprehensive unit tests in `tests/test_nanoclaw_adapter.py` covering:
    - Successful poll (STATUS: DONE)
    - Error poll (STATUS: ERROR / STATUS: FAILED)
    - Timeout conditions (empty DB / small deadline)
    - Missing database handling (no exception raised)
    - Footer contract verification
    - Path safety enforcement

## Verification Results
- **Unit Tests**: `uv run pytest tests/test_nanoclaw_adapter.py` passed (8 tests).
- **Contract Alignment**: The implementation satisfies all behavioral requirements specified in Plan 01.
- **Observation**: Current codebase implementation actually includes the dispatch and mount wiring intended for Plan 02, meaning the adapter is fully functional beyond the scope of this plan.

## Relevant Files
- `lab_harness_runner/nanoclaw_adapter.py`
- `tests/conftest.py`
- `tests/test_nanoclaw_adapter.py`
