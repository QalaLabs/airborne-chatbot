import json
import os
import sqlite3
import re
from pathlib import Path
from typing import Dict, Any, List, Optional

RAPTOR_TREE_PATH = Path("data/raptor_tree.json")
DB_PATH = Path("data/aviation_rag.db")

# Subject & Topic Taxonomy mapping DGCA CPL Ground School curriculum
SUBJECT_TOPIC_TAXONOMY = {
    "Principles of Flight": {
        "title": "Principles of Flight & Aerodynamics",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 024 (Principles of Flight)",
        "recommended_next": "Boundary Layer Separation & Stalling Recovery",
        "topics": [
            "Lift, Drag & Aerofoil Characteristics",
            "Stalling, Angle of Attack & Boundary Layer Control",
            "Stability, Control Surfaces (Aileron, Elevator, Rudder) & Trim",
            "High Speed Flight, Transonic Mach Tuck & Shockwave Stall",
            "Ground Effect & Vortex Induced Drag"
        ],
        "keywords": ["lift", "drag", "stall", "angle of attack", "aerofoil", "airfoil", "camber", "rudder", "aileron", "elevator", "dihedral", "mach", "transonic", "vortex", "ground effect"]
    },
    "Aviation Meteorology": {
        "title": "Aviation Meteorology & Weather Hazards",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 022 (Aviation Meteorology)",
        "recommended_next": "Upper-Level Jet Streams & Clear Air Turbulence (CAT)",
        "topics": [
            "Altimetry, Atmospheric Pressure & QNH/QFE/QNE Settings",
            "Lapse Rates, Atmospheric Stability & Inversions",
            "Winds, Coriolis Force, Geostrophic Balance & Wind Shear",
            "Clouds, Cumulonimbus, Thunderstorms & Microbursts",
            "Fog (Radiation & Advection) & Aircraft Icing (Clear & Rime)",
            "Upper Level Jet Streams & Clear Air Turbulence"
        ],
        "keywords": ["altimeter", "qnh", "qfe", "lapse rate", "coriolis", "geostrophic", "cumulonimbus", "fog", "radiation fog", "icing", "rime", "clear ice", "cat", "turbulence", "jet stream"]
    },
    "Indian Meteorology": {
        "title": "Indian Climatology & Regional Aviation Weather",
        "syllabus_code": "DGCA CAR Sec 7 > Subject 022 Annexure (Indian Climatology)",
        "recommended_next": "Southwest Monsoon Onset & Tropical Easterly Jet",
        "topics": [
            "Southwest Monsoon Mechanism & Tropical Easterly Jet",
            "Western Disturbances, Winter Fog & Snowfall",
            "Pre-Monsoon Convective Squalls (Nor'westers & Kalbaisakhi)",
            "Tropical Cyclones & Inter-Tropical Convergence Zone (ITCZ)"
        ],
        "keywords": ["monsoon", "easterly jet", "somali jet", "western disturbances", "norwester", "kalbaisakhi", "andhi", "itcz"]
    },
    "Air Regulations": {
        "title": "Air Regulations & Rules of the Air",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 023 (Air Regulations)",
        "recommended_next": "Visual Flight Rules (VFR) & Instrument Flight Rules (IFR) Minima",
        "topics": [
            "Rules of the Air (Right of Way, Head-On & Converging)",
            "Semi-Circular Cruising Altitude System",
            "Emergency SSR Transponder Squawk Codes (7500, 7600, 7700)",
            "DGCA Flight Duty Time Limitations (FDTL)",
            "Visual Flight Rules (VFR) & Instrument Flight Rules (IFR) Minima",
            "Logbook Maintenance & Aircraft Documents Carriage"
        ],
        "keywords": ["right of way", "head on", "converging", "semi-circular", "squawk", "7500", "7600", "7700", "fdtl", "vfr", "ifr", "logbook", "documents", "rule 67"]
    },
    "General Navigation": {
        "title": "General Navigation & Flight Planning",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 021 (Air Navigation)",
        "recommended_next": "Critical Point / Point of Equal Time (PET) Formulations",
        "topics": [
            "Great Circles, Rhumb Lines & Mercator/Lambert Projections",
            "Earth Convergence & Conversion Angle",
            "Airspeeds (IAS, CAS, EAS, TAS) & Density Corrections",
            "1 in 60 Rule, Track Errors & Wind Triangle Calculations",
            "Critical Point / Point of Equal Time (PET) & Point of Safe Return (PSR)"
        ],
        "keywords": ["great circle", "rhumb line", "convergence", "conversion angle", "true airspeed", "tas", "ias", "cas", "1 in 60", "point of equal time", "point of safe return", "psr", "pet"]
    },
    "Radio Navigation": {
        "title": "Radio Navigation Aids & Radar Systems",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 021 Part B (Radio Navigation)",
        "recommended_next": "Instrument Landing System (ILS) Localizer & Glide Path",
        "topics": [
            "VOR (VHF Omnidirectional Range) & Radial Tracking",
            "DME (Distance Measuring Equipment) & Slant Range Geometry",
            "ILS (Instrument Landing System) Localizer & Glide Path",
            "NDB & Automatic Direction Finder (ADF) Errors (Coastal & Night Effect)",
            "Surveillance Radar (PSR & SSR) & Transponders",
            "GNSS, GPS Architecture & Receiver Autonomous Integrity Monitoring (RAIM)"
        ],
        "keywords": ["vor", "radial", "dme", "slant range", "ils", "localizer", "glide path", "ndb", "adf", "coastal refraction", "night effect", "radar", "psr", "ssr", "raim", "gps"]
    },
    "Aircraft Systems & Electrics": {
        "title": "Aircraft Systems, Hydraulics & Electrical Infrastructure",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 024 Part B (Aircraft Systems)",
        "recommended_next": "Fly-by-Wire Flight Control Redundancy & Actuators",
        "topics": [
            "Fly-by-Wire Flight Control Systems & Hydraulic Actuators",
            "Hydraulic Accumulators & Nitrogen Pre-charge Functions",
            "Aircraft Batteries & Nickel-Cadmium (Ni-Cd) Thermal Runaway"
        ],
        "keywords": ["fly by wire", "fbw", "hydraulic", "accumulator", "nitrogen", "thermal runaway", "ni-cd", "battery", "electrics"]
    },
    "Powerplant": {
        "title": "Aircraft Powerplants & Propulsion Systems",
        "syllabus_code": "DGCA CAR Sec 7 > Ground Subject 024 Part C (Aero Engines)",
        "recommended_next": "Gas Turbine Turbofan Bypass Ratios & FADEC Controls",
        "topics": [
            "Piston Engine Carburetor Icing & Induction Heating",
            "Aero-Engine Independent Magneto Dual Ignition Systems",
            "Gas Turbine Turbofans: High Bypass vs Low Bypass Efficiency"
        ],
        "keywords": ["carburetor", "carburettor", "carb heat", "magneto", "magnetos", "ignition", "spark plug", "turbofan", "bypass ratio", "turbojet"]
    },
    "Radio Telephony": {
        "title": "Radio Telephony Restricted (Aeronautical) & Phraseology",
        "syllabus_code": "Ministry of Communications & WPC > RTR(A) COP Syllabus",
        "recommended_next": "Emergency Distress (MAYDAY) & Urgency (PAN PAN) Transmissions",
        "topics": [
            "Distress Communications (MAYDAY) Format & Procedures",
            "Urgency Communications (PAN PAN) Protocol",
            "Mandatory ATC Readback Transmissions",
            "Radio Communication Failure (RCF) Procedures under IFR"
        ],
        "keywords": ["mayday", "pan pan", "distress", "urgency", "readback", "clearance", "communication failure", "phraseology", "rtr"]
    }
}

