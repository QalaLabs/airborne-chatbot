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
        "topics": [
            "Fly-by-Wire Flight Control Systems & Hydraulic Actuators",
            "Hydraulic Accumulators & Nitrogen Pre-charge Functions",
            "Aircraft Batteries & Nickel-Cadmium (Ni-Cd) Thermal Runaway"
        ],
        "keywords": ["fly by wire", "fbw", "hydraulic", "accumulator", "nitrogen", "thermal runaway", "ni-cd", "battery", "electrics"]
    },
    "Powerplant": {
        "title": "Aircraft Powerplants & Propulsion Systems",
        "topics": [
            "Piston Engine Carburetor Icing & Induction Heating",
            "Aero-Engine Independent Magneto Dual Ignition Systems",
            "Gas Turbine Turbofans: High Bypass vs Low Bypass Efficiency"
        ],
        "keywords": ["carburetor", "carburettor", "carb heat", "magneto", "magnetos", "ignition", "spark plug", "turbofan", "bypass ratio", "turbojet"]
    },
    "Radio Telephony": {
        "title": "Radio Telephony Restricted (Aeronautical) & Phraseology",
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
            "version": "1.2.0",
            "total_levels": 3,
            "subjects": {}
        }

        # Query chunk counts per subject from SQLite
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

    def get_hierarchical_context(self, subject: str) -> Dict[str, Any]:
        """Returns chapter topics and tree metadata for a given subject"""
        return SUBJECT_TOPIC_TAXONOMY.get(subject, {
            "title": subject,
            "topics": ["General DGCA Theoretical Knowledge"],
            "keywords": []
        })

raptor_engine = RaptorHierarchicalEngine()
