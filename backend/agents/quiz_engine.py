import re
from typing import Dict, Any, List, Optional

DGCA_QUIZ_BANK = [
    {
        "id": "pof_stall_turn",
        "subject": "Principles of Flight",
        "keywords": ["stall", "angle of attack", "turn", "load factor", "bank"],
        "question": "What happens to the stalling speed of an aircraft as the bank angle increases in a coordinated level turn?",
        "options": [
            "A) Stalling speed increases",
            "B) Stalling speed decreases",
            "C) Stalling speed remains unaffected",
            "D) Stalling speed depends only on engine thrust"
        ],
        "correct_option": "A",
        "explanation": "In a level banked turn, the load factor (n) increases according to n = 1 / cos(bank angle). Stalling speed in a turn increases proportionally to the square root of the load factor: Vs_turn = Vs * sqrt(n). At a 60° bank turn (n = 2), stalling speed increases by 41%.",
        "source": "Principles of Flight: Oxford Aviation Academy (Page 218)"
    },
    {
        "id": "met_altimeter_qnh",
        "subject": "Aviation Meteorology",
        "keywords": ["altimeter", "qnh", "qfe", "pressure", "subscale"],
        "question": "When flying from an area of high pressure into an area of low pressure without resetting the altimeter subscale, the altimeter will indicate:",
        "options": [
            "A) Higher than true altitude ('High to low, look out below')",
            "B) Lower than true altitude",
            "C) The correct true altitude",
            "D) Zero altitude"
        ],
        "correct_option": "A",
        "explanation": "When flying from high pressure to low pressure without adjusting the altimeter, the pressure levels sink toward the ground. The altimeter registers lower pressure as higher altitude, causing the aircraft to fly dangerously lower than indicated ('High to Low, Look Out Below').",
        "source": "Aviation Meteorology: Oxford Aviation Academy (Page 52)"
    },
    {
        "id": "regs_head_on",
        "subject": "Air Regulations",
        "keywords": ["right of way", "head on", "converging", "rules of the air"],
        "question": "When two power-driven aircraft are approaching head-on or approximately so, each aircraft must:",
        "options": [
            "A) Alter heading to the right",
            "B) Alter heading to the left",
            "C) Climb immediately",
            "D) Give way to the faster aircraft"
        ],
        "correct_option": "A",
        "explanation": "Under ICAO Annex 2 and DGCA Aircraft Rules 1937 (Rule 68), when two aircraft are approaching head-on, each shall alter its heading to the right to maintain safe separation.",
        "source": "Air Regulations: RK Bali 15th Edition (Rules of the Air, Rule 68)"
    },
    {
        "id": "nav_1_in_60",
        "subject": "General Navigation",
        "keywords": ["1 in 60", "track error", "closing angle", "drift"],
        "question": "Using the 1-in-60 rule, if an aircraft has flown 60 Nautical Miles and is found 3 NM off track, what is the Track Error Angle (TEA)?",
        "options": [
            "A) 3° Track Error",
            "B) 6° Track Error",
            "C) 1° Track Error",
            "D) 12° Track Error"
        ],
        "correct_option": "A",
        "explanation": "The 1 in 60 rule states: Track Error Angle (TEA) = (Distance Off Track * 60) / Distance Flown. Here, (3 NM * 60) / 60 NM = 3°.",
        "source": "General Navigation: Oxford Aviation Academy (Page 84)"
    },
    {
        "id": "nav_kepler_perihelion",
        "subject": "General Navigation",
        "keywords": ["perihelion", "aphelion", "kepler", "orbit", "earth orbit", "elliptical orbit"],
        "question": "When does perihelion occur, and what is the relative orbital speed of Earth at this point?",
        "options": [
            "A) Early January (~Jan 3-4); orbital speed is fastest",
            "B) Early July (~July 3-4); orbital speed is slowest",
            "C) Mid March at spring equinox; orbital speed is constant",
            "D) Late June at summer solstice; orbital speed is slowest"
        ],
        "correct_option": "A",
        "explanation": "Under Kepler's First and Second Laws, Earth travels in an elliptical orbit around the Sun. At 'perihelion' (closest distance to the Sun, approx 147 million km), which occurs in early January (~Jan 3-4), the radius vector is shortest and the orbital speed is fastest. At 'aphelion' (furthest distance, early July), orbital speed is slowest.",
        "source": "Air Navigation: General Navigation (Page 416, Chapter 25: Time)"
    },
    {
        "id": "pwr_carb_icing",
        "subject": "Powerplant",
        "keywords": ["carburetor", "carburettor", "carb heat", "ice", "rpm"],
        "question": "When applying Carburetor Heat to clear carburetor icing in a fixed-pitch propeller piston engine, what is the initial RPM indication?",
        "options": [
            "A) Immediate small drop in RPM",
            "B) Immediate sharp increase in RPM",
            "C) Constant RPM with rising oil pressure",
            "D) Immediate engine flameout"
        ],
        "correct_option": "A",
        "explanation": "Carburetor heat introduces warm, less-dense air into the induction system, causing an immediate initial drop in RPM due to a richer mixture. As ice melts and clears, RPM then steadily rises higher than the original value.",
        "source": "Powerplant: Oxford Aviation Academy (Page 142)"
    },
    {
        "id": "rt_emergency_squawk",
        "subject": "Radio Telephony",
        "keywords": ["mayday", "pan pan", "squawk", "7700", "7500", "7600", "distress"],
        "question": "What is the standard ICAO SSR transponder squawk code set by pilots during an in-flight distress emergency?",
        "options": [
            "A) Squawk 7700",
            "B) Squawk 7500",
            "C) Squawk 7600",
            "D) Squawk 7000"
        ],
        "correct_option": "A",
        "explanation": "Squawk 7700 denotes General Distress/Emergency. (Squawk 7500 denotes Hijacking/Unlawful Interference; Squawk 7600 denotes Radio Communication Failure).",
        "source": "Radio Telephony: RTR(A) & ICAO Annex 10 Communications"
    }
]

