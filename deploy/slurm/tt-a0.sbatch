#!/bin/bash
#SBATCH --job-name=greenpulse-tt-a0
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --no-requeue

set -eo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit this script from the GreenPulse workspace}"
umask 077

module load Stages/2025 GCCcore/.13.3.0 Python/3.12.3 PyTorch/2.5.1
export TT_METAL_ARCH_NAME=blackhole PYTHONNOUSERSITE=1
unset TT_METAL_HOME
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

mkdir -p results/slurm
run_dir=$(mktemp -d "results/slurm/tt-a0-${SLURM_JOB_ID:?Missing Slurm job ID}-XXXXXX")
export XDG_CACHE_HOME="$PWD/$run_dir/cache"
export TT_METAL_CACHE="$XDG_CACHE_HOME/tt-metal"
export TTNN_CONFIG_OVERRIDES="{\"cache_path\":\"$XDG_CACHE_HOME/ttnn\",\"model_cache_path\":\"$XDG_CACHE_HOME/models\",\"tmp_dir\":\"$XDG_CACHE_HOME/tmp\"}"
printf 'Run directory: %s\n' "$run_dir"
srun --ntasks=1 --cpus-per-task=1 --gres=gpu:1 \
    .venv-tt-a0/bin/python deploy/slurm/tt_a0.py deploy/slurm/tt-a0.yaml "$run_dir/profile.json"
