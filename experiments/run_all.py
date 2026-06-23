"""
TreeMedChain Phase 6 — Run All Experiments + Generate Plots

Runs in order:
  1. exp_privacy.py    -> results/privacy_results.csv
  2. exp_overhead.py   -> results/overhead_crypto.csv, overhead_chain.csv
  3. exp_scalability.py -> results/scalability_results.csv
  4. plot_all.py       -> results/plots/fig{1-4}_*.png

Usage:
    python -m experiments.run_all [--synthea-dir data/synthea_raw/csv]

Pass --skip-experiments to jump straight to plotting (if CSVs already exist).
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _header(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-dir", default="data/synthea_raw/csv")
    parser.add_argument("--skip-experiments", action="store_true",
                        help="Skip data collection, only regenerate plots")
    args = parser.parse_args()

    t_start = time.perf_counter()

    if not args.skip_experiments:

        _header("Step 1/3 — Privacy Accuracy Experiment")
        from experiments.exp_privacy import main as run_privacy
        sys.argv = ["exp_privacy", "--synthea-dir", args.synthea_dir]
        run_privacy()

        _header("Step 2/3 — Cryptographic & Blockchain Overhead")
        from experiments.exp_overhead import main as run_overhead
        sys.argv = ["exp_overhead"]
        run_overhead()

        _header("Step 3/3 — Scalability Experiment")
        from experiments.exp_scalability import main as run_scalability
        sys.argv = ["exp_scalability", "--synthea-dir", args.synthea_dir]
        run_scalability()

    _header("Plotting — Generating All Figures")
    from experiments.plot_all import main as run_plots
    run_plots()

    elapsed = time.perf_counter() - t_start
    print(f"\n{'='*60}")
    print(f"  All done in {elapsed:.1f}s")
    print(f"  Results: experiments/results/")
    print(f"  Figures: experiments/results/plots/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
