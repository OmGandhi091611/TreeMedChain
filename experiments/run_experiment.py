"""Orchestrates the Phase 4 experiment end-to-end.

Usage:
    python -m experiments.run_experiment --synthea-dir data/synthea_processed
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.synthea_loader import load_synthea_directory
from src.attack.experiment import run_experiment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-dir", default="data/synthea_processed")
    parser.add_argument("--target-system", default="MentalHealth")
    parser.add_argument("--adversary-role", default="Insurer")
    parser.add_argument("--output", default="experiments/results/experiment_results.csv")
    args = parser.parse_args()

    print(f"Loading patient trees from {args.synthea_dir} ...")
    trees = load_synthea_directory(args.synthea_dir)
    print(f"  Loaded {len(trees)} patients.")

    result = run_experiment(
        patient_trees=trees,
        target_system=args.target_system,
        adversary_role=args.adversary_role,
    )

    print(f"\n=== Results ===")
    print(f"  Patients:              {result.n_patients}")
    print(f"  Target system:         {result.target_system}")
    print(f"  Adversary role:        {result.adversary_role}")
    print(f"  Naive accuracy:        {result.naive_accuracy:.3f}")
    print(f"  TreeMedChain accuracy: {result.treemedchain_accuracy:.3f}")

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n_patients", "target_system", "adversary_role",
                    "naive_accuracy", "treemedchain_accuracy"])
        w.writerow([result.n_patients, result.target_system, result.adversary_role,
                    result.naive_accuracy, result.treemedchain_accuracy])
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
