# Agent Eval Suite — versioned score record (PRD R8)

Regenerate with `python -m atlas.agent.evals.runner`. CI runs the same command
as a hard gate: any regression below 100% fails the build.

| | |
|---|---|
| Prompt version | `2024-06-orchestrator-narrator-1` |
| Cases | 16 (PRD minimum: 15) |
| Score | 16/16 = 100% |
| Mode | scripted LLM (deterministic, free, network-free) |

## What each case asserts

Assertions are on **structured outcomes**, never on exact prose — that is what
makes them stable regression detectors.

- **Planning (5):** impairment questions phrased as risk / scenario / regime /
  stress / valuation all route to the `impairment` engine.
- **Refusals (5):** FX, crypto, equity-price, options and unrelated questions
  are declined honestly, the refusal naming the real capabilities.
- **Narration + citations (6):** a compliant narrative validates and does not
  degrade; an uncited number is rejected, retried, then degraded to a valid
  numbers-only summary; a citation to a non-existent artifact degrades; the
  degraded narrative is itself fully cited; the planned engine actually ran;
  a refusal still advertises capabilities.

## History

| Date | Prompt version | Score |
|---|---|---|
| 2026-06-11 | 2024-06-orchestrator-narrator-1 | 16/16 |
