"""
TreeMedChain - AES-256-GCM Off-Chain Encryption

Clinical content is encrypted before leaving the in-memory tree for
storage. Only the SHA-256 hash of the ciphertext is stored on-chain,
binding the blockchain record to the encrypted content without exposing it.

Write path:
    encrypt(data, key) -> blob          store blob off-chain
    content_hash(blob) -> hash          store hash on-chain

Read path (authorized only):
    blob = offchain_store.retrieve(hash)
    data = decrypt(blob, key)           plaintext back to authorized accessor

AES-256-GCM provides both confidentiality and integrity — a tampered
ciphertext raises InvalidTag on decrypt, so corruption is always detected.
"""

from __future__ import annotations

import hashlib
import json
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_patient_key() -> bytes:
    """Generate a fresh AES-256 key for a patient."""
    return os.urandom(32)


def encrypt(data: dict, key: bytes) -> bytes:
    """
    Encrypt a data dict with AES-256-GCM.
    Returns a blob: 12-byte nonce || ciphertext+tag.
    """
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    plaintext = json.dumps(data, sort_keys=True).encode()
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def decrypt(blob: bytes, key: bytes) -> dict:
    """
    Decrypt a blob produced by encrypt().
    Raises cryptography.exceptions.InvalidTag if tampered.
    """
    nonce, ciphertext = blob[:12], blob[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())


def content_hash(blob: bytes) -> str:
    """SHA-256 of the ciphertext blob — stored on-chain as integrity proof."""
    return hashlib.sha256(blob).hexdigest()
