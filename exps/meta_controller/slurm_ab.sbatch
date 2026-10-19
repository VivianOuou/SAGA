#!/bin/bash
# Real-LLM A/B pilot (3 tasks x 2 seeds x {A, B}) on Gautschi. The work is API-bound (no GPU use), but
# account lusu can only run on GPU partitions: `ai` needs 1 GPU with 14 CPUs per job.
#
# Submit from the repository root:
#   sbatch exps/meta_controller/slurm_ab.sbatch
# Requires OPENAI_API_KEY, either exported in the submitting shell (sbatch forwards the environment) or
# set in llm_configs/.env.openai (git-ignored; `export OPENAI_API_KEY=...`, chmod 600).
# Progress: exps/meta_controller/results/grid_status.json ; summary: exps/meta_controller/results/ab_summary.md
#SBATCH -A lusu
#SBATCH -p ai
#SBATCH --gres=gpu:1
#SBATCH -c 14
#SBATCH -t 04:00:00
#SBATCH -J saga-mc-ab
#SBATCH -o /scratch/gautschi/ou57/logs/saga/ab-%j.out

set -euo pipefail
SAGA_ROOT=${SAGA_ROOT:-/scratch/gautschi/ou57/SAGA}
SAGA_ENV=${SAGA_ENV:-/scratch/gautschi/ou57/conda-envs/saga}
cd "$SAGA_ROOT"
export PATH="$SAGA_ENV/bin:$PATH"
if [ -f llm_configs/.env.openai ]; then source llm_configs/.env.openai; fi
: "${OPENAI_API_KEY:?OPENAI_API_KEY is not set (see header)}"
echo "host=$(hostname) start=$(date -Is) commit=$(git rev-parse --short HEAD)"
python exps/meta_controller/launch_ab.py --parallel "${AB_PARALLEL:-4}"
echo "end=$(date -Is)"
