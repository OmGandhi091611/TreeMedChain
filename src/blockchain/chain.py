"""
TreeMedChain - Blockchain (SHA-3-256, ML-DSA-65 signatures)

SHA-3-256 replaces SHA-256 for hash chaining. Grover's algorithm halves
the effective security of SHA-256 to 128 bits; SHA-3-256 retains 256-bit
preimage resistance against quantum adversaries.

Blocks optionally carry a ML-DSA-65 (Dilithium) signature over the block
hash, signed by the authority node that created the block. is_valid()
verifies both the hash chain and any present signatures.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class Block:
    index: int
    timestamp: float
    data: Any
    prev_hash: str
    signed_by: Optional[str] = None
    hash: str = field(init=False)

    # PQC signature fields — excluded from hash computation
    signature: bytes = field(default=b"", compare=False)
    signer_public_key: bytes = field(default=b"", compare=False)

    def __post_init__(self) -> None:
        self.hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = json.dumps(
            {
                "index":     self.index,
                "timestamp": self.timestamp,
                "data":      self.data,
                "prev_hash": self.prev_hash,
                "signed_by": self.signed_by,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha3_256(payload).hexdigest()


class Chain:
    def __init__(self) -> None:
        genesis = Block(index=0, timestamp=time.time(),
                        data="genesis", prev_hash="0")
        self.blocks: List[Block] = [genesis]

    def add_block(self, data: Any, signed_by: Optional[str] = None) -> Block:
        prev = self.blocks[-1]
        block = Block(
            index=len(self.blocks),
            timestamp=time.time(),
            data=data,
            prev_hash=prev.hash,
            signed_by=signed_by,
        )
        self.blocks.append(block)
        return block

    def is_valid(self) -> bool:
        from src.privacy.pqc import DilithiumSigner
        for i in range(1, len(self.blocks)):
            cur, prev = self.blocks[i], self.blocks[i - 1]
            if cur.hash != cur._compute_hash():
                return False
            if cur.prev_hash != prev.hash:
                return False
            if cur.signature:
                if not DilithiumSigner.verify(
                    cur.hash.encode(), cur.signature, cur.signer_public_key
                ):
                    return False
        return True
