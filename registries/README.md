# Registries

Append-only JSONL. Never edit or delete a past line. Supersede with a new line (new `recorded_at`, same id if updating status).

| File | Object | Schema |
|---|---|---|
| `ideas.jsonl` | Idea | `schemas/idea.schema.json` |
| `hypotheses.jsonl` | Hypothesis | `schemas/hypothesis.schema.json` |
| `experiments.jsonl` | Experiment spec record | `schemas/experiment.schema.json` |
| `runs.jsonl` | Immutable run | `schemas/run.schema.json` |
| `decisions.jsonl` | Decision | `schemas/decision.schema.json` |
| `errors.jsonl` | Error | `schemas/error.schema.json` |

R0-A seeds only IDs that already exist in v4.1 §6 (decisions and errors), as references, without copying research results.

`ideas.jsonl`, `hypotheses.jsonl`, `experiments.jsonl`, and `runs.jsonl` are empty. No legacy HYP/EXP/RUN ids are invented.

Validate: `python3 registries/validate_registries.py`
