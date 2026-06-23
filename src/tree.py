"""
TreeMedChain - Core Tree Structure

Tree shape (same skeleton for every patient — structural normalization
requires all patients present the same shape regardless of data):

PatientID (root)
├── Demographics
├── Gender
├── Cardiovascular  → Heart, BloodVessels
├── Respiratory     → Lungs, Trachea
├── Neurological    → Brain, SpinalCord
├── Digestive       → Stomach, Intestines, Liver
├── Musculoskeletal → Bones, Joints
├── Reproductive    → ReproductiveOrgans
├── MentalHealth    → Psychiatry
└── Unclassified    → General  (fallback for unmapped Synthea entries)

Each organ node holds entry nodes directly (flat, one level):
    organ → [entry, entry, ...]   node_type = "diagnosis"|"medications"|...
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid

NON_SYSTEM_CHILDREN = {"Demographics", "Gender"}

BODY_SYSTEMS: dict[str, list[str]] = {
    "Cardiovascular":  ["Heart", "BloodVessels"],
    "Respiratory":     ["Lungs", "Trachea"],
    "Neurological":    ["Brain", "SpinalCord"],
    "Digestive":       ["Stomach", "Intestines", "Liver"],
    "Musculoskeletal": ["Bones", "Joints"],
    "Reproductive":    ["ReproductiveOrgans"],
    "MentalHealth":    ["Psychiatry"],
    "Unclassified":    ["General"],
}

ENTRY_TYPES = {"Diagnosis", "Medications", "Procedures", "Imaging", "LabTests"}
_ENTRY_TYPES_LOWER = {e.lower() for e in ENTRY_TYPES}


@dataclass
class MedicalNode:
    """A single node in the patient's medical tree."""

    node_type: str
    name: str
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    data: dict = field(default_factory=dict)
    timestamp: str = ""

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    sensitivity: str = "standard"       # "standard" | "sensitive" | "high"
    allowed_roles: set[str] = field(default_factory=set)

    is_placeholder: bool = False
    is_real: bool = True

    # Set when entry data is encrypted and stored off-chain.
    # This hash is what gets logged on the blockchain.
    data_hash: str = ""

    children: dict[str, "MedicalNode"] = field(default_factory=dict)

    def add_child(self, child: "MedicalNode") -> "MedicalNode":
        self.children[child.name] = child
        return child

    def get_child(self, name: str) -> Optional["MedicalNode"]:
        return self.children.get(name)

    def has_data(self) -> bool:
        """True if this node is a clinical entry or any descendant is."""
        if self.node_type in _ENTRY_TYPES_LOWER:
            return True
        return any(c.has_data() for c in self.children.values())

    def touch(self):
        self.updated_at = datetime.now(timezone.utc)

    def __repr__(self):
        flag = "★" if self.node_type in _ENTRY_TYPES_LOWER else ""
        return f"<{self.node_type}:{self.name}{flag}>"


class PatientTree:
    """Wraps a single patient's full anatomical record tree."""

    def __init__(self, patient_id: str, demographics: Optional[dict] = None,
                 gender: Optional[str] = None):
        self.patient_id = patient_id
        self.root = MedicalNode(node_type="patient", name=patient_id)

        demo = self.root.add_child(MedicalNode(node_type="demographics", name="Demographics"))
        demo.data = demographics or {}

        gen = self.root.add_child(MedicalNode(node_type="gender", name="Gender"))
        gen.data = {"value": gender} if gender else {}

        # Fast organ lookup: (system_name, organ_name) -> MedicalNode
        self._organ_nodes: dict[tuple[str, str], MedicalNode] = {}

        for system_name, organs in BODY_SYSTEMS.items():
            sys_node = self.root.add_child(
                MedicalNode(node_type="system", name=system_name)
            )
            for organ_name in organs:
                org_node = sys_node.add_child(
                    MedicalNode(node_type="organ", name=organ_name)
                )
                self._organ_nodes[(system_name, organ_name)] = org_node

    # -- navigation --------------------------------------------------------

    def system_nodes(self):
        """Iterate over system-level nodes (skips Demographics and Gender)."""
        for name, node in self.root.children.items():
            if name not in NON_SYSTEM_CHILDREN:
                yield node

    def get_system_node(self, system_name: str) -> Optional[MedicalNode]:
        return self.root.children.get(system_name)

    # -- data insertion ----------------------------------------------------

    def add_clinical_entry(
        self,
        system: str,
        organ: str,
        entry_type: str,
        name: str,
        data: dict,
        timestamp: str,
        sensitivity: str = "standard",
        allowed_roles=None,
        offchain_store=None,
    ) -> MedicalNode:
        """
        Add a clinical entry directly under an organ node.

        If offchain_store is provided, the data dict is encrypted and stored
        there; the entry's data_hash is set to the returned content hash.
        Raises ValueError if system or organ are not in the predefined skeleton.
        """
        if system not in BODY_SYSTEMS:
            raise ValueError(f"Unknown system: {system!r}")
        if organ not in BODY_SYSTEMS[system]:
            raise ValueError(f"Unknown organ {organ!r} for system {system!r}")

        organ_node = self._organ_nodes[(system, organ)]
        entry = MedicalNode(
            node_type=entry_type.lower(),
            name=name,
            data=data,
            timestamp=timestamp,
            sensitivity=sensitivity,
            allowed_roles=set(allowed_roles) if allowed_roles else set(),
        )

        if offchain_store is not None:
            entry.data_hash = offchain_store.store(self.patient_id, data)
            entry.data = {}  # plaintext cleared — lives only in off-chain store

        # Key by node_id so duplicate-named entries don't overwrite each other
        organ_node.children[entry.node_id] = entry
        organ_node.touch()
        return entry

    # -- pruning -----------------------------------------------------------

    def prune_empty(self):
        """Remove organ/system subtrees with no clinical entries."""
        for sys_name in list(self.root.children.keys()):
            if sys_name in NON_SYSTEM_CHILDREN:
                continue
            sys_node = self.root.children[sys_name]
            for org_name in list(sys_node.children.keys()):
                if not sys_node.children[org_name].has_data():
                    del sys_node.children[org_name]
                    self._organ_nodes.pop((sys_name, org_name), None)
            if not sys_node.children:
                del self.root.children[sys_name]

    # -- display -----------------------------------------------------------

    def print_tree(self, node: Optional[MedicalNode] = None, indent: int = 0):
        if node is None:
            node = self.root
        marker = "🔒" if node.is_placeholder else ""
        print("  " * indent + f"{node} {marker}")
        for child in node.children.values():
            self.print_tree(child, indent + 1)


if __name__ == "__main__":
    tree = PatientTree(
        patient_id="patient_001",
        demographics={"name": "John Doe", "dob": "1980-04-12"},
        gender="male",
    )
    tree.add_clinical_entry(
        "Cardiovascular", "Heart", "Diagnosis",
        name="Hypertension", data={"code": "44054006"}, timestamp="2024-01-15",
        sensitivity="standard", allowed_roles={"Cardiologist", "PrimaryCare"},
    )
    tree.add_clinical_entry(
        "MentalHealth", "Psychiatry", "Diagnosis",
        name="Generalized Anxiety Disorder", data={}, timestamp="2023-08-02",
        sensitivity="high", allowed_roles={"Psychiatrist", "Therapist"},
    )
    print("=== Full tree ===")
    tree.print_tree()
    tree.prune_empty()
    print("\n=== After pruning empty branches ===")
    tree.print_tree()
