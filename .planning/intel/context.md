# Context

The source document describes an adapter package tentatively aligned with the
`lab-nanoclaw` shape. It connects Harvey LAB task/evaluation infrastructure to
the local nanoclaw-lq agent system.

LAB is described as having a useful split between execution and scoring: the
scorer reads files from a result directory and does not import the harness. This
project exploits that split by replacing only execution while leaving scoring
and reporting untouched.

nanoclaw-lq is a local agent system using gemma4:26b through Ollama, a Claude
Agent SDK loop, and local document tooling in its own Docker container. The
adapter will supply LAB task instructions and documents to that environment,
then harvest deliverables from the mounted output directory.

The intended community-facing package is not nanoclaw-specific. Package-owned
logic covers task discovery, result directory setup, evaluator invocation,
metrics writing, run aggregation, and reporting handoff. Adapter-owned logic
covers task dispatch, environment details, completion detection, and harness
metrics.
