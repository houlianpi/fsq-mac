#!/usr/bin/env bash
set -euo pipefail

TRACE_DIR="artifacts/traces/agent-demo"

mac session start
mac trace start "$TRACE_DIR"
mac app launch com.apple.calculator
mac element click --role AXButton --name 7
mac element click --role AXButton --name +
mac element click --role AXButton --name 8
mac input key Return
mac trace stop
mac trace replay "$TRACE_DIR"
mac trace codegen "$TRACE_DIR" --output "$TRACE_DIR/generated.sh"
mac session end
