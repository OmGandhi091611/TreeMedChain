"""
TreeMedChain — Generate All Paper Figures (Phase 6)

Reads CSVs from experiments/results/ and saves PNGs to experiments/results/plots/.

Figures produced:
  fig1_privacy_accuracy.png  — Adversary accuracy: Naive vs TreeMedChain
  fig2_crypto_overhead.png   — Per-operation crypto latency (ms)
  fig3_chain_overhead.png    — Blockchain validation time vs chain length
  fig4_scalability.png       — End-to-end access time vs patient count

Usage:
    python -m experiments.plot_all
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import csv
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

RESULTS = Path("experiments/results")
PLOTS   = RESULTS / "plots"


# ─── helpers ────────────────────────────────────────────────────────────────

def read_csv(name: str) -> list[dict]:
    path = RESULTS / name
    if not path.exists():
        print(f"[WARNING] {path} not found — skipping.")
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def _f(row: dict, key: str) -> float:
    return float(row[key])


def savefig(fig, name: str) -> None:
    PLOTS.mkdir(parents=True, exist_ok=True)
    out = PLOTS / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved -> {out}")


# ─── Figure 1: Privacy accuracy ──────────────────────────────────────────────

def fig_privacy_accuracy():
    rows = read_csv("privacy_results.csv")
    if not rows:
        return

    BLOCKED_SCENARIOS = [
        ("MentalHealth",   "Insurer",  "Mental Health / Insurer"),
        ("MentalHealth",   "Employer", "Mental Health / Employer"),
        ("Reproductive",   "Insurer",  "Reproductive / Insurer"),
        ("Reproductive",   "Employer", "Reproductive / Employer"),
    ]
    CONTROL_SCENARIO = ("Cardiovascular", "Insurer", "Cardiovascular / Insurer (control)")

    # collect data
    def get_series(system, role):
        subset = [r for r in rows if r["target_system"] == system and r["adversary_role"] == role]
        subset.sort(key=lambda r: int(r["n_patients"]))
        ns    = [int(r["n_patients"])          for r in subset]
        naive = [_f(r, "naive_accuracy")       for r in subset]
        tmc   = [_f(r, "treemedchain_accuracy") for r in subset]
        return ns, naive, tmc

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), sharey=True)
    axes = axes.flatten()

    all_scenarios = BLOCKED_SCENARIOS + [CONTROL_SCENARIO]
    for ax, (system, role, title) in zip(axes, all_scenarios):
        ns, naive, tmc = get_series(system, role)
        if not ns:
            ax.set_visible(False)
            continue
        ax.plot(ns, naive, "o-",  color="#e05c5c", linewidth=2, label="Naive", markersize=5)
        ax.plot(ns, tmc,   "s--", color="#3a7fc1", linewidth=2, label="TreeMedChain", markersize=5)
        ax.axhline(0.5, color="gray", linestyle=":", linewidth=1, label="Random guess (0.5)")
        ax.set_title(title, fontsize=10, fontweight="bold")
        ax.set_xlabel("Number of Patients", fontsize=9)
        ax.set_ylabel("Adversary Accuracy", fontsize=9)
        ax.set_ylim(-0.05, 1.10)
        ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f"))
        ax.legend(fontsize=8, loc="lower left")
        ax.grid(True, alpha=0.3)

    # hide 6th panel if only 5 scenarios
    if len(all_scenarios) < len(axes):
        for ax in axes[len(all_scenarios):]:
            ax.set_visible(False)

    fig.suptitle(
        "Shape-Inference Attack: Adversary Accuracy (Naive vs. TreeMedChain)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.tight_layout()
    savefig(fig, "fig1_privacy_accuracy.png")


# ─── Figure 2: Crypto overhead ───────────────────────────────────────────────

def fig_crypto_overhead():
    rows = read_csv("overhead_crypto.csv")
    if not rows:
        return

    # group into families
    GROUPS = {
        "ML-KEM-512\n(Kyber)":    ["ML-KEM-512 keygen", "ML-KEM-512 encaps", "ML-KEM-512 decaps"],
        "ML-DSA-65\n(Dilithium)": ["ML-DSA-65 keygen",  "ML-DSA-65 sign",    "ML-DSA-65 verify"],
        "AES-256-GCM":             ["AES-256-GCM encrypt (1 KB)", "AES-256-GCM decrypt (1 KB)"],
    }

    lookup = {r["operation"]: r for r in rows}

    labels, means, stds, colors = [], [], [], []
    palette = {"ML-KEM-512\n(Kyber)": "#3a7fc1",
               "ML-DSA-65\n(Dilithium)": "#e07c3a",
               "AES-256-GCM": "#5cb85c"}

    for family, ops in GROUPS.items():
        for op in ops:
            if op not in lookup:
                continue
            short = op.replace("ML-KEM-512 ", "").replace("ML-DSA-65 ", "").replace("AES-256-GCM ", "").strip()
            labels.append(f"{short}\n({family.split(chr(10))[0]})")
            means.append(_f(lookup[op], "mean_ms"))
            stds.append( _f(lookup[op], "std_ms"))
            colors.append(palette[family])

    x = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(11, 5))
    bars = ax.bar(x, means, yerr=stds, capsize=4, color=colors, alpha=0.85,
                  error_kw={"linewidth": 1.5})

    for bar, m in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.002,
                f"{m:.3f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8.5)
    ax.set_ylabel("Latency (ms)", fontsize=10)
    ax.set_title("Post-Quantum Cryptographic Operation Latency\n(ML-KEM-512, ML-DSA-65, AES-256-GCM)",
                 fontsize=11, fontweight="bold")
    ax.grid(True, axis="y", alpha=0.3)

    # legend patches
    from matplotlib.patches import Patch
    legend_handles = [Patch(color=c, label=l.replace("\n", " ")) for l, c in palette.items()]
    ax.legend(handles=legend_handles, fontsize=9, loc="upper right")

    fig.tight_layout()
    savefig(fig, "fig2_crypto_overhead.png")


# ─── Figure 3: Blockchain overhead ───────────────────────────────────────────

def fig_chain_overhead():
    rows = read_csv("overhead_chain.csv")
    if not rows:
        return

    rows.sort(key=lambda r: int(r["n_blocks"]))
    ns           = [int(_f(r, "n_blocks"))          for r in rows]
    val_means    = [_f(r, "valid_mean_ms")           for r in rows]
    val_stds     = [_f(r, "valid_std_ms")            for r in rows]
    add_means    = [_f(r, "add_mean_ms")             for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # chain validation time
    ax1.errorbar(ns, val_means, yerr=val_stds, fmt="o-", color="#3a7fc1",
                 linewidth=2, capsize=4, markersize=5, label="Validate chain")
    # fit a line
    coeffs = np.polyfit(ns, val_means, 1)
    x_fit = np.linspace(min(ns), max(ns), 200)
    ax1.plot(x_fit, np.polyval(coeffs, x_fit), "--", color="#e05c5c",
             linewidth=1.5, alpha=0.7,
             label=f"Linear fit ({coeffs[0]:.4f}·n + {coeffs[1]:.2f})")
    ax1.set_xlabel("Chain Length (blocks)", fontsize=10)
    ax1.set_ylabel("Validation Time (ms)", fontsize=10)
    ax1.set_title("SHA-3-256 + Dilithium Chain Validation\nvs. Chain Length",
                  fontsize=10, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # block add time (shows Dilithium sign cost is ~constant)
    ax2.bar(ns, add_means, color="#e07c3a", alpha=0.8,
            width=[ns[i] * 0.08 if i < len(ns) - 1 else (ns[-1] - ns[-2]) * 0.8 for i in range(len(ns))])
    ax2.axhline(np.mean(add_means), color="#3a7fc1", linestyle="--", linewidth=1.5,
                label=f"Mean = {np.mean(add_means):.3f} ms")
    ax2.set_xlabel("Chain Length at Measurement (blocks)", fontsize=10)
    ax2.set_ylabel("Block Add Time (ms)", fontsize=10)
    ax2.set_title("Block Addition Overhead\n(sign_and_log, SHA-3-256 + ML-DSA-65)",
                  fontsize=10, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.grid(True, axis="y", alpha=0.3)

    fig.suptitle("Blockchain Overhead — TreeMedChain (PoA + SHA-3-256 + ML-DSA-65)",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    savefig(fig, "fig3_chain_overhead.png")


# ─── Figure 4: Scalability ───────────────────────────────────────────────────

def fig_scalability():
    rows = read_csv("scalability_results.csv")
    if not rows:
        return

    rows.sort(key=lambda r: int(r["n_patients"]))
    ns          = [int(r["n_patients"])                  for r in rows]
    no_pqc_tot  = [_f(r, "no_pqc_total_mean_ms")        for r in rows]
    no_pqc_std  = [_f(r, "no_pqc_total_std_ms")         for r in rows]
    pqc_tot     = [_f(r, "pqc_total_mean_ms")           for r in rows]
    pqc_std     = [_f(r, "pqc_total_std_ms")            for r in rows]
    no_pqc_per  = [_f(r, "no_pqc_per_patient_ms")       for r in rows]
    pqc_per     = [_f(r, "pqc_per_patient_ms")          for r in rows]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # total access time
    ax1.errorbar(ns, no_pqc_tot, yerr=no_pqc_std, fmt="o-",  color="#5cb85c",
                 linewidth=2, capsize=4, markersize=5, label="Without PQC encryption")
    ax1.errorbar(ns, pqc_tot,    yerr=pqc_std,    fmt="s--", color="#3a7fc1",
                 linewidth=2, capsize=4, markersize=5, label="With PQC (Kyber + AES + Dilithium)")

    # linear fits
    for ys, color in [(no_pqc_tot, "#5cb85c"), (pqc_tot, "#3a7fc1")]:
        coeffs = np.polyfit(ns, ys, 1)
        x_fit = np.linspace(min(ns), max(ns), 200)
        ax1.plot(x_fit, np.polyval(coeffs, x_fit), ":", color=color, alpha=0.5, linewidth=1.5)

    ax1.set_xlabel("Number of Patients", fontsize=10)
    ax1.set_ylabel("Total Access Time (ms)", fontsize=10)
    ax1.set_title("End-to-End Access Pipeline: Total Time\nvs. Patient Count",
                  fontsize=10, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)

    # per-patient time (should be flat — shows O(1) per patient)
    ax2.plot(ns, no_pqc_per, "o-",  color="#5cb85c", linewidth=2, markersize=5,
             label="Without PQC encryption")
    ax2.plot(ns, pqc_per,    "s--", color="#3a7fc1", linewidth=2, markersize=5,
             label="With PQC (Kyber + AES + Dilithium)")
    ax2.axhline(np.mean(no_pqc_per), color="#5cb85c", linestyle=":", alpha=0.5)
    ax2.axhline(np.mean(pqc_per),    color="#3a7fc1", linestyle=":", alpha=0.5)
    ax2.set_xlabel("Number of Patients", fontsize=10)
    ax2.set_ylabel("Per-Patient Access Time (ms)", fontsize=10)
    ax2.set_title("Per-Patient Access Overhead\n(Amortized Cost Stability)",
                  fontsize=10, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)

    fig.suptitle("TreeMedChain Scalability — Access Pipeline Performance",
                 fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    savefig(fig, "fig4_scalability.png")


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    print("=== TreeMedChain — Generating Figures ===\n")
    fig_privacy_accuracy()
    fig_crypto_overhead()
    fig_chain_overhead()
    fig_scalability()
    print(f"\nAll figures saved to {PLOTS}/")


if __name__ == "__main__":
    main()
