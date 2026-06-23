"""
Tests for blockchain access logging and tamper detection.

Key properties verified:
  1. Every access produces an immutable block on the chain
  2. Chain remains valid after multiple accesses
  3. Tampering with any block is detected by is_valid()
  4. Raw patient IDs never appear in any block
  5. Redacted systems are correctly recorded
  6. Authorized systems are correctly recorded
"""
import json
import pytest

from src.tree import PatientTree
from src.blockchain.chain import Chain
from src.blockchain.access_log import access_patient_record, log_tree_access
from src.privacy.virtual_tree import build_virtual_tree


def _sample_tree() -> PatientTree:
    t = PatientTree("patient_001")
    t.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis", "Hypertension",
        {}, "2024-01-01",
    )
    t.add_clinical_entry(
        "MentalHealth", "Psychiatry", "Diagnosis", "Anxiety",
        {}, "2023-06-01", sensitivity="high", allowed_roles=["Psychiatrist"],
    )
    return t


def test_access_logged_to_chain():
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    assert len(chain.blocks) == 2  # genesis + 1 access block


def test_chain_valid_after_multiple_accesses():
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    access_patient_record(tree, "Cardiologist", chain, "HospitalB")
    access_patient_record(tree, "Psychiatrist", chain, "ClinicC")
    assert chain.is_valid()
    assert len(chain.blocks) == 4  # genesis + 3 accesses


def test_tamper_detection():
    """Modifying any block's data must invalidate the chain."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    assert chain.is_valid()

    chain.blocks[1].data["role"] = "Admin"  # tamper

    assert not chain.is_valid()


def test_patient_id_not_stored_raw():
    """Raw patient ID must never appear in any block on the chain."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")

    for block in chain.blocks:
        block_str = json.dumps(block.data) if isinstance(block.data, dict) else str(block.data)
        assert tree.patient_id not in block_str


def test_redacted_systems_logged_for_insurer():
    """MentalHealth must appear in redacted list for Insurer role."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    event = chain.blocks[1].data
    assert "MentalHealth" in event["systems_redacted"]


def test_real_systems_logged_for_cardiologist():
    """Cardiovascular must appear in real list for Cardiologist role."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Cardiologist", chain, "HospitalA")
    event = chain.blocks[1].data
    assert "Cardiovascular" in event["systems_real"]


def test_tree_root_hash_differs_by_role():
    """Different roles see different virtual trees — hashes must differ."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    access_patient_record(tree, "Psychiatrist", chain, "HospitalA")

    insurer_hash = chain.blocks[1].data["tree_root_hash"]
    psychiatrist_hash = chain.blocks[2].data["tree_root_hash"]
    assert insurer_hash != psychiatrist_hash


def test_block_signed_by_authority():
    """Each access block must carry the authority node that signed it."""
    tree = _sample_tree()
    chain = Chain()
    access_patient_record(tree, "Insurer", chain, "HospitalA")
    assert chain.blocks[1].signed_by == "HospitalA"
