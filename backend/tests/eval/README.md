# Orion Evaluation Harness

The Orion evaluation harness provides a deterministic, reproducible benchmark for measuring the correctness and safety of Orion's repository analysis and supervised coding-agent workflows.

The harness is intentionally separate from the production application and is designed to answer two questions:

1. **Does Orion's system behave correctly on known repository tasks?**
2. **Does a future model or agent change improve or regress that behavior?**

A passing evaluation is evidence that the tested behavior works for the defined cases. It is **not** evidence that Orion is universally reliable or that the underlying model is production-perfect.

## Evaluation Structure

The evaluation suite is divided into three categories.

### 1. Graph QA

Graph QA evaluates deterministic repository-understanding capabilities:

* symbol lookup;
* caller analysis;
* callee analysis;
* impact analysis;
* dependency/path traversal.

Current cases:

| Case        | Capability                            |
| ----------- | ------------------------------------- |
| `graph-001` | Symbol lookup for `app.run`           |
| `graph-002` | Callers of `parser.parse`             |
| `graph-003` | Callees of `app.run`                  |
| `graph-004` | Impact analysis for `parser.parse`    |
| `graph-005` | Path from `app.run` to `parser.parse` |

### 2. Agent Proposal

Agent proposal evaluation exercises Orion's supervised edit workflow:

* creating a proposed change;
* ensuring proposal state is preserved before application;
* applying an explicitly approved proposal;
* verifying the resulting filesystem state.

Current cases:

| Case        | Capability                 |
| ----------- | -------------------------- |
| `agent-001` | Create a proposal          |
| `agent-002` | Apply an approved proposal |

### 3. Safety

Safety evaluation exercises filesystem and edit-workflow protections:

* path traversal protection;
* stale-file detection;
* explicit approval requirements;
* validation failure and rollback.

Current cases:

| Case         | Capability                                 |
| ------------ | ------------------------------------------ |
| `safety-001` | Reject path escape during application      |
| `safety-002` | Reject stale file content                  |
| `safety-003` | Reject application without approval        |
| `safety-004` | Roll back changes after validation failure |

## Current Baseline

The current controlled evaluation set contains **11 cases**:

* 5 Graph QA cases;
* 2 Agent Proposal cases;
* 4 Safety cases.

Current baseline:

```text
Cases:         11
Passed:        11
Failed:        0
Pass rate:     100.0%
Average score: 100.0%
```

The backend regression suite currently contains **150 tests**, all passing.

These numbers represent the current baseline for the evaluation fixture and test suite. They should be preserved when introducing changes to Orion.

## Running the Evaluation

Run the complete evaluation suite from the `backend` directory:

```powershell
python -m tests.eval.run_all
```

Run individual evaluation categories when debugging:

```powershell
python -m tests.eval.run_graph_eval
python -m tests.eval.agent_adapter
python -m tests.eval.safety_adapter
```

Run the complete backend regression suite:

```powershell
python -m unittest discover -s tests -v
```

A change should not be considered safe to merge if it causes an existing evaluation case or regression test to fail without an intentional, documented change to the expected behavior.

## Fixture Repository

The deterministic Graph QA cases operate against:

```text
backend/tests/eval/fixture_repo/
```

The fixture contains a deliberately small Python repository with:

* `app.py`;
* `parser.py`;
* `validator.py`.

Its purpose is to provide known ground truth for graph relationships.

The fixture should remain:

* small;
* deterministic;
* self-contained;
* version-controlled;
* free of external dependencies;
* stable across evaluation runs.

Changes to the fixture can change evaluation results and should therefore be treated as benchmark changes rather than ordinary test-fixture cleanup.

## Evaluation Architecture

The harness separates test definitions from execution and scoring.

```text
tests/eval/
│
├── cases.py
│   └── Evaluation case definitions and expected results
│
├── runner.py
│   └── Common result and scoring infrastructure
│
├── graph_adapter.py
│   └── Graph QA evaluation against Orion graph state
│
├── agent_adapter.py
│   └── Agent proposal workflow evaluation
│
├── safety_adapter.py
│   └── Safety and rollback evaluation
│
├── run_graph_eval.py
│   └── Graph-only evaluation entry point
│
├── run_all.py
│   └── Canonical complete evaluation entry point
│
└── fixture_repo/
    └── Controlled repository used by Graph QA
```

The adapters translate Orion's actual runtime behavior into `EvalResult` objects. The common runner then aggregates those results consistently.

## Scoring

Each evaluation case produces a score between `0.0` and `1.0`.

For deterministic cases, the score is based on explicit checks against expected behavior.

The aggregate report includes:

* total cases;
* passed cases;
* failed cases;
* pass rate;
* average score;
* results grouped by category.

A 100% score means every currently defined assertion passed. It does not imply correctness outside the benchmark.

## System Evaluation vs. Model Evaluation

The evaluation harness is primarily a **system evaluation**.

A failure can originate from several layers:

```text
User task
    ↓
Model / Agent
    ↓
Agent workflow
    ↓
Graph / retrieval
    ↓
Safety controls
    ↓
Filesystem
```

Therefore, a failed evaluation must be investigated before attributing it to model quality.

For example:

* a graph-query failure may be a graph construction bug;
* a proposal failure may be workflow logic;
* a path-safety failure may be path validation;
* an incorrect generated patch may actually be a model failure.

This distinction is important before fine-tuning Orion's coding model.

## Model-Quality Benchmarking

When model evaluation is introduced, the existing deterministic cases should remain unchanged as a stable system baseline.

Model experiments should be compared using:

* the same evaluation cases where applicable;
* the same fixture repository;
* the same scoring rules;
* the same safety requirements;
* the same regression suite.

A model change should not be considered an improvement solely because it produces better-looking responses.

The preferred measurement is:

```text
Baseline model
      ↓
Run evaluation
      ↓
Record results
      ↓
Candidate model
      ↓
Run identical evaluation
      ↓
Compare results
```

Future benchmark expansion should add cases that expose observed failures rather than artificially optimizing for a fixed benchmark.

## Safety Principle

Evaluation infrastructure must never weaken production safety guarantees.

Test-only behavior may use explicitly controlled test modes, but production API paths must continue enforcing:

* authentication and authorization;
* approved edit workflows;
* allowed-root restrictions;
* stale-content checks;
* validation;
* rollback on validation failure;
* audit logging.

In particular, test-only validation modes must not become an unrestricted production mechanism for bypassing validation.

## Reproducibility

Evaluation cases should avoid dependence on:

* network availability;
* external APIs;
* nondeterministic services;
* the developer's local repository;
* machine-specific paths;
* unpinned external state.

Temporary directories should be used for filesystem mutation tests where practical.

The complete evaluation should be runnable from a clean backend environment using the commands documented above.

## Extending the Harness

When adding an evaluation case:

1. Add the case definition to `cases.py`.
2. Define explicit expected behavior.
3. Implement or extend the appropriate adapter.
4. Add unit tests for the adapter.
5. Include the case in `run_all.py`.
6. Run the complete evaluation.
7. Run the complete backend regression suite.
8. Document meaningful benchmark changes.

Prefer several small, independent cases over one large scenario.

New cases should target meaningful behavior, particularly failures discovered during real development or testing.

## Baseline Policy

The current 11-case, 100% evaluation result is the initial Orion v1 evaluation baseline.

Future changes should report:

```text
Previous baseline
→ New evaluation result
→ Regression test result
→ Explanation of any changed cases
```

The benchmark should evolve with Orion, but historical results should remain understandable rather than silently changing expected behavior to make a new implementation pass.
