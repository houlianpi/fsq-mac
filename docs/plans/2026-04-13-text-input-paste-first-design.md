# Text Input Paste-First Design

> Date: 2026-04-13
> Status: Approved

## Goal

Make `input_text()` and `type_text()` reliable when the host Mac has non-English input sources enabled, while still supporting explicit real-key input for callers that need key-event semantics.

## Problem Summary

The current text input path uses simulated key injection:

- `input_text()` sends `macos: keys` with `list(text)`
- `type_text()` tries `send_keys(text)` and falls back to `macos: keys`

That path is fragile when the active macOS input source is an IME such as Chinese Pinyin, Japanese, or Korean. The OS may route the synthetic keystrokes through composition, candidate selection, or input-source-specific transforms instead of inserting the final intended text. The practical result is garbled text, dropped characters, or reordered input.

## Product Decision

The product semantics for `input_text()` and `type_text()` should be:

- stable insertion of the final text value
- not faithful emulation of a user typing one key at a time

Based on that decision, the default strategy changes from key injection to paste-first text insertion.

## Approaches Considered

### 1. Paste-first with explicit `keys` fallback

Use clipboard write + `command+v` as the default path, while keeping an explicit `keys` mode for flows that require key-event semantics.

Pros:

- most reliable for non-English input sources
- supports Chinese, Japanese, Korean, emoji, and symbols as final text
- avoids IME composition-state bugs
- can be implemented inside the existing Appium Mac2 adapter boundary

Cons:

- some apps treat paste differently from real typing
- clipboard handling introduces state restoration work

### 2. Auto-select between paste and keys using heuristics

Choose the input strategy based on target type, text content, or runtime hints.

Pros:

- can hide complexity from callers

Cons:

- easy to misclassify
- adds complexity before the repository has enough signal to justify it

### 3. Temporarily switch input source, then keep key injection

Switch to an ASCII-capable input source before typing, then restore the original source afterward.

Pros:

- preserves real-key semantics

Cons:

- changes global user state
- still less reliable than paste-first
- not sufficient for final-text insertion in all apps
- significantly higher failure and cleanup risk

## Recommended Design

Adopt approach 1.

- Default text input mode becomes `paste`
- Keep `keys` as an explicit compatibility mode
- Allow `auto`, but implement it as equivalent to `paste` in the first version
- Do not change system input source automatically in the first version

## Interface Design

Add `--input-method paste|keys|auto` to the CLI surfaces that write text:

- `mac input text <text>`
- `mac element type <ref> <text>`

Default:

- `paste`

Semantics:

- `paste`: stable final-text insertion via clipboard + paste hotkey
- `keys`: preserve the current key-injection behavior for callers that need key events
- `auto`: first version behaves the same as `paste`; later versions may refine selection logic without changing the CLI shape

Parameter flow:

- CLI parses `input_method`
- daemon passes it through unchanged
- core passes it through unchanged
- `AppiumMac2Adapter` owns the strategy implementation

## Adapter Design

Add internal helpers in `src/fsq_mac/adapters/appium_mac2.py`:

- `_get_clipboard_text()`
- `_set_clipboard_text(text)`
- `_paste_via_hotkey()`
- `_input_text_via_paste(text)`

### `input_text(text, input_method="paste")`

- `paste` and `auto`
  - save clipboard contents
  - write target text to clipboard
  - send `command+v`
  - restore clipboard in `finally`
  - continue returning focused-element geometry best-effort
- `keys`
  - preserve the current `macos: keys` path

### `type_text(ref, text, strategy="accessibility_id", input_method="paste")`

- resolve and focus the target element
- clear the current value using the existing element-level path
- `paste` and `auto`
  - use `_input_text_via_paste(text)`
- `keys`
  - preserve the current `send_keys()` plus `macos: keys` fallback path
- keep the current response contract:
  - `expected`
  - `typed_value`
  - `verified`
  - geometry fields when available

## Error Handling

- Clipboard restoration must run in `finally`
- `paste` mode:
  - clipboard or paste failures return a structured error response using the existing adapter/core envelope
- `auto` mode:
  - may fall back to `keys` if paste setup fails, but the first version does not require broad heuristics
- clipboard restore failure:
  - command may still succeed, but the adapter should log the restore failure for operator visibility

The design intentionally avoids widening the top-level JSON response contract in the first version.

## Testing Plan

### Automated

- Adapter tests:
  - `input_text(..., input_method="paste")` uses clipboard write plus paste hotkey
  - `type_text(..., input_method="paste")` preserves verification fields
  - `auto` behaves like `paste`
  - `keys` preserves the existing path
  - clipboard is restored on both success and failure
- CLI tests:
  - parse `--input-method`
  - default is `paste`
- daemon/core tests:
  - `input_method` is passed through unchanged

### Manual Regression

- active input source set to Chinese Pinyin
- active input source set to Japanese
- verify text insertion in a native text field
- verify text insertion in a browser text field
- verify `keys` mode still works when explicitly requested
- verify clipboard content is restored after both success and failure paths

## Out of Scope

- IME candidate-window automation
- composition-state inspection
- automatic switching of system input sources
- guaranteeing identical behavior to real per-key typing in every rich editor

## Rollout Notes

This is a default behavior change. Docs should explicitly state that the default text-entry contract is now stable final-text insertion, while `keys` remains available for workflows that need real key-event semantics.
