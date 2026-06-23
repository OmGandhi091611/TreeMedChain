"""
TreeMedChain - Off-Chain Encrypted Store (ML-KEM-512 key encapsulation)

Patient AES-256 keys are never stored in plaintext. Instead:

  1. register_patient()  → Kyber keygen → (pk, sk)
                         → Kyber encaps(pk) → (ciphertext, shared_secret)
                         → AES key = SHA-3-256(shared_secret)
                         → Store (sk, ciphertext); discard raw AES key

  2. store()             → derive AES key via decaps(sk, ct)
                         → encrypt(data, aes_key) → blob
                         → store blob under content_hash

  3. retrieve()          → derive AES key via decaps(sk, ct)
                         → decrypt(blob, aes_key) → plaintext data

An adversary who steals the ciphertext (ct) cannot recover the AES key
without the secret key (sk). And even with a quantum computer, ML-KEM-512
is immune to Shor's algorithm — the key remains safe.
"""

from __future__ import annotations

from src.privacy.encryption import encrypt, decrypt, content_hash
from src.privacy.pqc import KyberKEM


class OffChainStore:

    def __init__(self):
        self._blobs: dict[str, bytes] = {}   # content_hash -> encrypted blob
        self._kyber: dict[str, dict] = {}    # patient_id  -> {sk, ct}

    # -- patient registration ----------------------------------------------

    def register_patient(self, patient_id: str) -> None:
        """
        Generate a Kyber key pair and encapsulate the AES-256 key.
        Only (sk, ct) are stored — the raw AES key and shared secret
        are never persisted.
        """
        if patient_id in self._kyber:
            return
        pk, sk = KyberKEM.keygen()
        ct, _ss = KyberKEM.encaps(pk)
        self._kyber[patient_id] = {"sk": sk, "ct": ct}

    def has_patient(self, patient_id: str) -> bool:
        return patient_id in self._kyber

    # -- AES key derivation ------------------------------------------------

    def _aes_key(self, patient_id: str) -> bytes:
        """Derive the AES-256 key via Kyber decapsulation."""
        kk = self._kyber[patient_id]
        ss = KyberKEM.decaps(kk["sk"], kk["ct"])
        return KyberKEM.derive_aes_key(ss)

    # -- write / read ------------------------------------------------------

    def store(self, patient_id: str, data: dict) -> str:
        """
        Encrypt data with the Kyber-derived AES key and store it.
        Returns content_hash — the only thing logged on-chain.
        """
        if patient_id not in self._kyber:
            self.register_patient(patient_id)
        blob = encrypt(data, self._aes_key(patient_id))
        chash = content_hash(blob)
        self._blobs[chash] = blob
        return chash

    def retrieve(self, chash: str, patient_id: str) -> dict:
        """
        Decrypt and return data. Raises KeyError if hash unknown.
        """
        blob = self._blobs[chash]
        return decrypt(blob, self._aes_key(patient_id))

    def has(self, chash: str) -> bool:
        return chash in self._blobs

    def entry_count(self) -> int:
        return len(self._blobs)

    def patient_count(self) -> int:
        return len(self._kyber)
