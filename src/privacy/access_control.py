# Phase 3: Role-based access control for tree nodes.
from __future__ import annotations

from src.tree import MedicalNode

# Roles with blanket read access to all systems (e.g. treating physician).
_SUPERROLES = {"PrimaryCare", "Admin"}

# Systems entirely restricted from certain roles.
_SYSTEM_BLOCKLIST: dict[str, set[str]] = {
    "MentalHealth": {"Insurer", "Employer"},
    "Reproductive": {"Insurer", "Employer"},
}


def is_authorized(role: str, node: MedicalNode) -> bool:
    """Return True if role may view node's real contents."""
    if role in _SUPERROLES:
        return True
    if node.sensitivity == "high":
        return role in node.allowed_roles
    if node.allowed_roles and role not in node.allowed_roles:
        return False
    return True


def is_authorized_for_system(role: str, system_name: str) -> bool:
    """Coarser check at the system level, used by experiment harness."""
    if role in _SUPERROLES:
        return True
    blocked = _SYSTEM_BLOCKLIST.get(system_name, set())
    return role not in blocked
