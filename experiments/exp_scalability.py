"""
Scalability Experiment — TreeMedChain Phase 6

Measures end-to-end access pipeline time (build_virtual_tree + blockchain log)
as a function of patient count. Two variants:
  - without PQC offchain encryption (tree traversal + chain only)
  - with PQC offchain encryption (Kyber key wrap + AES + Dilithium sign)

Saves results/scalability_results.csv.

Usage:
    python -m experiments.exp_scalability [--synthea-dir data/synthea_raw/csv]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import statistics
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.synthea_loader import load_synthea_directory
from src.privacy.virtual_tree import build_virtual_tree
from src.blockchain.chain import Chain
from src.blockchain.access_log import access_patient_record, log_tree_access
from src.blockchain.poa import AuthorityNode
from src.privacy.offchain_store import OffChainStore

PATIENT_COUNTS = [10, 50, 100, 200, 300, 400, 500, 573]
ROLE = "PrimaryCare"
AUTHORITY = "HospitalA"
OUTPUT = "experiments/results/scalability_results.csv"


def _prep_store(trees: dict) -> OffChainStore:
    """Pre-register all patients in the store (one-time setup, not timed)."""
    store = OffChainStore()
    for pid in trees:
        store.register_patient(pid)
    return store


def _time_access_no_pqc(trees: dict, reps: int = 3) -> dict:
    """Virtual tree + blockchain only (no encryption)."""
    times = []
    for _ in range(reps):
        chain = Chain()
        authority = AuthorityNode(AUTHORITY)
        t0 = time.perf_counter()
        for tree in trees.values():
            vt = build_virtual_tree(tree, ROLE)
            log_tree_access(chain, tree, vt, ROLE, authority)
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "total_mean_ms": round(statistics.mean(times), 2),
        "total_std_ms":  round(statistics.stdev(times) if reps > 1 else 0.0, 2),
        "per_patient_ms": round(statistics.mean(times) / len(trees), 4),
    }


def _time_access_pqc(trees: dict, store: OffChainStore, reps: int = 3) -> dict:
    """Full pipeline: Kyber + AES + virtual tree + Dilithium + chain."""
    times = []
    for _ in range(reps):
        chain = Chain()
        t0 = time.perf_counter()
        for tree in trees.values():
            access_patient_record(tree, ROLE, chain, AUTHORITY,
                                  offchain_store=store)
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "total_mean_ms": round(statistics.mean(times), 2),
        "total_std_ms":  round(statistics.stdev(times) if reps > 1 else 0.0, 2),
        "per_patient_ms": round(statistics.mean(times) / len(trees), 4),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthea-dir", default="data/synthea_raw/csv")
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()

    print(f"Loading patients from {args.synthea_dir} ...")
    all_trees = load_synthea_directory(args.synthea_dir)
    total = len(all_trees)
    all_pids = list(all_trees.keys())
    print(f"  Loaded {total} patients.\n")

    # Pre-register all patients once (Kyber keygen, not part of per-access benchmark)
    print("Pre-registering patients in OffChainStore (Kyber keygen) ...")
    store = _prep_store(all_trees)
    print("  Done.\n")

    rows = []
    print(f"{'n':>6}  {'no_pqc_per_ms':>14}  {'pqc_per_ms':>12}")
    print("-" * 40)

    for n in PATIENT_COUNTS:
        n = min(n, total)
        subset = {pid: all_trees[pid] for pid in all_pids[:n]}

        r_no_pqc = _time_access_no_pqc(subset, reps=args.reps)
        r_pqc    = _time_access_pqc(subset, store, reps=args.reps)

        row = {
            "n_patients":              n,
            "no_pqc_total_mean_ms":    r_no_pqc["total_mean_ms"],
            "no_pqc_total_std_ms":     r_no_pqc["total_std_ms"],
            "no_pqc_per_patient_ms":   r_no_pqc["per_patient_ms"],
            "pqc_total_mean_ms":       r_pqc["total_mean_ms"],
            "pqc_total_std_ms":        r_pqc["total_std_ms"],
            "pqc_per_patient_ms":      r_pqc["per_patient_ms"],
        }
        rows.append(row)
        print(
            f"{n:6d}  {r_no_pqc['per_patient_ms']:14.4f}  {r_pqc['per_patient_ms']:12.4f}"
        )

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nSaved {len(rows)} rows -> {args.output}")


if __name__ == "__main__":
    main()
