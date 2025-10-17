#!/bin/bash
set -e
mkdir -p results-final/tables results-final/figures
cp results/tables/* results-final/tables/ 2>/dev/null || true
cp results/figures/* results-final/figures/ 2>/dev/null || true
echo "Results copied to results-final."