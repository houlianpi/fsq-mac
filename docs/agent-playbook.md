# Agent Playbook

This guide describes the recommended orchestration patterns for agents using `fsq-mac`.

## Canonical Sources

- Machine-readable contract: `docs/agent-contract.json`
- Short discovery summary: `llms.txt`
- Human-readable command contract: `docs/cli-reference.md`

When these artifacts appear to disagree, treat `docs/agent-contract.json` as the canonical machine-readable source and use the CLI reference as the human-readable explanation layer.

## Recommended Control Loop

For element workflows, prefer this sequence:

1. `mac doctor` if environment readiness is unknown.
2. `mac session start`.
3. `mac element inspect --pretty` to establish a fresh snapshot.
4. Choose a stable locator or a ref returned by the latest snapshot.
5. Execute one mutating command.
6. If you need to continue targeting elements, re-inspect after mutations or consume the attached best-effort `snapshot` from the success payload.

## Locator Strategy

- Prefer `--role` plus `--name` when both are stable.
- Prefer `--id` when the application exposes meaningful accessibility identifiers.
- Use refs (`e0`, `e1`, ...) only within the immediate snapshot they came from.
- Treat `--xpath` as replayable but fragile.

## Recovery Recipes

### `ELEMENT_NOT_FOUND`

- Run `mac element inspect` again.
- Re-evaluate whether the UI state changed or the locator is too narrow.
- Retry only if the current state still makes the action logically valid.

### `ELEMENT_REFERENCE_STALE`

- Re-run `mac element inspect`.
- Do not reuse refs across mutations.
- Prefer a locator-based retry when possible.

### `BACKEND_UNAVAILABLE`

- Run `mac doctor backend`.
- Confirm Appium is running and reachable.
- Restart the session only after backend readiness is restored.

### `BACKEND_RPC_TIMEOUT` or `TIMEOUT`

- Retry only if `error.retryable` is true.
- Refresh the snapshot before retrying element actions.
- Increase `--timeout` only when the target state is expected to converge slowly.

## Retry Guidance

- Respect `error.retryable` as the primary retry signal.
- Prefer at most 2 to 3 retries for the same logical step.
- Use a short backoff between retries.
- For element errors, insert a fresh `element inspect` before the retry.

## Web Content Boundary

If snapshot warnings contain `WEB_CONTENT_BEST_EFFORT` or action failure details contain `web_best_effort=true`:

- Treat the result as accessibility-based best effort.
- Do not assume DOM-native semantics.
- Prefer simpler, high-signal interactions and extra verification steps.

## Trace Workflows

- Use `mac trace start` before a multi-step flow when you want replay or code generation.
- Use `mac trace replay <path>` for deterministic re-execution.
- Use `mac trace codegen <path>` when you need a shell artifact.
- Remember that `trace codegen` succeeds via raw text output rather than the usual JSON envelope.
