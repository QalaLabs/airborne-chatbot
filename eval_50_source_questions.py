import json
import time
from typing import List, Dict, Any
from backend.ai_engine import ai_engine
from backend.rag_pipeline import rag_pipeline

TEST_50_QUESTIONS = [
    # --- Principles of Flight & Aerodynamics ---
    {
        "id": 1,
        "subject": "Principles of Flight",
        "question": "What causes aerodynamic stall and how does angle of attack affect it?",
        "expected_keywords": ["stall", "separation", "angle of attack", "airflow"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 2,
        "subject": "Principles of Flight",
        "question": "How do wingtip vortices generate induced drag on an aircraft wing?",
        "expected_keywords": ["vortex", "induced drag", "wingtip", "downwash"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 3,
        "subject": "Principles of Flight",
        "question": "What is adverse yaw and how does the rudder counteract it during turns?",
        "expected_keywords": ["adverse yaw", "aileron", "rudder", "yaw"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 4,
        "subject": "Principles of Flight",
        "question": "Explain ground effect on aircraft lift and induced drag during takeoff and landing",
        "expected_keywords": ["ground effect", "induced drag", "wing", "downwash"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 5,
        "subject": "Principles of Flight",
        "question": "How does the center of pressure move with angle of attack in cambered aerofoils?",
        "expected_keywords": ["center of pressure", "camber", "angle of attack", "aerofoil"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 6,
        "subject": "Principles of Flight",
        "question": "How does wing dihedral provide lateral stability in roll?",
        "expected_keywords": ["dihedral", "lateral stability", "roll", "sideslip"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 7,
        "subject": "Principles of Flight",
        "question": "What is Mach tuck and shock stall in high speed transonic flight?",
        "expected_keywords": ["mach", "shock", "stall", "transonic"],
        "expected_source": "Principles of Flight"
    },
    {
        "id": 8,
        "subject": "Principles of Flight",
        "question": "How does wing aspect ratio affect induced drag and aerodynamic efficiency?",
        "expected_keywords": ["aspect ratio", "induced drag", "span", "chord"],
        "expected_source": "Principles of Flight"
    },

    # --- Aviation Meteorology (Oxford Met) ---
    {
        "id": 9,
        "subject": "Aviation Meteorology",
        "question": "What are the altimeter pressure settings for QFE, QNH, and standard 1013 hPa?",
        "expected_keywords": ["qfe", "qnh", "altimeter", "pressure"],
        "expected_source": "Meteorology"
    },
    {
        "id": 10,
        "subject": "Aviation Meteorology",
        "question": "What is the difference between Environmental Lapse Rate and Dry Adiabatic Lapse Rate?",
        "expected_keywords": ["lapse rate", "dalr", "temperature", "adiabatic"],
        "expected_source": "Meteorology"
    },
    {
        "id": 11,
        "subject": "Aviation Meteorology",
        "question": "How does Coriolis force affect geostrophic wind direction in the Northern Hemisphere?",
        "expected_keywords": ["coriolis", "geostrophic", "wind", "pressure gradient"],
        "expected_source": "Meteorology"
    },
    {
        "id": 12,
        "subject": "Aviation Meteorology",
        "question": "What are the formation stages of a Cumulonimbus cloud and associated microburst hazards?",
        "expected_keywords": ["cumulonimbus", "microburst", "downdraft", "thunderstorm"],
        "expected_source": "Meteorology"
    },
    {
        "id": 13,
        "subject": "Aviation Meteorology",
        "question": "What are the conditions required for radiation fog formation versus advection fog?",
        "expected_keywords": ["radiation fog", "advection fog", "moisture", "cooling"],
        "expected_source": "Meteorology"
    },
    {
        "id": 14,
        "subject": "Aviation Meteorology",
        "question": "What causes Clear Air Turbulence around upper-level jet stream cores?",
        "expected_keywords": ["clear air turbulence", "jet stream", "shear", "cat"],
        "expected_source": "Meteorology"
    },
    {
        "id": 15,
        "subject": "Aviation Meteorology",
        "question": "Explain mountain waves, rotor clouds, and standing lenticular cloud hazards",
        "expected_keywords": ["mountain wave", "rotor", "lenticular", "downdraft"],
        "expected_source": "Meteorology"
    },
    {
        "id": 16,
        "subject": "Aviation Meteorology",
        "question": "What is the difference between Clear Ice and Rime Ice in aircraft icing?",
        "expected_keywords": ["clear ice", "rime ice", "supercooled", "droplets"],
        "expected_source": "Meteorology"
    },

    # --- Indian Meteorology (IC Joshi) ---
    {
        "id": 17,
        "subject": "Indian Meteorology",
        "question": "What is the Southwest Monsoon mechanism and Tropical Easterly Jet?",
        "expected_keywords": ["monsoon", "trough", "easterly jet", "tibetan"],
        "expected_source": "Indian Meteorology"
    },
    {
        "id": 18,
        "subject": "Indian Meteorology",
        "question": "What is the altitude and wind speed of Tropical Easterly Jet over South India?",
        "expected_keywords": ["tropical easterly jet", "easterlies", "summer", "southern india"],
        "expected_source": "Meteorology"
    },
    {
        "id": 19,
        "subject": "Indian Meteorology",
        "question": "How do Western Disturbances cause winter fog and snow over North India airfields?",
        "expected_keywords": ["western disturbances", "fog", "mediterranean", "snow"],
        "expected_source": "Indian Meteorology"
    },
    {
        "id": 20,
        "subject": "Indian Meteorology",
        "question": "Explain Nor'westers or Kalbaisakhi pre-monsoon convective squalls in India",
        "expected_keywords": ["nor'wester", "kalbaisakhi", "squall", "convective"],
        "expected_source": "Indian Meteorology"
    },

    # --- Air Regulations (RK Bali & DGCA) ---
    {
        "id": 21,
        "subject": "Air Regulations",
        "question": "What are the rules of the air when two aircraft approach head on?",
        "expected_keywords": ["head-on", "right", "heading", "collision"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 22,
        "subject": "Air Regulations",
        "question": "What is the right of way rule when two power-driven aircraft are converging at the same level?",
        "expected_keywords": ["converging", "right", "give way", "aircraft"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 23,
        "subject": "Air Regulations",
        "question": "Explain the semi-circular cruising level rule for eastbound and westbound flights in Indian airspace",
        "expected_keywords": ["semi-circular", "cruising level", "odd", "even", "track"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 24,
        "subject": "Air Regulations",
        "question": "What are the standard SSR emergency squawk codes for hijack, radio failure, and emergency?",
        "expected_keywords": ["7500", "7600", "7700", "emergency"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 25,
        "subject": "Air Regulations",
        "question": "What are the DGCA Flight Duty Time Limitations for daily and weekly maximum flight hours?",
        "expected_keywords": ["flight duty time", "fdtl", "flight time", "rest"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 26,
        "subject": "Air Regulations",
        "question": "What are the Visual Flight Rules VFR visibility and cloud distance minima in controlled airspace?",
        "expected_keywords": ["vfr", "visibility", "cloud", "distance"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 27,
        "subject": "Air Regulations",
        "question": "What are the DGCA logbook entry maintenance requirements under Aircraft Rule 67A?",
        "expected_keywords": ["logbook", "rule 67a", "48 hours", "cfi"],
        "expected_source": "Air Regulations"
    },
    {
        "id": 28,
        "subject": "Air Regulations",
        "question": "What mandatory aircraft documents must be carried on board an Indian registered aircraft under Rule 7?",
        "expected_keywords": ["rule 7", "certificate of registration", "airworthiness", "license"],
        "expected_source": "Air Regulations"
    },

    # --- Air Navigation: General Navigation & Flight Planning ---
    {
        "id": 29,
        "subject": "General Navigation",
        "question": "What is the difference between a Great Circle track and a Rhumb Line track on Mercator charts?",
        "expected_keywords": ["great circle", "rhumb line", "mercator", "track"],
        "expected_source": "Navigation"
    },
    {
        "id": 30,
        "subject": "General Navigation",
        "question": "How is Earth convergence and conversion angle calculated between two meridians?",
        "expected_keywords": ["convergence", "conversion angle", "meridian", "latitude"],
        "expected_source": "Navigation"
    },
    {
        "id": 31,
        "subject": "General Navigation",
        "question": "How does True Airspeed relate to Indicated Airspeed with increasing altitude and temperature?",
        "expected_keywords": ["true airspeed", "indicated airspeed", "density", "altitude"],
        "expected_source": "Navigation"
    },
    {
        "id": 32,
        "subject": "General Navigation",
        "question": "How is the 1 in 60 rule applied to calculate track error and closing angle in flight navigation?",
        "expected_keywords": ["1 in 60", "track error", "distance", "heading"],
        "expected_source": "Navigation"
    },
    {
        "id": 33,
        "subject": "Flight Planning",
        "question": "Explain the Point of Equal Time formula in flight planning between departure and destination",
        "expected_keywords": ["point of equal time", "pet", "critical point", "groundspeed"],
        "expected_source": "Flight Planning"
    },
    {
        "id": 34,
        "subject": "Flight Planning",
        "question": "How is the Point of Safe Return calculated for aircraft fuel endurance?",
        "expected_keywords": ["point of safe return", "psr", "endurance", "fuel"],
        "expected_source": "Flight Planning"
    },

    # --- Radio Navigation & Radar ---
    {
        "id": 35,
        "subject": "Radio Navigation",
        "question": "Explain how VOR navigation aids determine aircraft radial and TO FROM indication",
        "expected_keywords": ["vor", "radial", "phase", "to/from"],
        "expected_source": "Radio Navigation"
    },
    {
        "id": 36,
        "subject": "Radio Navigation",
        "question": "What is DME slant range error and when is it most significant relative to ground distance?",
        "expected_keywords": ["dme", "slant range", "distance", "overhead"],
        "expected_source": "Radio Navigation"
    },
    {
        "id": 37,
        "subject": "Radio Navigation",
        "question": "Explain ILS Localizer and Glide Path beam frequencies and coverage sectors",
        "expected_keywords": ["ils", "localizer", "glide path", "runway"],
        "expected_source": "Radio Navigation"
    },
    {
        "id": 38,
        "subject": "Radio Navigation",
        "question": "What causes NDB coastal refraction and night effect in ADF navigation?",
        "expected_keywords": ["ndb", "adf", "coastal refraction", "night effect"],
        "expected_source": "Radio Navigation"
    },
    {
        "id": 39,
        "subject": "Radio Navigation",
        "question": "What is the difference between Primary Surveillance Radar and Secondary Surveillance Radar?",
        "expected_keywords": ["primary radar", "secondary radar", "transponder", "interrogation"],
        "expected_source": "Radio Navigation"
    },
    {
        "id": 40,
        "subject": "Radio Navigation",
        "question": "How does GPS RAIM Receiver Autonomous Integrity Monitoring detect satellite anomalies?",
        "expected_keywords": ["gps", "raim", "satellite", "integrity"],
        "expected_source": "Radio Navigation"
    },

    # --- Aircraft General Knowledge: Airframes, Systems, Electrics & Powerplant ---
    {
        "id": 41,
        "subject": "Airframes and Systems",
        "question": "How does a Fly-by-Wire flight control system operate with hydraulic actuators?",
        "expected_keywords": ["fly by wire", "actuator", "control", "servo"],
        "expected_source": "Airframes"
    },
    {
        "id": 42,
        "subject": "Airframes and Systems",
        "question": "What is the function of a hydraulic accumulator and nitrogen pre-charge in aircraft hydraulic systems?",
        "expected_keywords": ["accumulator", "hydraulic", "nitrogen", "pressure"],
        "expected_source": "Airframes"
    },
    {
        "id": 43,
        "subject": "Powerplant",
        "question": "What causes carburetor icing in piston aircraft engines and what happens when carb heat is applied?",
        "expected_keywords": ["heat", "icing", "ice", "engine"],
        "expected_source": "Powerplant"
    },
    {
        "id": 44,
        "subject": "Powerplant",
        "question": "Why do aero-engine magnetos operate independently of the aircraft battery and electrical system?",
        "expected_keywords": ["magneto", "ignition", "spark", "independent"],
        "expected_source": "Powerplant"
    },
    {
        "id": 45,
        "subject": "Powerplant",
        "question": "What is the difference between high bypass and low bypass turbofan engines in propulsive efficiency?",
        "expected_keywords": ["bypass ratio", "turbofan", "efficiency", "thrust"],
        "expected_source": "Powerplant"
    },
    {
        "id": 46,
        "subject": "Aircraft Electrics",
        "question": "What is thermal runaway in aircraft Nickel Cadmium Ni-Cd batteries and how is it prevented?",
        "expected_keywords": ["thermal runaway", "battery", "nickel cadmium", "temperature"],
        "expected_source": "Electrics"
    },

    # --- Radio Telephony & RTR(A) ---
    {
        "id": 47,
        "subject": "Radio Telephony",
        "question": "What is the standard format and transmission components of an aeronautical MAYDAY distress message?",
        "expected_keywords": ["mayday", "distress", "callsign", "position"],
        "expected_source": "Radio Telephony"
    },
    {
        "id": 48,
        "subject": "Radio Telephony",
        "question": "What is the urgency signal PAN PAN and when should a pilot transmit PAN PAN instead of MAYDAY?",
        "expected_keywords": ["pan pan", "urgency", "safety", "condition"],
        "expected_source": "Radio Telephony"
    },
    {
        "id": 49,
        "subject": "Radio Telephony",
        "question": "What are the mandatory readback items for pilots receiving ATC air traffic control clearances?",
        "expected_keywords": ["readback", "clearance", "runway", "altimeter"],
        "expected_source": "Radio Telephony"
    },
    {
        "id": 50,
        "subject": "Radio Telephony",
        "question": "What is the radio communication failure procedure under IFR in IMC instrument conditions?",
        "expected_keywords": ["communication failure", "radio failure", "7600", "ifr"],
        "expected_source": "Radio Telephony"
    }
]

def run_50_question_benchmark():
    print(f"Starting 50-Question Source Book QA & Evaluation Benchmark...", flush=True)
    results = []
    failures = []
    t_start = time.time()

    for item in TEST_50_QUESTIONS:
        q_id = item["id"]
        q_subj = item["subject"]
        q_text = item["question"]
        expected_kws = item["expected_keywords"]
        expected_src = item["expected_source"]

        t0 = time.time()
        ans_data = ai_engine.answer_query(q_text)
        latency_ms = (time.time() - t0) * 1000

        answer_text = ans_data.get("answer", "")
        answer_lower = answer_text.lower()

        # Check keyword matches
        matched_kws = [kw for kw in expected_kws if kw.lower() in answer_lower]
        kw_ratio = len(matched_kws) / len(expected_kws) if expected_kws else 1.0

        # Check source citation presence
        has_citations = "Referenced DGCA Textbooks" in answer_text or expected_src.lower() in answer_lower
        
        # Check if greeting hijacked this query
        is_hijacked_greeting = "Welcome to **Airborne Aviation Academy**" in answer_text

        # Evaluate pass/fail: At least 40% keyword match and not hijacked
        passed = (kw_ratio >= 0.40 or len(matched_kws) >= 2) and not is_hijacked_greeting

        record = {
            "id": q_id,
            "subject": q_subj,
            "question": q_text,
            "matched_keywords": matched_kws,
            "keyword_ratio": round(kw_ratio, 2),
            "passed": passed,
            "is_hijacked_greeting": is_hijacked_greeting,
            "has_citations": has_citations,
            "latency_ms": round(latency_ms, 2),
            "answer_preview": answer_text[:160].replace("\n", " ")
        }
        results.append(record)

        if not passed:
            failures.append(record)
            print(f"[FAIL] Q{q_id:02d} ({q_subj}): {q_text[:60]}... -> Ratio: {kw_ratio:.2f}, Hijacked: {is_hijacked_greeting}", flush=True)
        else:
            print(f"[PASS] Q{q_id:02d} ({q_subj}): {q_text[:60]}... -> Latency: {latency_ms:.1f}ms", flush=True)

    elapsed = time.time() - t_start
    passed_count = len(results) - len(failures)
    pass_rate = (passed_count / len(results)) * 100

    report = {
        "total_questions": len(results),
        "passed": passed_count,
        "failed": len(failures),
        "pass_rate": round(pass_rate, 2),
        "total_time_seconds": round(elapsed, 2),
        "failures": failures,
        "details": results
    }

    with open("data/benchmark_50_results.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*60)
    print(f"BENCHMARK COMPLETE: {passed_count}/{len(results)} Passed ({pass_rate:.1f}%) in {elapsed:.2f}s")
    print(f"Failed Questions: {len(failures)}")
    print("="*60)
    return report

if __name__ == "__main__":
    run_50_question_benchmark()
