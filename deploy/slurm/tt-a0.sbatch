#!/bin/bash
#SBATCH --job-name=greenpulse-tt-a0
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#SBATCH --mem=4G
#SBATCH --time=00:03:00
#SBATCH --no-requeue
#SBATCH --export=NIL

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?Submit this script from the GreenPulse workspace}"
umask 077
ulimit -c 0

export PATH=/usr/bin:/bin
# TTNN's native initializer expects the account's home directory.
if [[ -z "${HOME:-}" ]]; then
    account_home=$(getent passwd "$(id -u)" | cut -d: -f6)
    [[ -d "$account_home" ]] || { echo 'Account home directory unavailable' >&2; exit 1; }
    export HOME="$account_home"
fi
runtime="$PWD/private/tt-a0-runtime"
python="$runtime/venv/bin/python"
if [[ ! -x "$python" ]]; then
    printf 'GreenPulse TT runtime unavailable in %s\n' "$runtime" >&2
    exit 1
fi

if gcc_libs=$(set +u
    for init in /p/software/default/lmod/8.7.64/init/bash /usr/share/lmod/lmod/init/bash; do
        [[ -r "$init" ]] || continue
        if source "$init" >&2 && [[ -x "${LMOD_CMD:-}" ]] \
            && module use /p/software/default/productionstages >&2 \
            && module load Stages/2026 GCCcore/.14.3.0 GMP/6.3.0 MPFR/4.2.2 MPC/1.3.1 >&2 \
            && [[ -n "${LD_LIBRARY_PATH:-}" ]]; then
            module list >&2
            printf '%s\n' "$LD_LIBRARY_PATH"
            exit 0
        fi
    done
    exit 1
); then
    echo 'Runtime libraries: JSC GCCcore, GMP, MPFR and MPC modules'
else
    gcc_libs="$runtime/lib"
    echo 'JSC Lmod unavailable; using GreenPulse private GCC runtime libraries' >&2
    for library in libatomic.so.1 libgmp.so.10 libmpfr.so.6 libmpc.so.3; do
        if [[ ! -r "$gcc_libs/$library" ]]; then
            printf 'Required %s unavailable in %s\n' "$library" "$gcc_libs" >&2
            exit 1
        fi
    done
fi
export LD_LIBRARY_PATH="$gcc_libs"
sfpi="$runtime/venv/lib/python3.12/site-packages/ttnn/runtime/sfpi/compiler/bin/riscv-tt-elf-g++"
if [[ ! -x "$sfpi" ]]; then
    printf 'TTNN kernel compiler unavailable in %s\n' "$runtime" >&2
    exit 1
fi
"$sfpi" --version | sed -n '1p'
printf 'int probe() { return 0; }\n' | "$sfpi" -mcpu=tt-bh -x c++ -c - -o /dev/null
export TT_METAL_ARCH_NAME=blackhole PYTHONNOUSERSITE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

mkdir -p results/slurm
run_dir=$(mktemp -d "results/slurm/tt-a0-${SLURM_JOB_ID:?Missing Slurm job ID}-XXXXXX")
export XDG_CACHE_HOME="$PWD/$run_dir/cache"
export TT_METAL_CACHE="$XDG_CACHE_HOME/tt-metal"
export TTNN_CONFIG_OVERRIDES="{\"cache_path\":\"$XDG_CACHE_HOME/ttnn\",\"model_cache_path\":\"$XDG_CACHE_HOME/models\",\"tmp_dir\":\"$XDG_CACHE_HOME/tmp\"}"
printf 'Run directory: %s\n' "$run_dir"
# This single process runs inside Slurm's existing batch allocation.
exec "$python" -I -X faulthandler deploy/slurm/tt_a0.py deploy/slurm/tt-a0.yaml "$run_dir/profile.json"
