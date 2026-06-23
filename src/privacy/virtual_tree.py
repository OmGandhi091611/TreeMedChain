"""
TreeMedChain - Structural Normalization Layer

build_virtual_tree returns a PatientTree whose shape is IDENTICAL for every
patient regardless of what data they have in unauthorized branches.

Unauthorized organ branches are replaced with a fixed number of placeholder
entry nodes so an adversary cannot distinguish:
  - "MentalHealth branch absent because patient has no data"  (naive system)
  - "MentalHealth branch present with 2 entries"             (TreeMedChain)

Both look the same under TreeMedChain: 2 entries, all placeholders.
"""

from __future__ import annotations

import copy

from src.tree import MedicalNode, PatientTree, NON_SYSTEM_CHILDREN
from src.privacy.access_control import is_authorized, is_authorized_for_system

FIXED_PLACEHOLDER_CHILDREN = 2   # constant across all patients — must not vary
_PLACEHOLDER_SENTINEL = "__PLACEHOLDER__"


def _make_placeholder_entry() -> MedicalNode:
    node = MedicalNode(
        node_type="diagnosis",
        name=_PLACEHOLDER_SENTINEL,
        data={"code": "REDACTED", "detail": "REDACTED"},
        sensitivity="high",
        allowed_roles=set(),
        is_placeholder=True,
        is_real=False,
    )
    return node


def build_virtual_tree(patient_tree: PatientTree, role: str) -> PatientTree:
    """
    Return a new PatientTree for `role` where unauthorized organ branches are
    replaced with structurally identical placeholder nodes.

    The returned tree has the same system/organ shape for ALL patients,
    eliminating structural information leakage.
    """
    virtual = PatientTree(patient_id=patient_tree.patient_id)

    for sys_node in patient_tree.system_nodes():
        v_sys = virtual.get_system_node(sys_node.name)
        if v_sys is None:
            continue

        system_allowed = is_authorized_for_system(role, sys_node.name)

        for org_name, org_node in sys_node.children.items():
            v_org = v_sys.get_child(org_name)
            if v_org is None:
                v_org = v_sys.add_child(
                    MedicalNode(node_type="organ", name=org_name)
                )

            if system_allowed and is_authorized(role, org_node):
                for entry in org_node.children.values():
                    v_org.children[entry.node_id] = copy.deepcopy(entry)
            else:
                for _ in range(FIXED_PLACEHOLDER_CHILDREN):
                    p = _make_placeholder_entry()
                    v_org.children[p.node_id] = p

    return virtual


def is_placeholder(node: MedicalNode) -> bool:
    return node.is_placeholder
