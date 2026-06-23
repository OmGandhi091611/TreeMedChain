"""
ShapeAdversary: infers whether a target system branch has real data by
inspecting tree structure alone — no decryption, no role bypass.

Under naive responses (pruned trees), branch presence directly leaks ground
truth. Under TreeMedChain virtual trees, every branch always has a fixed
placeholder shape, so the adversary has no signal.
"""
from __future__ import annotations

from src.tree import PatientTree, MedicalNode
from src.privacy.virtual_tree import is_placeholder


class ShapeAdversary:

    def __init__(self, target_system: str):
        self.target_system = target_system

    def predict(self, tree: PatientTree) -> bool:
        """Return True if adversary believes patient has data in target_system."""
        sys_node = tree.root.children.get(self.target_system)
        if sys_node is None:
            return False
        return self._has_real_data(sys_node)

    def _has_real_data(self, sys_node: MedicalNode) -> bool:
        for organ in sys_node.children.values():
            for entry in organ.children.values():
                if not is_placeholder(entry):
                    return True
        return False