class DGCAQuizEngine:
    """
    DGCA Pariksha Practice Quiz Engine (EduBot Interactive Learning Pattern).
    Attaches context-aware CBT multiple-choice self-assessment questions to
    theoretical explanations and evaluates cadet responses.
    """
    def __init__(self, bank: List[Dict[str, Any]] = DGCA_QUIZ_BANK):
        self.bank = bank
        self.last_quiz: Optional[Dict[str, Any]] = None

    def match_quiz_for_query(self, query: str, subject: Optional[str] = None) -> Optional[Dict[str, Any]]:
        lower = query.lower()
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', lower))

        best_quiz = None
        max_score = 0
        for q in self.bank:
            score = len(tokens & set(q["keywords"]))
            if subject and q["subject"].lower() in subject.lower():
                score += 2
            if score > max_score and score >= 2:
                max_score = score
                best_quiz = q

        if best_quiz:
            self.last_quiz = best_quiz
        return best_quiz

    def is_quiz_answer_submission(self, message: str) -> Optional[Dict[str, Any]]:
        """Detects if message is a response to a previously asked quiz question"""
        lower = message.strip().lower()
        # Patterns like: "Option A", "A) Stalling speed", "Option B", "A", "B", etc.
        m = re.match(r'^(?:option\s+)?([a-d])\b', lower)
        if not m:
            return None

        chosen_letter = m.group(1).upper()

        # 1. Check if specific keywords or option text match any quiz in the bank
        matching_quiz = None
        for q in self.bank:
            if any(k in lower for k in q["keywords"]):
                matching_quiz = q
                break
            for opt in q["options"]:
                opt_snippet = opt[3:].strip().lower()
                if len(opt_snippet) > 4 and opt_snippet[:15] in lower:
                    matching_quiz = q
                    break
            if matching_quiz:
                break

        # 2. Fall back to the most recently asked quiz if available
        if not matching_quiz:
            matching_quiz = self.last_quiz or self.bank[0]

        is_correct = (chosen_letter == matching_quiz["correct_option"])
        return {
            "is_submission": True,
            "chosen": chosen_letter,
            "is_correct": is_correct,
            "question": matching_quiz["question"],
            "correct_option": matching_quiz["correct_option"],
            "explanation": matching_quiz["explanation"],
            "source": matching_quiz["source"]
        }

quiz_engine = DGCAQuizEngine()
