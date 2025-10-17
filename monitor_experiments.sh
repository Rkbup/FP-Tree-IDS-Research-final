#!/bin/bash
set -e
if [ -d logs ]; then
  tail -n 30 -F logs/*.log
else
  echo "No logs directory found."
fi