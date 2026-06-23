"""
TreeMedChain - Synthea Loader

Reads a Synthea CSV export directory and builds PatientTree objects
populated with real (synthetic) clinical data.

Expected files in data_dir (standard Synthea CSV export):
    patients.csv
    conditions.csv
    medications.csv
    procedures.csv
    observations.csv
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd

from src.tree import PatientTree, BODY_SYSTEMS
from src.code_mapping import (
    map_description_to_system_organ,
    is_sensitive,
    default_roles_for,
)

IMAGING_KEYWORDS = ["x-ray", "xray", "mri", "ct scan", "ultrasound", "imaging", "radiograph"]


def _clinical_type_for_observation(description: str) -> str:
    text = (description or "").lower()
    if any(kw in text for kw in IMAGING_KEYWORDS):
        return "Imaging"
    return "LabTests"


def _safe_str(value) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _build_patient_trees(patients_df: pd.DataFrame) -> dict[str, PatientTree]:
    trees: dict[str, PatientTree] = {}
    for _, row in patients_df.iterrows():
        patient_id = str(row["Id"])
        demographics = {
            "first_name": _safe_str(row.get("FIRST")),
            "last_name":  _safe_str(row.get("LAST")),
            "birthdate":  _safe_str(row.get("BIRTHDATE")),
            "address":    _safe_str(row.get("ADDRESS")),
            "city":       _safe_str(row.get("CITY")),
            "state":      _safe_str(row.get("STATE")),
        }
        gender = _safe_str(row.get("GENDER"))
        trees[patient_id] = PatientTree(
            patient_id=patient_id,
            demographics=demographics,
            gender=gender,
        )
    return trees


def _insert(trees: dict[str, PatientTree], patient_id: str, system: str,
            organ: str, entry_type: str, name: str, data: dict,
            timestamp: str) -> None:
    tree = trees.get(patient_id)
    if tree is None:
        return
    if system not in BODY_SYSTEMS or organ not in BODY_SYSTEMS.get(system, []):
        system, organ = "Unclassified", "General"
    sensitivity = "sensitive" if is_sensitive(system) else "standard"
    allowed_roles = default_roles_for(system)
    tree.add_clinical_entry(
        system=system, organ=organ, entry_type=entry_type,
        name=name, data=data, timestamp=timestamp,
        sensitivity=sensitivity, allowed_roles=allowed_roles,
    )


def _load_conditions(trees: dict[str, PatientTree], df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        desc = _safe_str(row.get("DESCRIPTION"))
        system, organ = map_description_to_system_organ(desc)
        _insert(trees, str(row["PATIENT"]), system, organ, "Diagnosis", desc,
                {"code": _safe_str(row.get("CODE")),
                 "start": _safe_str(row.get("START")),
                 "stop":  _safe_str(row.get("STOP"))},
                _safe_str(row.get("START")))


def _load_medications(trees: dict[str, PatientTree], df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        desc = _safe_str(row.get("DESCRIPTION"))
        system, organ = map_description_to_system_organ(desc)
        _insert(trees, str(row["PATIENT"]), system, organ, "Medications", desc,
                {"code": _safe_str(row.get("CODE")),
                 "start": _safe_str(row.get("START")),
                 "stop":  _safe_str(row.get("STOP"))},
                _safe_str(row.get("START")))


def _load_procedures(trees: dict[str, PatientTree], df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        desc = _safe_str(row.get("DESCRIPTION"))
        system, organ = map_description_to_system_organ(desc)
        _insert(trees, str(row["PATIENT"]), system, organ, "Procedures", desc,
                {"code": _safe_str(row.get("CODE")),
                 "date": _safe_str(row.get("START"))},
                _safe_str(row.get("START")))


def _load_observations(trees: dict[str, PatientTree], df: pd.DataFrame) -> None:
    for _, row in df.iterrows():
        desc = _safe_str(row.get("DESCRIPTION"))
        system, organ = map_description_to_system_organ(desc)
        ctype = _clinical_type_for_observation(desc)
        _insert(trees, str(row["PATIENT"]), system, organ, ctype, desc,
                {"value": _safe_str(row.get("VALUE")),
                 "units": _safe_str(row.get("UNITS")),
                 "date":  _safe_str(row.get("DATE"))},
                _safe_str(row.get("DATE")))


def load_synthea_directory(data_dir: str, prune: bool = False) -> dict[str, PatientTree]:
    """
    Load a Synthea CSV export directory into {patient_id: PatientTree}.

    prune=True removes empty branches — only use for debugging, never for
    role-filtered output (pruning is the exact shape leak we defend against).
    """
    path = Path(data_dir)
    trees = _build_patient_trees(pd.read_csv(path / "patients.csv"))

    for filename, loader in [
        ("conditions.csv",   _load_conditions),
        ("medications.csv",  _load_medications),
        ("procedures.csv",   _load_procedures),
        ("observations.csv", _load_observations),
    ]:
        fpath = path / filename
        if fpath.exists():
            loader(trees, pd.read_csv(fpath))
        else:
            print(f"[synthea_loader] {filename} not found, skipping")

    if prune:
        for tree in trees.values():
            tree.prune_empty()

    return trees


# Alias expected by tests and run_experiment.py
load_patient_trees = load_synthea_directory


if __name__ == "__main__":
    import sys
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/synthea_fixture"
    trees = load_synthea_directory(data_dir, prune=True)
    print(f"Loaded {len(trees)} patient(s)\n")
    for pid, tree in trees.items():
        print(f"=== {pid} ===")
        tree.print_tree()
        print()
