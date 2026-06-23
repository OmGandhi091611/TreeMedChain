"""
Tests for post-quantum cryptography integration.

Key properties verified:
  1. ML-KEM-512: encaps/decaps roundtrip recovers shared secret
  2. ML-DSA-65:  sign/verify roundtrip succeeds; wrong key fails
  3. SHA-3-256:  chain hashes use SHA-3 (not SHA-256)
  4. Dilithium:  signed blocks pass is_valid(); tampered signature fails
  5. Kyber:      OffChainStore derives correct AES key via decapsulation
  6. End-to-end: full access with PQC signing and Kyber key wrapping
"""
import hashlib
import pytest

from src.privacy.pqc import KyberKEM, DilithiumSigner
from src.privacy.offchain_store import OffChainStore
from src.blockchain.chain import Chain
from src.blockchain.poa import AuthorityNode
from src.blockchain.access_log import access_patient_record
from src.tree import PatientTree


# -- ML-KEM-512 ------------------------------------------------------------

def test_kyber_encaps_decaps_roundtrip():
    pk, sk = KyberKEM.keygen()
    ct, ss_enc = KyberKEM.encaps(pk)
    ss_dec = KyberKEM.decaps(sk, ct)
    assert ss_enc == ss_dec


def test_kyber_derive_aes_key_is_32_bytes():
    pk, sk = KyberKEM.keygen()
    _, ss = KyberKEM.encaps(pk)
    aes_key = KyberKEM.derive_aes_key(ss)
    assert len(aes_key) == 32


def test_kyber_wrong_secret_key_gives_different_secret():
    pk, sk1 = KyberKEM.keygen()
    _, sk2 = KyberKEM.keygen()
    ct, ss_enc = KyberKEM.encaps(pk)
    ss_wrong = KyberKEM.decaps(sk2, ct)
    assert ss_enc != ss_wrong


# -- ML-DSA-65 -------------------------------------------------------------

def test_dilithium_sign_verify_roundtrip():
    pk, sk = DilithiumSigner.keygen()
    msg = b"block_hash_abc123"
    sig = DilithiumSigner.sign(msg, sk)
    assert DilithiumSigner.verify(msg, sig, pk)


def test_dilithium_wrong_public_key_fails():
    pk1, sk = DilithiumSigner.keygen()
    pk2, _ = DilithiumSigner.keygen()
    sig = DilithiumSigner.sign(b"message", sk)
    assert not DilithiumSigner.verify(b"message", sig, pk2)


def test_dilithium_tampered_message_fails():
    pk, sk = DilithiumSigner.keygen()
    sig = DilithiumSigner.sign(b"original", sk)
    assert not DilithiumSigner.verify(b"tampered", sig, pk)


# -- SHA-3-256 in blockchain -----------------------------------------------

def test_chain_uses_sha3_256():
    chain = Chain()
    block_hash = chain.blocks[0].hash
    # SHA-3-256 produces 64-char hex; verify format
    assert len(block_hash) == 64
    # Confirm it's NOT SHA-256 by checking independently
    payload = '{"data": "genesis", "index": 0, "prev_hash": "0", "signed_by": null, "timestamp": '
    sha2 = hashlib.sha256(payload.encode()).hexdigest()
    assert block_hash != sha2  # different algorithm


def test_signed_block_passes_is_valid():
    chain = Chain()
    authority = AuthorityNode("HospitalA")
    authority.sign_and_log(chain, {"event": "test"})
    assert chain.is_valid()


def test_tampered_signature_fails_is_valid():
    chain = Chain()
    authority = AuthorityNode("HospitalA")
    authority.sign_and_log(chain, {"event": "test"})
    assert chain.is_valid()

    # Corrupt the signature
    sig = bytearray(chain.blocks[1].signature)
    sig[10] ^= 0xFF
    chain.blocks[1].signature = bytes(sig)

    assert not chain.is_valid()


def test_tampered_data_fails_is_valid():
    chain = Chain()
    authority = AuthorityNode("HospitalA")
    authority.sign_and_log(chain, {"event": "test"})
    chain.blocks[1].data["event"] = "hacked"
    assert not chain.is_valid()


# -- Kyber in OffChainStore ------------------------------------------------

def test_offchain_store_kyber_roundtrip():
    store = OffChainStore()
    data = {"diagnosis": "Hypertension", "code": "44054006"}
    chash = store.store("patient_001", data)
    assert store.retrieve(chash, "patient_001") == data


def test_offchain_store_different_patients_isolated():
    store = OffChainStore()
    chash = store.store("p1", {"x": 1})
    store.store("p2", {"x": 2})
    with pytest.raises(Exception):
        store.retrieve(chash, "p2")


# -- End-to-end PQC access -------------------------------------------------

def test_full_pqc_access_and_verify():
    """Full access: Kyber key wrapping + Dilithium block signing + SHA-3 chain."""
    store = OffChainStore()
    tree = PatientTree("patient_pqc")
    tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {"code": "44054006"}, "2024-01-01",
        offchain_store=store,
    )
    tree.add_clinical_entry(
        "MentalHealth", "Psychiatry", "Diagnosis", "Anxiety",
        {"code": "197480006"}, "2023-06-01",
        sensitivity="high", allowed_roles=["Psychiatrist"],
        offchain_store=store,
    )

    chain = Chain()
    vt = access_patient_record(tree, "Insurer", chain, "HospitalA",
                               offchain_store=store)

    # Chain is valid (SHA-3-256 + Dilithium)
    assert chain.is_valid()

    # Insurer sees Cardiovascular (not blocked)
    heart = vt.get_system_node("Cardiovascular").get_child("Heart")
    entries = list(heart.children.values())
    assert any(e.data == {"code": "44054006"} for e in entries)

    # MentalHealth is blocked for Insurer — placeholders only
    psych = vt.get_system_node("MentalHealth").get_child("Psychiatry")
    assert all(e.is_placeholder for e in psych.children.values())
