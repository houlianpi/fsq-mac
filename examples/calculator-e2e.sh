#!/usr/bin/env bash
set -euo pipefail

mac doctor
mac session start
mac app launch com.apple.calculator
mac element inspect --pretty
mac element click --role AXButton --name 5
mac element click --role AXButton --name +
mac element click --role AXButton --name 3
mac input key Return
mac session end
