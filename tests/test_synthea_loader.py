"""Smoke tests for the Synthea loader using minimal fixture CSVs."""
import csv
import pytest
from src.synthea_loader import load_patient_trees


def _write_csv(path, rows, fieldnames):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


@pytest.fixture()
def synthea_dir(tmp_path):
    _write_csv(
        str(tmp_path / "patients.csv"),
        [{"Id": "p1"}, {"Id": "p2"}],
        ["Id"],
    )
    _write_csv(
        str(tmp_path / "conditions.csv"),
        [
            {"PATIENT": "p1", "DESCRIPTION": "Major depression", "CODE": "370143000",
             "START": "2020-01-01", "STOP": ""},
            {"PATIENT": "p2", "DESCRIPTION": "Hypertension", "CODE": "44054006",
             "START": "2019-06-01", "STOP": ""},
        ],
        ["PATIENT", "DESCRIPTION", "CODE", "START", "STOP"],
    )
    return str(tmp_path)


def test_load_returns_all_patients(synthea_dir):
    trees = load_patient_trees(synthea_dir)
    assert set(trees.keys()) == {"p1", "p2"}


def test_mental_health_entry_loaded(synthea_dir):
    trees = load_patient_trees(synthea_dir)
    psych = trees["p1"]._organ_nodes[("MentalHealth", "Psychiatry")]
    assert any("depress" in n.name.lower() for n in psych.children.values())


def test_cardiovascular_entry_loaded(synthea_dir):
    trees = load_patient_trees(synthea_dir)
    heart = trees["p2"]._organ_nodes[("Cardiovascular", "Heart")]
    assert any("hypertension" in n.name.lower() for n in heart.children.values())