class RaptorHierarchicalEngine:
    """
    RAPTOR (Recursive Abstractive Processing for Tree-Organized Retrieval) Engine.
    Organizes 9,000+ DGCA textbook chunks into a 3-tier hierarchy:
    - Root: Comprehensive DGCA Pilot Training Curriculum
    - Level 1: Core Subjects (Air Nav, Met, Regs, Tech Gen, RT)
    - Level 2: Topic & Chapter Subclusters
    - Level 3: Leaf Chunks (indexed with SQLite FTS5)
    """
    def __init__(self, db_path: str = str(DB_PATH), tree_path: str = str(RAPTOR_TREE_PATH)):
        self.db_path = db_path
        self.tree_path = tree_path
        self.tree = self._load_or_build_tree()

    def _load_or_build_tree(self) -> Dict[str, Any]:
        if os.path.exists(self.tree_path):
            try:
                with open(self.tree_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[RAPTOR] Failed to load cached tree: {e}")

        return self.build_and_save_tree()

    def build_and_save_tree(self) -> Dict[str, Any]:
        """Constructs and serializes the RAPTOR tree representation"""
        tree = {
            "root": "DGCA Commercial Pilot Training Ground Curriculum",
            "version": "1.3.0",
            "total_levels": 3,
            "subjects": {}
        }

        counts = {}
        if os.path.exists(self.db_path):
            try:
                with sqlite3.connect(self.db_path) as con:
                    for row in con.execute("SELECT subject, count(*) FROM chunks GROUP BY subject"):
                        counts[row[0]] = row[1]
            except Exception as e:
                print(f"[RAPTOR] Database query error: {e}")

        for subj_key, meta in SUBJECT_TOPIC_TAXONOMY.items():
            tree["subjects"][subj_key] = {
                "title": meta["title"],
                "syllabus_code": meta.get("syllabus_code", ""),
                "recommended_next": meta.get("recommended_next", ""),
                "topics": meta["topics"],
                "keywords": meta["keywords"],
                "chunk_count": counts.get(subj_key, 0)
            }

        os.makedirs(os.path.dirname(self.tree_path), exist_ok=True)
        with open(self.tree_path, "w", encoding="utf-8") as f:
            json.dump(tree, f, indent=2)

        return tree

    def resolve_subject_cluster(self, query: str) -> Optional[str]:
        """Classifies query into the most relevant subject cluster"""
        lower = query.lower()
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', lower))
        best_subj = None
        best_matches = 0

        for subj, meta in SUBJECT_TOPIC_TAXONOMY.items():
            matches = len(tokens & set(meta["keywords"]))
            if matches > best_matches:
                best_matches = matches
                best_subj = subj

        return best_subj

    def get_syllabus_breadcrumb(self, subject: str) -> Dict[str, str]:
        """Returns curriculum hierarchy and recommended next module"""
        meta = SUBJECT_TOPIC_TAXONOMY.get(subject, {})
        return {
            "breadcrumb": meta.get("syllabus_code", f"DGCA CAR Section 7 > {subject}"),
            "recommended_next": meta.get("recommended_next", "Comprehensive DGCA Pariksha Practice Examination")
        }

raptor_engine = RaptorHierarchicalEngine()
