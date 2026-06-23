# TreeMedChain

**A Blockchain-Backed Hierarchical EHR Model with Intelligent Graph Traversal**

Research prototype — Illinois Institute of Technology
Author: Om Amit Gandhi (ogandhi1@hawk.illinoistech.edu)

---

## Overview

TreeMedChain is a privacy-preserving Electronic Health Record (EHR) system that organizes patient data as an anatomical tree and protects it using three layered mechanisms:

1. **Structural normalization** — every patient's tree has the same fixed shape, so an adversary who observes only the tree structure cannot infer which medical conditions a patient has (the _shape inference attack_).
2. **Post-quantum cryptography** — off-chain patient data is encrypted with AES-256-GCM, keys are wrapped with ML-KEM-512 (CRYSTALS-Kyber, NIST FIPS 203), and every blockchain block is signed with ML-DSA-65 (CRYSTALS-Dilithium, NIST FIPS 204).
3. **Immutable blockchain access log** — every access event is recorded in a SHA-3-256 hash-chained ledger signed by a registered authority node (Proof of Authority consensus).

Clinical data used in experiments is generated with [Synthea](https://synthea.mitre.org/) (573 synthetic patients).

---

## The Shape Inference Attack (Core Novelty)

A naive EHR system prunes empty branches before returning a tree. An adversary — such as an insurer — who is denied access to sensitive systems (MentalHealth, Reproductive) can still observe *whether those branches exist* in the returned tree and infer the patient's condition without decrypting a single byte.

**TreeMedChain's defense:** every patient's tree is always returned with the same fixed skeleton. Unauthorized branches are replaced with a fixed number of placeholder nodes (`FIXED_PLACEHOLDER_CHILDREN = 2`) so all trees look structurally identical to a blocked role.

| System | Role | Naive Accuracy | TreeMedChain Accuracy |
|--------|------|---------------|----------------------|
| MentalHealth | Insurer | ~1.0 | ~0.13 (near chance) |
| Reproductive | Insurer | ~1.0 | ~0.50 (near chance) |

The adversary's accuracy collapses from near-perfect to chance level.

---

## Architecture

```
PatientID (root)
├── Demographics
├── Gender
├── Cardiovascular  →  Heart, BloodVessels
├── Respiratory     →  Lungs, Trachea
├── Neurological    →  Brain, SpinalCord
├── Digestive       →  Stomach, Intestines, Liver
├── Musculoskeletal →  Bones, Joints
├── Reproductive    →  ReproductiveOrgans
├── MentalHealth    →  Psychiatry
└── Unclassified    →  General
```

Each organ holds clinical entry nodes (Diagnosis, Medications, Procedures, Imaging, LabTests) keyed by UUID so duplicate-named entries never collide.

### Data Flow

```
Synthea CSV
    │
    ▼
PatientTree (src/tree.py)
    │
    ├── add_clinical_entry()
    │       └── OffChainStore.store()  ←─ encrypt(AES-256-GCM)
    │               └── key wrapped by ML-KEM-512 (Kyber)
    │
    ▼
access_patient_record(role)
    │
    ├── build_virtual_tree()           ←─ structural normalization
    │       ├── authorized branch  →  real entries (decrypted on retrieval)
    │       └── blocked branch     →  2 placeholder nodes (shape preserved)
    │
    └── log_tree_access()             ←─ blockchain event
            └── AuthorityNode.sign_and_log()
                    ├── SHA-3-256 hash chain
                    └── ML-DSA-65 (Dilithium) signature
```

---

## Project Structure

```
treemedchain/
├── src/
│   ├── tree.py                    # PatientTree, MedicalNode, BODY_SYSTEMS
│   ├── synthea_loader.py          # Loads Synthea CSV → PatientTree dict
│   ├── code_mapping.py            # Maps SNOMED/Synthea descriptions to systems
│   ├── attack/
│   │   ├── adversary.py           # ShapeAdversary: predicts sensitive system presence
│   │   └── experiment.py          # Naive vs. TreeMedChain accuracy comparison
│   ├── blockchain/
│   │   ├── chain.py               # Block + Chain (SHA-3-256, ML-DSA-65)
│   │   ├── poa.py                 # Proof of Authority — AuthorityNode
│   │   └── access_log.py          # log_tree_access(), access_patient_record()
│   └── privacy/
│       ├── access_control.py      # Role-based access control + system blocklist
│       ├── virtual_tree.py        # Structural normalization with placeholders
│       ├── encryption.py          # AES-256-GCM encrypt/decrypt
│       ├── offchain_store.py      # Kyber-wrapped off-chain encrypted store
│       └── pqc.py                 # KyberKEM (ML-KEM-512), DilithiumSigner (ML-DSA-65)
│
├── experiments/
│   ├── run_all.py                 # Master runner: all experiments + plots
│   ├── exp_privacy.py             # Privacy accuracy sweep
│   ├── exp_overhead.py            # Crypto + blockchain overhead benchmarks
│   ├── exp_scalability.py         # End-to-end access time vs patient count
│   └── plot_all.py                # Generates all 4 paper figures
│
├── tests/
│   ├── test_tree.py               # PatientTree unit tests
│   ├── test_virtual_tree.py       # Structural normalization tests
│   ├── test_attack.py             # Shape adversary accuracy tests
│   ├── test_blockchain.py         # Chain integrity + access log tests
│   ├── test_encryption.py         # AES-256-GCM + OffChainStore tests
│   ├── test_pqc.py                # ML-KEM-512 + ML-DSA-65 + end-to-end PQC tests
│   └── test_synthea_loader.py     # Synthea CSV loader tests
│
├── data/
│   ├── synthea.jar                # Synthea patient generator
│   └── synthea_raw/csv/           # Generated Synthea CSVs (573 patients)
│
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+
- Java (for Synthea data generation — one-time only)
- [liboqs](https://github.com/open-quantum-safe/liboqs) C library (installed automatically via pip)

### Install system dependencies (macOS)

```bash
brew install cmake ninja
```

### Install system dependencies (Ubuntu/Debian)

```bash
sudo apt-get install cmake ninja-build libssl-dev
```

---

## Installation

```bash
git clone <repo-url>
cd treemedchain

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate       # macOS / Linux
# venv\Scripts\activate        # Windows

# Install Python dependencies (liboqs compiles from source automatically)
pip install -r requirements.txt
```

---

## Generate Synthetic Patient Data (one-time)

```bash
mkdir -p data/synthea_raw
java -jar data/synthea.jar \
  -p 573 \
  --exporter.csv.export=true \
  --exporter.fhir.export=false \
  -o data/synthea_raw
```

This produces `data/synthea_raw/csv/` containing `patients.csv`, `conditions.csv`, `medications.csv`, `procedures.csv`, and `observations.csv`.

---

## Running Tests

```bash
# Full test suite (46 tests)
venv/bin/python -m pytest --tb=short -q

# Individual test files
venv/bin/python -m pytest tests/test_tree.py -v
venv/bin/python -m pytest tests/test_virtual_tree.py -v
venv/bin/python -m pytest tests/test_attack.py -v
venv/bin/python -m pytest tests/test_blockchain.py -v
venv/bin/python -m pytest tests/test_encryption.py -v
venv/bin/python -m pytest tests/test_pqc.py -v
venv/bin/python -m pytest tests/test_synthea_loader.py -v
```

Expected: **46 passed** in approximately 1–2 minutes. The PQC tests (Kyber/Dilithium operations) and Synthea loader test dominate runtime.

---

## Running Experiments

### All experiments + plots (recommended)

```bash
venv/bin/python -m experiments.run_all --synthea-dir data/synthea_raw/csv
```

Estimated runtime: **15–25 minutes** (Kyber/Dilithium benchmarks are the bottleneck).

### Individual experiments

```bash
# 1. Privacy accuracy: adversary accuracy across roles, systems, patient counts
venv/bin/python -m experiments.exp_privacy --synthea-dir data/synthea_raw/csv

# 2. Crypto + blockchain overhead benchmarks
venv/bin/python -m experiments.exp_overhead

# 3. Scalability: end-to-end access time vs patient count
venv/bin/python -m experiments.exp_scalability --synthea-dir data/synthea_raw/csv

# 4. Generate all figures from existing CSVs (skip re-running experiments)
venv/bin/python -m experiments.plot_all
```

### Regenerate plots only (CSVs already exist)

```bash
venv/bin/python -m experiments.run_all --skip-experiments
```

---

## Output

All results are saved to `experiments/results/`:

| File | Contents |
|------|----------|
| `privacy_results.csv` | Naive vs. TreeMedChain adversary accuracy per scenario |
| `overhead_crypto.csv` | Mean/std latency (ms) per crypto operation |
| `overhead_chain.csv` | Block add time and chain validation time by chain length |
| `scalability_results.csv` | Per-patient and total access time with/without PQC |
| `plots/fig1_privacy_accuracy.png` | Adversary accuracy curves — main result |
| `plots/fig2_crypto_overhead.png` | PQC operation latency bar chart |
| `plots/fig3_chain_overhead.png` | Blockchain validation time vs. chain length |
| `plots/fig4_scalability.png` | End-to-end access time vs. patient count |

---

## Cryptographic Design

### Post-Quantum Key Management

```
Patient registration
  ML-KEM-512 keygen  →  (pk, sk)
  ML-KEM-512 encaps(pk)  →  (ciphertext, shared_secret)
  AES key = SHA-3-256(shared_secret)        [32 bytes, never stored]
  Persisted: (sk, ciphertext) only

Data retrieval
  ML-KEM-512 decaps(sk, ciphertext)  →  shared_secret
  AES key = SHA-3-256(shared_secret)
  AES-256-GCM decrypt(blob, aes_key)  →  plaintext data
```

A quantum adversary running Shor's algorithm cannot recover the AES key from the stored `(sk, ciphertext)` pair because ML-KEM-512 is based on Module Learning With Errors (MLWE), which has no known quantum speedup.

### Blockchain Block Signing

```
Fields hashed per block:  index, timestamp, data, prev_hash, signed_by
Hash algorithm:           SHA-3-256  (256-bit preimage security, Grover-resistant)
Signature:                ML-DSA-65 (Dilithium) over the block hash
Verification:             chain.is_valid() checks full hash chain + all signatures
```

### Access Control

| Role | MentalHealth | Reproductive | Other systems |
|------|-------------|-------------|---------------|
| `PrimaryCare`, `Admin` | Full access | Full access | Full access |
| `Insurer`, `Employer` | Placeholders only | Placeholders only | Real data |
| All other roles | Real data | Real data | Real data (high-sensitivity nodes require explicit `allowed_roles`) |

---

## Key Design Decisions

**Why Proof of Authority over PBFT?**
PoA is appropriate for a prototype with a known, trusted set of hospital/clinic authority nodes. PBFT is the recommended upgrade path for production deployments with untrusted validators.

**Why SHA-3-256 over SHA-256?**
Grover's algorithm reduces SHA-256's effective preimage security to 128 bits on a quantum computer. SHA-3-256 retains full 256-bit resistance.

**Why AES-256-GCM for off-chain data?**
AES is symmetric and unaffected by Shor's algorithm. GCM provides authenticated encryption — any tampering of the ciphertext causes decryption to raise `InvalidTag` immediately.

**Why a fixed placeholder count (2) rather than randomized?**
A fixed count is the simplest, provably correct construction. Every blocked patient tree presents exactly the same structure to the adversary. Randomizing within a bounded range adds negligible security while complicating formal analysis.

**Why off-chain storage?**
Storing encrypted blobs on-chain is expensive and defeats the purpose of a hash chain (the hash would change with every update). The blockchain stores only the content hash; retrieval queries the off-chain store using that hash as the key.

---

## Phase Map

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Core tree structure (`PatientTree`, structural normalization) | Complete |
| 2 | Synthea loader + 573 synthetic patients | Complete |
| 3 | Blockchain access log (SHA-3-256 hash chain, PoA) | Complete |
| 4 | Off-chain AES-256-GCM encryption | Complete |
| 5 | Post-quantum cryptography (ML-KEM-512, ML-DSA-65) | Complete |
| 6 | Experiments + figures | Complete |

---

## Citation

If you use this prototype in research or build on it, please cite:

```
Om Amit Gandhi, "TreeMedChain: A Blockchain-Backed Hierarchical EHR Model
with Intelligent Graph Traversal," Illinois Institute of Technology, 2024.
```

---

## License

Research prototype — Illinois Institute of Technology. All rights reserved.
