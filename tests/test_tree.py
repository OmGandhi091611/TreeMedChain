import pytest
from src.tree import PatientTree, MedicalNode


def _populated_tree() -> PatientTree:
    t = PatientTree("p001")
    t.add_clinical_entry(
        system="Cardiovascular", organ="Heart",
        entry_type="Diagnosis", name="Hypertension",
        data={}, timestamp="2022-01-01",
    )
    t.add_clinical_entry(
        system="MentalHealth", organ="Psychiatry",
        entry_type="Diagnosis", name="Anxiety",
        data={}, timestamp="2021-06-15",
        sensitivity="high", allowed_roles=["Psychiatrist"],
    )
    return t


def test_skeleton_built():
    t = PatientTree("p000")
    system_names = {n.name for n in t.root.children.values()}
    assert "MentalHealth" in system_names
    assert "Cardiovascular" in system_names


def test_add_clinical_entry():
    t = _populated_tree()
    heart = t._organ_nodes[("Cardiovascular", "Heart")]
    assert any(n.name == "Hypertension" for n in heart.children.values())


def test_prune_empty_removes_empty_branches():
    t = _populated_tree()
    t.prune_empty()
    system_names = {n.name for n in t.root.children.values()}
    assert "Cardiovascular" in system_names
    assert "Renal" not in system_names


def test_unknown_organ_raises():
    t = PatientTree("p002")
    with pytest.raises(ValueError):
        t.add_clinical_entry("Cardiovascular", "Spleen", "Diagnosis", "X", {}, "2020-01-01")
