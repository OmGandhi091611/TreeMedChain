"""
Naive vs. TreeMedChain comparative privacy experiment.

Naive system:      pruned tree (shape leaks ground truth)
TreeMedChain:      structural normalization (placeholders, shape reveals nothing)

Expected result:
    naive_accuracy      ≈ 1.0   (adversary reads branch presence directly)
    treemedchain_accuracy ≈ 0.5  (adversary reduced to random guessing)
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Dict

from src.tree import PatientTree
from src.privacy.virtual_tree import build_virtual_tree
from src.attack.adversary import ShapeAdversary


@dataclass
class ExperimentResult:
    n_patients: int
    naive_accuracy: float
    treemedchain_accuracy: float
    target_system: str
    adversary_role: str


def _naive_response(patient_tree: PatientTree) -> PatientTree:
    """Pruned tree with no access control — baseline without privacy."""
    naive = copy.deepcopy(patient_tree)
    naive.prune_empty()
    return naive


def _has_data_in_system(tree: PatientTree, system: str) -> bool:
    sys_node = tree.root.children.get(system)
    if sys_node is None:
        return False
    return any(len(organ.children) > 0 for organ in sys_node.children.values())


def run_experiment(
    patient_trees: Dict[str, PatientTree],
    target_system: str = "MentalHealth",
    adversary_role: str = "Insurer",
) -> ExperimentResult:
    adversary = ShapeAdversary(target_system=target_system)
    ground_truth: Dict[str, bool] = {}
    naive_preds: Dict[str, bool] = {}
    tmc_preds: Dict[str, bool] = {}

    for pid, tree in patient_trees.items():
        ground_truth[pid] = _has_data_in_system(tree, target_system)
        naive_preds[pid] = adversary.predict(_naive_response(tree))
        tmc_preds[pid] = adversary.predict(build_virtual_tree(tree, adversary_role))

    n = len(patient_trees)
    naive_acc = sum(naive_preds[p] == ground_truth[p] for p in patient_trees) / n
    tmc_acc = sum(tmc_preds[p] == ground_truth[p] for p in patient_trees) / n

    return ExperimentResult(
        n_patients=n,
        naive_accuracy=naive_acc,
        treemedchain_accuracy=tmc_acc,
        target_system=target_system,
        adversary_role=adversary_role,
    )
