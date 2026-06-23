"""
TreeMedChain - Blockchain Access Logger

Every time a role queries a patient record, this module:
  1. Builds the role-filtered virtual tree
  2. Logs an immutable block to the chain containing:
       - SHA-256 hash of patient_id  (raw ID never touches the chain)
       - Role of the accessor
       - Timestamp
       - Which systems showed real data vs placeholders
       - Hash of the virtual tree structure (proves exactly what was returned)
  3. Returns the virtual tree to the caller

The tree_root_hash is the key audit primitive: it cryptographically binds
the access record to the specific view the accessor received. Any attempt
to later claim "I was shown different data" is disprovable from the chain.
"""

from __future__ import annotations

import hashlib
import json
import time

from src.tree import PatientTree
from src.blockchain.chain import Block, Chain
from src.blockchain.poa import AuthorityNode
from src.privacy.virtual_tree import build_virtual_tree


def _hash_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def _tree_root_hash(virtual_tree: PatientTree) -> str:
    """
    Deterministic hash of the virtual tree's structure.

    Encodes node identity and placeholder status — proves what was shown
    to the accessor without revealing any clinical content.
    """
    records = []
    for sys_node in virtual_tree.system_nodes():
        for org_name, org in sys_node.children.items():
            for entry_id, entry in org.children.items():
                records.append(
                    f"{sys_node.name}/{org_name}/{entry_id}/{entry.is_placeholder}"
                )
    payload = "|".join(sorted(records))
    return hashlib.sha256(payload.encode()).hexdigest()


def _systems_summary(virtual_tree: PatientTree) -> dict:
    """Classify each system as showing real data or placeholders."""
    real, redacted = [], []
    for sys_node in virtual_tree.system_nodes():
        has_real = any(
            not entry.is_placeholder
            for org in sys_node.children.values()
            for entry in org.children.values()
        )
        (real if has_real else redacted).append(sys_node.name)
    return {"real": sorted(real), "redacted": sorted(redacted)}


def _content_hashes(virtual_tree: PatientTree) -> list[str]:
    """Collect data_hashes from all real (non-placeholder) entries shown."""
    hashes = []
    for sys_node in virtual_tree.system_nodes():
        for org in sys_node.children.values():
            for entry in org.children.values():
                if not entry.is_placeholder and entry.data_hash:
                    hashes.append(entry.data_hash)
    return sorted(hashes)


def log_tree_access(
    chain: Chain,
    patient_tree: PatientTree,
    virtual_tree: PatientTree,
    role: str,
    authority: str,
) -> Block:
    """
    Log a tree access event as an immutable block on the chain.

    Can be called independently if you already have a virtual tree,
    or use access_patient_record() to do both in one step.
    """
    summary = _systems_summary(virtual_tree)
    event = {
        "patient_id_hash":   _hash_str(patient_tree.patient_id),
        "role":              role,
        "timestamp":         time.time(),
        "systems_real":      summary["real"],
        "systems_redacted":  summary["redacted"],
        "tree_root_hash":    _tree_root_hash(virtual_tree),
        "content_hashes":    _content_hashes(virtual_tree),
    }
    node = AuthorityNode(authority)
    return node.sign_and_log(chain, event)


def access_patient_record(
    patient_tree: PatientTree,
    role: str,
    chain: Chain,
    authority: str,
    offchain_store=None,
) -> PatientTree:
    """
    Single entry point for a role querying a patient record.

    Builds the role-filtered virtual tree, optionally decrypts authorized
    entries from the off-chain store, and logs the access atomically.
    Returns the virtual tree to the caller.
    """
    virtual = build_virtual_tree(patient_tree, role)

    if offchain_store is not None:
        for sys_node in virtual.system_nodes():
            for org in sys_node.children.values():
                for entry in org.children.values():
                    if not entry.is_placeholder and entry.data_hash:
                        entry.data = offchain_store.retrieve(
                            entry.data_hash, patient_tree.patient_id
                        )

    log_tree_access(chain, patient_tree, virtual, role, authority)
    return virtual
