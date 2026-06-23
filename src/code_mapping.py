"""
TreeMedChain - Code Mapping
----------------------------
Maps Synthea clinical record descriptions to (body_system, organ) pairs
in the TreeMedChain tree skeleton.

Scope note: this is a deliberately narrow, keyword-based mapper covering
the ~6 systems in the prototype skeleton. It does NOT attempt full
SNOMED-CT / RxNorm hierarchy resolution - that's out of scope for a
prototype and adds significant effort with no research payoff here.
Synthea's CODE field (SNOMED/RxNorm/LOINC) is kept in the entry data for
reference, but matching is done against the human-readable DESCRIPTION
text, since that's robust to not having a full ontology on hand.

If you outgrow this later, the natural upgrade path is plugging in a
real SNOMED-CT hierarchy lookup instead of keyword matching.
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Keyword tables: (system, organ) -> list of keywords matched against
# the lowercased description string. Order matters - first match wins,
# so put more specific organs before more general ones within a system.
# ---------------------------------------------------------------------------

SYSTEM_ORGAN_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "Cardiovascular": {
        "Heart": [
            "heart", "cardiac", "myocardial", "coronary", "atrial",
            "ventricular", "arrhythmia", "hypertension", "blood pressure",
            "cholesterol", "ecg", "ekg", "cardio",
        ],
        "BloodVessels": [
            "vein", "artery", "vascular", "varicose", "thrombosis",
            "embolism", "aneurysm", "circulation",
        ],
    },
    "Respiratory": {
        "Lungs": [
            "lung", "pulmonary", "pneumonia", "asthma", "copd",
            "bronchitis", "respiratory failure", "oxygen",
        ],
        "Trachea": [
            "trachea", "airway", "throat", "laryngitis", "pharyngitis",
        ],
    },
    "Neurological": {
        "Brain": [
            "brain", "cerebral", "stroke", "seizure", "epilepsy",
            "migraine", "headache", "dementia", "alzheimer", "concussion",
        ],
        "SpinalCord": [
            "spinal", "spine", "nerve", "neuropathy", "sciatica",
        ],
    },
    "Digestive": {
        "Stomach": [
            "stomach", "gastric", "gastritis", "ulcer", "reflux", "gerd",
        ],
        "Intestines": [
            "intestin", "colon", "bowel", "crohn", "colitis", "appendix",
            "appendicitis",
        ],
        "Liver": [
            "liver", "hepatic", "hepatitis", "cirrhosis",
        ],
    },
    "Musculoskeletal": {
        "Bones": [
            "bone", "fracture", "osteoporosis", "osteopenia",
        ],
        "Joints": [
            "joint", "arthritis", "knee", "hip replacement", "shoulder",
            "tendon", "ligament", "sprain",
        ],
    },
    "Reproductive": {
        "ReproductiveOrgans": [
            "pregnan", "prenatal", "ovarian", "uterine", "menstrual",
            "prostate", "testicular", "contraception", "fertility",
        ],
    },
    "MentalHealth": {
        "Psychiatry": [
            "depress", "anxiety", "bipolar", "schizophrenia", "ptsd",
            "stress disorder", "substance", "psychiatric", "mental health",
            "suicidal", "panic disorder",
        ],
    },
}

# Systems whose data should default to "sensitive" classification.
# Used by synthea_loader.py when constructing entries.
SENSITIVE_SYSTEMS = {"MentalHealth", "Reproductive"}

# Default role visibility per system.
DEFAULT_ALLOWED_ROLES: dict[str, set[str]] = {
    "Cardiovascular":  {"Cardiologist", "PrimaryCare"},
    "Respiratory":     {"Pulmonologist", "PrimaryCare"},
    "Neurological":    {"Neurologist", "PrimaryCare"},
    "Digestive":       {"Gastroenterologist", "PrimaryCare"},
    "Musculoskeletal": {"Orthopedist", "PrimaryCare"},
    "Reproductive":    {"OBGYN", "PrimaryCare"},
    "MentalHealth":    {"Psychiatrist", "Therapist"},
    "Unclassified":    set(),
}

FALLBACK_SYSTEM = "Unclassified"
FALLBACK_ORGAN = "General"


def map_description_to_system_organ(description: str) -> tuple[str, str]:
    """
    Map a Synthea condition/medication/procedure description to a
    (system, organ) pair using keyword matching.

    Falls back to ("Unclassified", "General") if nothing matches -
    these should be reviewed periodically to expand keyword coverage,
    rather than silently dropped.
    """
    if not description:
        return FALLBACK_SYSTEM, FALLBACK_ORGAN

    text = description.lower()

    for system, organs in SYSTEM_ORGAN_KEYWORDS.items():
        for organ, keywords in organs.items():
            for kw in keywords:
                if kw in text:
                    return system, organ

    return FALLBACK_SYSTEM, FALLBACK_ORGAN


def is_sensitive(system: str) -> bool:
    return system in SENSITIVE_SYSTEMS


def default_roles_for(system: str) -> set[str]:
    return DEFAULT_ALLOWED_ROLES.get(system, set())


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    samples = [
        "Hypertension",
        "Essential hypertension (disorder)",
        "Major depressive disorder",
        "Fracture of forearm",
        "Asthma",
        "Routine prenatal visit",
        "Some totally unrelated future diagnosis name",
    ]
    for s in samples:
        system, organ = map_description_to_system_organ(s)
        print(f"{s!r:55} -> {system}/{organ}  (sensitive={is_sensitive(system)})")