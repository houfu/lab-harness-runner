# Constraints

- Harvey LAB must remain unmodified.
- The project should not rely on LAB's harness-side orchestration internals.
- nanoclaw-lq must not be run inside LAB's sandbox.
- Exact deliverable filenames should be used even if LAB has fuzzy matching.
- Agent completion must not be inferred from any arbitrary outbound message.
- A timeout must produce a distinct run end-state.
- Model, harness, scaffolding, and judge effects must not be conflated in
  result descriptions.
- LAB's judge may call external APIs even if the evaluated agent is local.
- Live repository interfaces must be verified before implementation work relies
  on them.
