"""Key property: shape invariance under TreeMedChain for unauthorized roles."""
import pytest
from src.tree import PatientTree
from src.privacy.virtual_tree import build_virtual_tree, is_placeholder


def _tree_with_mental_health(pid: str) -> PatientTree:
    t = PatientTree(pid)
    t.add_clinical_entry(
        system="MentalHealth", organ="Psychiatry",
        entry_type="Diagnosis", name="Depression",
        data={}, timestamp="2022-03-10",
        sensitivity="high", allowed_roles=["Psychiatrist"],
    )
    return t


def _tree_without_mental_health(pid: str) -> PatientTree:
    t = PatientTree(pid)
    t.add_clinical_entry(
        system="Cardiovascular", organ="Heart",
        entry_type="Diagnosis", name="Hypertension",
        data={}, timestamp="2021-05-20",
    )
    return t


def _child_count_for_system(tree: PatientTree, system: str) -> int:
    for sys_node in tree.root.children.values():
        if sys_node.name == system:
            return sum(len(org.children) for org in sys_node.children.values())
    return 0


def test_shape_invariance_for_insurer():
    """An Insurer-role virtual tree must have identical MentalHealth shape
    regardless of whether the underlying patient has MentalHealth data."""
    tree_with = _tree_with_mental_health("p_with")
    tree_without = _tree_without_mental_health("p_without")

    vt_with = build_virtual_tree(tree_with, role="Insurer")
    vt_without = build_virtual_tree(tree_without, role="Insurer")

    count_with = _child_count_for_system(vt_with, "MentalHealth")
    count_without = _child_count_for_system(vt_without, "MentalHealth")
    assert count_with == count_without, (
        f"Shape differs: {count_with} vs {count_without} children in MentalHealth"
    )


def test_placeholder_nodes_present_for_unauthorized_system():
    tree = _tree_with_mental_health("p001")
    vt = build_virtual_tree(tree, role="Insurer")
    for sys_node in vt.root.children.values():
        if sys_node.name == "MentalHealth":
            for org in sys_node.children.values():
                for entry in org.children.values():
                    assert is_placeholder(entry)


def test_authorized_role_sees_real_data():
    tree = _tree_with_mental_health("p002")
    vt = build_virtual_tree(tree, role="Psychiatrist")
    found_real = False
    for sys_node in vt.root.children.values():
        if sys_node.name == "MentalHealth":
            for org in sys_node.children.values():
                for entry in org.children.values():
                    if not is_placeholder(entry):
                        found_real = True
    assert found_real
