"""
Privacy Accuracy Experiment — TreeMedChain Phase 6

Measures adversary shape-inference accuracy under two systems:
  - Naive:        pruned tree, shape leaks ground truth
  - TreeMedChain: structural normalization, placeholders hide shape

Sweeps patient count and (system, role) pairs, saves results/privacy_results.csv.

Usage:
    python -m experiments.exp_privacy [--synthea-dir data/synthea_raw/csv]
"""
from __future__ import annotations

import argparse
import csv
import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.synthea_loader import load_synthea_directory
from src.attack.experiment import run_experiment

PATIENT_COUNTS = [100, 200, 300, 400, 500, 573]

SCENARIOS = [
    ("MentalHealth",   "Insurer"),
    ("MentalHealth",   "Employer"),
    ("Reproductive",   "Insurer"),
    ("Reproductive",   "Employer"),
    ("Cardiovascular", "Insurer"),   # control: not blocked, accuracy should stay high
]

OUTPUT = "experiments/results/privacy_results.csv"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-dir", default="data/synthea_raw/csv")
    parser.add_argument("--output", default=OUTPUT)
    args = parser.parse_args()

    print(f"Loading patients from {args.synthea_dir} ...")
    all_trees = load_synthea_directory(args.synthea_dir)
    total = len(all_trees)
    print(f"  Loaded {total} patients.\n")

    all_pids = list(all_trees.keys())
    rows = []

    for (system, role), n in itertools.product(SCENARIOS, PATIENT_COUNTS):
        n = min(n, total)
        subset = {pid: all_trees[pid] for pid in all_pids[:n]}
        result = run_experiment(subset, target_system=system, adversary_role=role)
        row = {
            "n_patients":            result.n_patients,
            "target_system":         result.target_system,
            "adversary_role":        result.adversary_role,
            "naive_accuracy":        round(result.naive_accuracy, 4),
            "treemedchain_accuracy": round(result.treemedchain_accuracy, 4),
        }
        rows.append(row)
        print(
            f"  n={n:4d}  {system:14s} / {role:8s}  "
            f"naive={result.naive_accuracy:.3f}  tmc={result.treemedchain_accuracy:.3f}"
        )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fieldnames = ["n_patients", "target_system", "adversary_role",
                  "naive_accuracy", "treemedchain_accuracy"]
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()
