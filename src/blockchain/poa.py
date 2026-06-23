"""
TreeMedChain - Proof of Authority with ML-DSA-65 Signatures

Each registered authority node (hospital/clinic) holds a Dilithium
key pair generated at startup. Every block it signs carries:
  - signed_by: the authority's name
  - signature: ML-DSA-65 signature over the block hash
  - signer_public_key: authority's Dilithium public key

Anyone with the public key can verify the signature, ensuring that
block authorship is cryptographically unforgeable even against a
quantum adversary running Shor's algorithm.
"""

from __future__ import annotations

from src.blockchain.chain import Block, Chain
from src.privacy.pqc import DilithiumSigner

_AUTHORITY_NODES = {"HospitalA", "HospitalB", "ClinicC"}


class AuthorityNode:
    def __init__(self, name: str):
        if name not in _AUTHORITY_NODES:
            raise ValueError(f"{name} is not a registered authority node")
        self.name = name
        self._public_key, self._secret_key = DilithiumSigner.keygen()

    def sign_and_log(self, chain: Chain, event: dict) -> Block:
        block = chain.add_block(data=event, signed_by=self.name)
        block.signature = DilithiumSigner.sign(block.hash.encode(), self._secret_key)
        block.signer_public_key = self._public_key
        return block

    @property
    def public_key(self) -> bytes:
        return self._public_key


def log_access_event(
    chain: Chain,
    patient_id: str,
    role: str,
    system_accessed: str,
    authority: str,
) -> None:
    node = AuthorityNode(authority)
    node.sign_and_log(
        chain,
        {
            "patient_id": patient_id,
            "role": role,
            "system_accessed": system_accessed,
        },
    )
