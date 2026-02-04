#!/bin/bash
# run_monte_carlo.sh — 1000 reproducible episodes → Optuna input

set -euo pipefail

SEED=42
POLICY=optuna
EPISODES=1000

for i in $(seq 1 $EPISODES); do
  echo "Running episode $i/$EPISODES (seed=$((SEED+i)))" >&2
  love . --headless --policy "$POLICY" --seed $((SEED+i)) \
    | tee -a "episodes_$i.ndjson"
done

# Aggregate for Optuna
cat episodes_*.ndjson | jq -s 'map(select(.reward)) | map(.reward) | mean' \
  > optuna_objective.json
