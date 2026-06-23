"""Verify that the adversary can infer from naive trees but not from virtual trees."""
from src.tree import PatientTree
from src.attack.experiment import run_experiment, _has_data_in_system


def _make_trees():
    trees = {}
    for i in range(10):
        pid = f"p{i:03d}"
        t = PatientTree(pid)
        if i % 2 == 0:
            t.add_clinical_entry(
                system="MentalHealth", organ="Psychiatry",
                entry_type="Diagnosis", name="Anxiety",
                data={}, timestamp="2022-01-01",
                sensitivity="high", allowed_roles=["Psychiatrist"],
            )
        else:
            t.add_clinical_entry(
                system="Cardiovascular", organ="Heart",
                entry_type="Diagnosis", name="Hypertension",
                data={}, timestamp="2021-01-01",
            )
        trees[pid] = t
    return trees


def test_naive_adversary_high_accuracy():
    trees = _make_trees()
    result = run_experiment(trees, target_system="MentalHealth", adversary_role="Insurer")
    assert result.naive_accuracy > 0.7, f"Naive accuracy too low: {result.naive_accuracy}"


def test_treemedchain_adversary_near_chance():
    trees = _make_trees()
    result = run_experiment(trees, target_system="MentalHealth", adversary_role="Insurer")
    # Chance level for a balanced population is 0.5; allow ±0.2 tolerance.
    assert abs(result.treemedchain_accuracy - 0.5) <= 0.2, (
        f"TreeMedChain accuracy should be near chance, got {result.treemedchain_accuracy}"
    )
