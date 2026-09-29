# Orion Production v1 Spec

Date: 2026-08-31

## Goal

Turn Orion from a local code-graph analyzer into a production-ready code assistant that can:

- analyze repositories,
- answer structural questions from the knowledge graph,
- propose code changes,
- safely apply approved changes,
- and verify those changes with tests before reporting success.

Production v1 is not “fully autonomous coding agent” yet. It is a safe, supervised assistant with strong retrieval, controlled writes, and a clear validation loop.

## Product Definition

### What Orion must do in v1

- Ingest and scan a repository reliably.
- Build and persist a searchable knowledge graph.
- Answer questions about symbols, callers, callees, impact, and paths.
- Suggest changes as diffs or patch plans.
- Apply only approved, bounded edits.
- Run validation after edits.
- Explain what changed and whether validation passed.

### What Orion must not do in v1

- Edit arbitrary files outside the repo root.
- Make silent changes without approval.
- Claim success without running validation.
- Depend on the model for exact graph queries that can be answered deterministically.
- Expose the service publicly without authentication.

## Production v1 Success Criteria

Orion is production-ready for v1 when all of the following are true:

### Reliability

- The app starts cleanly on a fresh checkout.
- A failed scan does not crash the server.
- Graph reads continue to work after restarts.
- Scan jobs survive process restarts or are recoverable from storage.

### Safety

- Only authorized users can access the service.
- File access is restricted to approved project roots.
- Code edits require explicit approval.
- Dangerous actions have guardrails and rollback.

### Code-Editing Capability

- Orion can produce a patch for a requested change.
- Orion can apply a patch only after approval.
- Orion can run targeted tests after applying a change.
- Orion can summarize what changed and whether tests passed.

### Observability

- Logs capture scan, retrieval, model, patch, and test events.
- Health endpoints report the state of the backend and model service.
- Failures are traceable with request IDs or job IDs.

### Model Quality

- The model is good enough for graph QA and patch planning.
- Deterministic graph queries do not rely on the model.
- We can measure where the model fails before deciding on retraining.

## Scope For This Week

### In scope

- Persistent storage for graph state and scan jobs.
- A safe edit workflow: plan -> diff -> apply -> test -> summarize.
- Authentication and basic authorization.
- File/path restrictions for all write actions.
- Logging and health checks.
- An evaluation harness for graph QA and edit tasks.

### Out of scope for v1

- Multi-language parsing beyond the current Python focus.
- Fully autonomous background coding without approval.
- Distributed team collaboration.
- Large-scale enterprise RBAC and tenant management.
- Perfect code generation across arbitrary repos.

## Recommended Architecture For v1

### Read path

1. User asks a question.
2. Orion resolves the relevant symbols from the graph.
3. Orion answers deterministically when the question is structural.
4. Orion uses the model only when synthesis is needed.

### Write path

1. User requests a change.
2. Orion gathers relevant graph context.
3. Orion proposes a patch.
4. Orion shows a diff and impact summary.
5. User approves the patch.
6. Orion applies the patch.
7. Orion runs tests and formatting.
8. Orion reports outcome and logs the result.

## Week Plan

### Day 1

- Freeze the production v1 scope.
- Define the exact supported workflows.
- Define what “done” means.
- Decide which risks are acceptable in v1.

### Day 2

- Add durable storage for graph state and scan jobs.
- Make restarts safe.
- Preserve search and query availability.

### Day 3

- Build the edit workflow and patch representation.
- Add diff generation and patch application.
- Add a validation step after changes.

### Day 4

- Add authentication.
- Add write approval gates.
- Add rollback and file-level restrictions.

### Day 5

- Build evaluation datasets and regression tests.
- Measure graph QA accuracy.
- Measure patch success and test pass rates.

### Day 6

- Add structured logging and health checks.
- Harden config and deployment.
- Add failure reporting and request/job tracing.

### Day 7

- Run a release candidate pass.
- Fix blocker issues.
- Freeze v1 launch criteria.
- Prepare the launch checklist.

## Decision On The Finetuned Model

For v1, the current finetuned model is probably enough for:

- graph question answering,
- summarization,
- and patch planning drafts.

It is not enough on its own for reliable code editing. The system around the model matters more:

- deterministic retrieval,
- patch tools,
- tests,
- approvals,
- and rollback.

So the rule for v1 is:

- improve the product system first,
- then use production failures to decide whether to retrain.

## Day 1 Output

By the end of Day 1, we should have:

- a locked v1 scope,
- a clear non-goal list,
- acceptance criteria,
- the 1-week execution plan,
- and a decision rule for whether the finetuned model needs improvement.

