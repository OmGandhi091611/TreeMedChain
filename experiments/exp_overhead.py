"""
Cryptographic & Blockchain Overhead Experiment — TreeMedChain Phase 6

Measures mean latency (ms) and std for:
  - ML-KEM-512:  keygen, encaps, decaps
  - ML-DSA-65:   keygen, sign, verify
  - AES-256-GCM: encrypt, decrypt  (1 KB payload)
  - SHA-3-256:   single hash
  - Block add:   sign_and_log() call
  - Chain valid: is_valid() at 10, 50, 100, 500 blocks

Saves results/overhead_crypto.csv and results/overhead_chain.csv.

Usage:
    python -m experiments.exp_overhead
"""
from __future__ import annotations

import csv
import os
import sys
import time
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.privacy.pqc import KyberKEM, DilithiumSigner
from src.privacy.encryption import encrypt, decrypt
from src.blockchain.chain import Chain
from src.blockchain.poa import AuthorityNode

REPS = 50
CHAIN_SIZES = [10, 50, 100, 200, 500]
CRYPTO_OUT   = "experiments/results/overhead_crypto.csv"
CHAIN_OUT    = "experiments/results/overhead_chain.csv"

SAMPLE_DATA = {"diagnosis": "Hypertension", "code": "44054006", "notes": "x" * 900}


def _timeit(fn, reps=REPS):
    """Returns list of per-call durations in ms."""
    times = []
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return times


def bench_crypto():
    rows = []

    def _add(label, fn):
        ts = _timeit(fn)
        rows.append({
            "operation": label,
            "mean_ms":   round(statistics.mean(ts), 4),
            "std_ms":    round(statistics.stdev(ts), 4),
            "min_ms":    round(min(ts), 4),
            "max_ms":    round(max(ts), 4),
            "reps":      REPS,
        })
        print(f"  {label:30s}  mean={rows[-1]['mean_ms']:7.3f} ms  std={rows[-1]['std_ms']:.4f}")

    print("--- ML-KEM-512 ---")
    pk, sk = KyberKEM.keygen()
    ct, ss = KyberKEM.encaps(pk)
    _add("ML-KEM-512 keygen",  KyberKEM.keygen)
    _add("ML-KEM-512 encaps",  lambda: KyberKEM.encaps(pk))
    _add("ML-KEM-512 decaps",  lambda: KyberKEM.decaps(sk, ct))

    print("--- ML-DSA-65 ---")
    dpk, dsk = DilithiumSigner.keygen()
    sig = DilithiumSigner.sign(b"bench", dsk)
    _add("ML-DSA-65 keygen",   DilithiumSigner.keygen)
    _add("ML-DSA-65 sign",     lambda: DilithiumSigner.sign(b"bench_block_hash_hex", dsk))
    _add("ML-DSA-65 verify",   lambda: DilithiumSigner.verify(b"bench_block_hash_hex", sig, dpk))

    print("--- AES-256-GCM ---")
    aes_key = KyberKEM.derive_aes_key(ss)
    blob = encrypt(SAMPLE_DATA, aes_key)
    _add("AES-256-GCM encrypt (1 KB)", lambda: encrypt(SAMPLE_DATA, aes_key))
    _add("AES-256-GCM decrypt (1 KB)", lambda: decrypt(blob, aes_key))

    return rows


def bench_chain():
    rows = []
    for target in CHAIN_SIZES:
        authority = AuthorityNode("HospitalA")
        chain = Chain()

        # build chain to target length
        for i in range(target):
            authority.sign_and_log(chain, {"seq": i})

        # time add_block (sign + hash, warm)
        add_times = _timeit(
            lambda: authority.sign_and_log(chain, {"bench": True}),
            reps=10,
        )

        # time is_valid()
        val_times = _timeit(chain.is_valid, reps=20)

        row = {
            "n_blocks":      len(chain.blocks),
            "add_mean_ms":   round(statistics.mean(add_times), 4),
            "add_std_ms":    round(statistics.stdev(add_times), 4),
            "valid_mean_ms": round(statistics.mean(val_times), 4),
            "valid_std_ms":  round(statistics.stdev(val_times), 4),
        }
        rows.append(row)
        print(
            f"  chain={row['n_blocks']:4d}  "
            f"add={row['add_mean_ms']:.3f}ms  "
            f"validate={row['valid_mean_ms']:.3f}ms"
        )
    return rows


def main():
    os.makedirs("experiments/results", exist_ok=True)

    print("=== Crypto overhead ===")
    crypto_rows = bench_crypto()

    fields_c = ["operation", "mean_ms", "std_ms", "min_ms", "max_ms", "reps"]
    with open(CRYPTO_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields_c)
        w.writeheader()
        w.writerows(crypto_rows)
    print(f"\nSaved -> {CRYPTO_OUT}")

    print("\n=== Blockchain overhead ===")
    chain_rows = bench_chain()

    fields_b = ["n_blocks", "add_mean_ms", "add_std_ms", "valid_mean_ms", "valid_std_ms"]
    with open(CHAIN_OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields_b)
        w.writeheader()
        w.writerows(chain_rows)
    print(f"\nSaved -> {CHAIN_OUT}")


if __name__ == "__main__":
    main()
