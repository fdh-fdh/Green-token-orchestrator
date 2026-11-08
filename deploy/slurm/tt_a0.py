"""Run a single Blackhole matrix-projection smoke test inside a Slurm step."""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter

import yaml


def main() -> None:
    config_path, output_path = map(Path, sys.argv[1:])
    raw = config_path.read_bytes()
    config = yaml.safe_load(raw)
    size = config["matrix_size"]
    warmups = config["warmup_iterations"]
    repeats = config["measured_iterations"]
    if any(type(value) is not int or value <= 0 for value in (size, warmups, repeats)):
        raise ValueError("Matrix size and iteration counts must be positive integers")
    if size % 32:
        raise ValueError("Matrix size must be a multiple of the 32-element tile size")

    chip = os.getenv("SLURM_STEP_GPUS", "")
    if not re.fullmatch(r"[0-9]+", chip) or not Path(f"/dev/tenstorrent/{chip}").is_char_device():
        raise RuntimeError(
            f"Expected exactly one allocated Tenstorrent device, got SLURM_STEP_GPUS={chip!r}"
        )
    os.environ["TT_VISIBLE_DEVICES"] = chip

    import torch
    import ttnn

    device_ids = ttnn.get_device_ids()
    if len(device_ids) != 1:
        raise RuntimeError(f"TTNN must expose exactly one allocated device, got {device_ids}")
    started_at = datetime.now(timezone.utc)
    with ttnn.manage_device(device_id=device_ids[0]) as device:
        matrix = ttnn.full(
            (size, size), 1.0, dtype=ttnn.bfloat16, layout=ttnn.TILE_LAYOUT, device=device
        )
        for _ in range(warmups):
            ttnn.matmul(matrix, matrix)
        ttnn.synchronize_device(device)

        seconds = []
        for _ in range(repeats):
            started = perf_counter()
            result = ttnn.matmul(matrix, matrix)
            ttnn.synchronize_device(device)
            seconds.append(perf_counter() - started)

        actual = ttnn.to_torch(result)
        expected = torch.full((size, size), size, dtype=actual.dtype)
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)

    record = {
        "protocol_version": "tt-a0-matmul-1",
        "measurement_provenance": "real",
        "workload_provenance": "synthetic",
        "workload": "single_device_bfloat16_matmul",
        "slurm_job_id": os.environ["SLURM_JOB_ID"],
        "slurm_step_id": os.environ["SLURM_STEP_ID"],
        "allocated_device": chip,
        "ttnn_version": version("ttnn"),
        "config_hash": hashlib.sha256(raw).hexdigest(),
        "script_hash": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "started_at_utc": started_at.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        **config,
        "iteration_seconds": seconds,
        "median_iteration_seconds": median(seconds),
        "numerical_check": "exact_match",
    }
    with output_path.open("x", encoding="utf-8") as output:
        json.dump(record, output, indent=2, allow_nan=False)
        output.write("\n")
    print(output_path)


if __name__ == "__main__":
    main()
