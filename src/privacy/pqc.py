"""
TreeMedChain - Post-Quantum Cryptography Primitives

NIST-standardized algorithms (2024):
  ML-KEM-512   (FIPS 203) — CRYSTALS-Kyber key encapsulation
  ML-DSA-65    (FIPS 204) — CRYSTALS-Dilithium digital signatures

Why these matter for EHR:
  Health records must be protected for 50+ years. Quantum computers
  running Shor's algorithm can break RSA and ECC within that timeframe.
  "Harvest now, decrypt later" attacks make this a present-day concern,
  not a future one. ML-KEM and ML-DSA are immune to Shor's algorithm.

Role in TreeMedChain:
  ML-KEM-512  → wraps the per-patient AES-256 key in off-chain storage
  ML-DSA-65   → signs each blockchain block so authority is unforgeable
  SHA-3-256   → replaces SHA-256 in hash chaining (Grover-resistant)
"""

from __future__ import annotations

import hashlib
import oqs

KEM_ALG = "ML-KEM-512"   # NIST FIPS 203
SIG_ALG = "ML-DSA-65"    # NIST FIPS 204


class KyberKEM:
    """ML-KEM-512 key encapsulation for quantum-safe AES key wrapping."""

    @staticmethod
    def keygen() -> tuple[bytes, bytes]:
        """Generate a Kyber key pair. Returns (public_key, secret_key)."""
        with oqs.KeyEncapsulation(KEM_ALG) as kem:
            public_key = kem.generate_keypair()
            secret_key = kem.export_secret_key()
        return public_key, secret_key

    @staticmethod
    def encaps(public_key: bytes) -> tuple[bytes, bytes]:
        """Encapsulate: returns (ciphertext, shared_secret)."""
        with oqs.KeyEncapsulation(KEM_ALG) as kem:
            ciphertext, shared_secret = kem.encap_secret(public_key)
        return ciphertext, shared_secret

    @staticmethod
    def decaps(secret_key: bytes, ciphertext: bytes) -> bytes:
        """Decapsulate: returns shared_secret."""
        with oqs.KeyEncapsulation(KEM_ALG, secret_key) as kem:
            return kem.decap_secret(ciphertext)

    @staticmethod
    def derive_aes_key(shared_secret: bytes) -> bytes:
        """Derive a 256-bit AES key from the Kyber shared secret via SHA-3-256."""
        return hashlib.sha3_256(shared_secret).digest()


class DilithiumSigner:
    """ML-DSA-65 digital signatures for quantum-safe block signing."""

    @staticmethod
    def keygen() -> tuple[bytes, bytes]:
        """Generate a Dilithium key pair. Returns (public_key, secret_key)."""
        with oqs.Signature(SIG_ALG) as signer:
            public_key = signer.generate_keypair()
            secret_key = signer.export_secret_key()
        return public_key, secret_key

    @staticmethod
    def sign(message: bytes, secret_key: bytes) -> bytes:
        """Sign a message. Returns signature bytes."""
        with oqs.Signature(SIG_ALG, secret_key) as signer:
            return signer.sign(message)

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a signature. Returns True if valid."""
        with oqs.Signature(SIG_ALG) as verifier:
            return verifier.verify(message, signature, public_key)
