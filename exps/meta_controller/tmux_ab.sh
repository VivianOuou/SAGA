#!/bin/bash
# Fallback when no scheduler is usable: run the A/B grid in a detached tmux session (survives SSH loss).
#   bash exps/meta_controller/tmux_ab.sh            # attach later with: tmux attach -t saga-mc-ab
set -euo pipefail
SAGA_ROOT=${SAGA_ROOT:-/scratch/gautschi/ou57/SAGA}
SAGA_ENV=${SAGA_ENV:-/scratch/gautschi/ou57/conda-envs/saga}
LOG=${LOG:-/scratch/gautschi/ou57/logs/saga/ab-tmux-$(date +%Y%m%d%H%M%S).out}
mkdir -p "$(dirname "$LOG")"
tmux new-session -d -s saga-mc-ab "cd $SAGA_ROOT && export PATH=$SAGA_ENV/bin:\$PATH && \
  { [ -f llm_configs/.env.openai ] && source llm_configs/.env.openai || true; } && \
  python exps/meta_controller/launch_ab.py --parallel \${AB_PARALLEL:-2} 2>&1 | tee $LOG"
echo "started tmux session saga-mc-ab, log: $LOG"
