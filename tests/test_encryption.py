"""
Tests for off-chain AES-256-GCM encryption and the OffChainStore.

Key properties verified:
  1. Encrypt → decrypt round-trip returns original data
  2. Wrong key cannot decrypt (InvalidTag raised)
  3. Tampered ciphertext is rejected (InvalidTag raised)
  4. Content hash is deterministic for the same blob
  5. OffChainStore stores and retrieves correctly
  6. add_clinical_entry with store clears plaintext and sets data_hash
  7. access_patient_record decrypts data for authorized roles
  8. Unauthorized roles still receive placeholders (no data)
"""
import pytest
from cryptography.exceptions import InvalidTag

from src.privacy.encryption import generate_patient_key, encrypt, decrypt, content_hash
from src.privacy.offchain_store import OffChainStore
from src.tree import PatientTree
from src.blockchain.chain import Chain
from src.blockchain.access_log import access_patient_record


# -- encryption primitives -------------------------------------------------

def test_encrypt_decrypt_roundtrip():
    key = generate_patient_key()
    data = {"diagnosis": "Hypertension", "code": "44054006", "severity": "moderate"}
    blob = encrypt(data, key)
    assert decrypt(blob, key) == data


def test_wrong_key_raises():
    key1 = generate_patient_key()
    key2 = generate_patient_key()
    blob = encrypt({"x": 1}, key1)
    with pytest.raises(InvalidTag):
        decrypt(blob, key2)


def test_tampered_ciphertext_raises():
    key = generate_patient_key()
    blob = bytearray(encrypt({"x": 1}, key))
    blob[20] ^= 0xFF  # flip a byte in the ciphertext
    with pytest.raises(InvalidTag):
        decrypt(bytes(blob), key)


def test_content_hash_is_deterministic():
    key = generate_patient_key()
    blob = encrypt({"a": 1}, key)
    assert content_hash(blob) == content_hash(blob)


def test_different_data_different_hash():
    key = generate_patient_key()
    h1 = content_hash(encrypt({"a": 1}, key))
    h2 = content_hash(encrypt({"a": 2}, key))
    assert h1 != h2


# -- OffChainStore ---------------------------------------------------------

def test_store_and_retrieve():
    store = OffChainStore()
    data = {"diagnosis": "Anxiety", "severity": "mild"}
    chash = store.store("patient_001", data)
    assert store.retrieve(chash, "patient_001") == data


def test_store_returns_hash():
    store = OffChainStore()
    chash = store.store("p1", {"x": 1})
    assert isinstance(chash, str) and len(chash) == 64  # SHA-256 hex


def test_different_patients_have_different_keys():
    store = OffChainStore()
    chash1 = store.store("p1", {"x": 1})
    # p2 has a different key — cannot retrieve p1's data
    store.store("p2", {"x": 1})
    with pytest.raises(Exception):
        store.retrieve(chash1, "p2")


# -- Integration with PatientTree ------------------------------------------

def test_add_entry_with_store_clears_plaintext():
    store = OffChainStore()
    tree = PatientTree("patient_001")
    entry = tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {"code": "44054006"}, "2024-01-01",
        offchain_store=store,
    )
    assert entry.data == {}           # plaintext cleared
    assert len(entry.data_hash) == 64 # hash set


def test_add_entry_without_store_keeps_plaintext():
    tree = PatientTree("patient_001")
    entry = tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {"code": "44054006"}, "2024-01-01",
    )
    assert entry.data == {"code": "44054006"}
    assert entry.data_hash == ""


def test_access_decrypts_for_authorized_role():
    store = OffChainStore()
    tree = PatientTree("patient_001")
    tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {"code": "44054006"}, "2024-01-01",
        offchain_store=store,
    )
    chain = Chain()
    vt = access_patient_record(tree, "Cardiologist", chain, "HospitalA",
                               offchain_store=store)

    heart = vt.get_system_node("Cardiovascular").get_child("Heart")
    entries = list(heart.children.values())
    assert len(entries) == 1
    assert entries[0].data == {"code": "44054006"}


def test_unauthorized_role_gets_no_data():
    store = OffChainStore()
    tree = PatientTree("patient_001")
    tree.add_clinical_entry(
        "MentalHealth", "Psychiatry", "Diagnosis", "Anxiety",
        {"code": "197480006"}, "2023-06-01",
        sensitivity="high", allowed_roles=["Psychiatrist"],
        offchain_store=store,
    )
    chain = Chain()
    vt = access_patient_record(tree, "Insurer", chain, "HospitalA",
                               offchain_store=store)

    psychiatry = vt.get_system_node("MentalHealth").get_child("Psychiatry")
    for entry in psychiatry.children.values():
        assert entry.is_placeholder
        assert entry.data_hash == ""
        assert entry.data.get("detail") == "REDACTED"


def test_content_hashes_logged_on_chain():
    store = OffChainStore()
    tree = PatientTree("patient_001")
    tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {"code": "44054006"}, "2024-01-01",
        offchain_store=store,
    )
    chain = Chain()
    access_patient_record(tree, "Cardiologist", chain, "HospitalA",
                          offchain_store=store)

    event = chain.blocks[1].data
    assert len(event["content_hashes"]) > 0
