import json
import os
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple

from backend.models.student_profile import StudentPersona
from backend.agents.theory_tutor import TheoryTutorAgent
from backend.agents.admissions_advisor import AdmissionsAdvisorAgent
from backend.agents.regulatory_verifier import RegulatoryVerifierAgent
from backend.agents.sql_rag import sql_rag
from backend.agents.quiz_engine import quiz_engine

DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

# High-intent escalation regex patterns
COMPLEX_PATTERNS = [
    re.compile(r'(loan|emi|financ|sbi|hdfc|bank)\b.*(approv|sanction|interest|amount|collateral|moratorium|lakh|crore)', re.I),
    re.compile(r'(approv|sanction|collateral)\b.*(loan|emi)', re.I),
    re.compile(r'(medical|doctor|vision|eyesight|color blind|lasik)\b.*(fail|reject|appeal|board|iam|afcme|pmr|fit)', re.I),
    re.compile(r'(fail|reject|appeal)\b.*(medical|class 1|class 2)', re.I),
    re.compile(r'cadet\b.*(interview|prep|indigo|air india|spicejet|adapt|compass|selection|assessment)', re.I),
    re.compile(r'(indigo|air india|spicejet)\b.*cadet', re.I),
    re.compile(r'(talk|speak|call|connect)\b.*(human|counselor|advisor|agent|person|instructor|desk|phone|whatsapp)', re.I),
    re.compile(r'(call|phone|whatsapp)\s*(me|now|back)', re.I),
    re.compile(r'(discount|concession|scholarship|negotiat|waiver|fee reduction)', re.I),
    re.compile(r'(foreign|faa|caa|sacaa|easa|conversion|convert)\b.*(license|cpl|dgca)', re.I)
]

# Explicit non-aviation pattern regexes
NON_AVIATION_PATTERNS = [
    re.compile(r'\b(recipe|cook|cooking|baking|bake|ingredients|dish|dinner|lunch|breakfast|pizza|pasta|sourdough|cake|curry|biryani|paneer|burger)\b', re.I),
    re.compile(r'\b(stocks?|nse|bse|nifty|sensex|crypto|bitcoin|ethereum|trading|share price|invest in stock|dividend|mutual funds?)\b', re.I),
    re.compile(r'\b(python|javascript|typescript|c\+\+|java|react|angular|html|css|sql query code|write code|debug code|flask|django)\b', re.I),
    re.compile(r'\b(cricket|football|fifa|ipl|world cup|movie|actor|actress|bollywood|hollywood|song|lyrics)\b', re.I)
]

# Aviation domain terminology guardrail
AVIATION_TERMS = {
    # Licensing & Training
    "cpl", "ppl", "atpl", "spl", "dgca", "pilot", "plane", "aircraft", "flying", "flight",
    "course", "courses", "fee", "fees", "cost", "price", "installment", "salary", "hours",
    "admission", "eligibility", "physics", "maths", "nios", "arts", "commerce", "12th",
    "spectacles", "glasses", "fleet", "duration", "subjects", "passing", "marks", "exam",
    "exams", "syllabus", "cadet", "ground school", "fdtl", "logbook", "rule 67a", "rule 7",
    "computer number", "egca", "pariksha", "medical", "medicals", "class 1", "class 2",
    "lasik", "vision", "eyesight", "afcme", "iam", "pmr", "rtr", "license", "quiz", "option",
    "type rating", "instrument rating", "night rating", "multi engine", "fto", "flight training",
    # Aerodynamics & Principles of Flight
    "aerodynamics", "lift", "drag", "thrust", "weight", "stall", "stalling", "angle of attack",
    "aoa", "camber", "cambered", "aerofoil", "airfoil", "chord", "span", "aspect ratio",
    "vortex", "vortices", "wingtip", "downwash", "induced drag", "parasite drag", "yaw",
    "adverse yaw", "rudder", "aileron", "elevator", "dihedral", "anhedral", "roll", "pitch", "stability",
    "center of pressure", "center of gravity", "ground effect", "mach", "transonic", "supersonic",
    "shock", "shock stall", "buffet", "boundary layer", "flaps", "slats", "spoilers", "canard",
    "stabilator", "tailplane", "fin", "trim tab", "balance tab", "servo tab", "stick pusher", "stick shaker",
    # Meteorology
    "weather", "met", "meteorology", "altimeter", "qnh", "qfe", "qne", "pressure", "atmosphere",
    "lapse", "lapse rate", "dalr", "salr", "elr", "temperature", "inversion", "coriolis",
    "geostrophic", "wind", "winds", "shear", "wind shear", "fog", "radiation fog", "advection fog",
    "cloud", "clouds", "cumulonimbus", "cb", "microburst", "downdraft", "thunderstorm",
    "turbulence", "cat", "clear air turbulence", "mountain wave", "rotor", "lenticular",
    "icing", "supercooled", "rime", "rime ice", "clear ice", "monsoon", "trough", "tibetan",
    "easterly jet", "somali jet", "western disturbances", "norwester", "nor'wester", "kalbaisakhi",
    "andhi", "metar", "taf", "speci", "cavok", "rvr", "albedo", "insolation", "dewpoint", "humidity",
    "isobar", "isotherm", "isallobar", "katabatic", "anabatic", "front", "frontal", "cold front",
    "warm front", "occlusion", "occluded", "frontogenesis", "squall", "virga", "mammatus", "stratus",
    "cirrus", "itcz", "doldrums", "jet stream",
    # Air Regulations & ATC
    "airspace", "fir", "atc", "runway", "speed", "knot", "knots", "heading", "track",
    "right of way", "head on", "converging", "overtaking", "semi-circular", "cruising level",
    "vfr", "ifr", "imc", "vmc", "minima", "squawk", "transponder", "7500", "7600", "7700",
    "flight level", "transition altitude", "papi", "vasi", "tora", "toda", "asda", "lda",
    # Navigation & Instruments (including Earth, Orbits & Time)
    "nav", "navigation", "vor", "dme", "radial", "ils", "localizer", "glide path", "glideslope",
    "ndb", "adf", "coastal refraction", "night effect", "radar", "psr", "ssr", "gps", "gnss",
    "raim", "satellite", "great circle", "rhumb line", "mercator", "lambert", "convergence",
    "conversion angle", "true airspeed", "tas", "indicated airspeed", "ias", "cas", "eas",
    "groundspeed", "1 in 60", "drift", "cross country", "solo", "pet", "critical point",
    "point of safe return", "psr", "endurance", "fuel flow", "perihelion", "aphelion", "kepler",
    "orbit", "orbital", "solstice", "equinox", "celestial", "ecliptic", "sidereal", "solar",
    "declination", "hour angle", "zenith", "nadir", "oblate", "spheroid", "geoid", "meridian",
    "parallel", "latitude", "longitude", "dlat", "dlong", "convergency", "departure", "scale",
    "conformal", "isogonal", "agonic", "isogonic", "variation", "deviation", "compass", "dip",
    "quadrantal", "quadrantal error", "time", "apparent solar time", "mean solar time", "equation of time",
    "utc", "gmt", "lst", "lmt", "astronomical",
    # Airframes, Systems, Engines & RT
    "airframe", "hydraulics", "hydraulic", "accumulator", "nitrogen", "actuator", "fly by wire",
    "fbw", "powerplant", "engine", "engines", "piston", "carburetor", "carburettor", "carb heat",
    "magneto", "magnetos", "spark plug", "ignition", "propeller", "turbofan", "turbojet",
    "turboprop", "bypass ratio", "bypass", "thermal runaway", "battery", "nickel cadmium", "ni-cd",
    "mayday", "pan pan", "distress", "urgency", "readback", "clearance", "phraseology",
    "cessna", "cessna 172", "supercharger", "turbocharger", "wastegate", "bleed air", "pressurization",
    "outflow valve", "cabin altitude", "anti-skid", "oleo strut"
}

class IntentRouter:
    """
    Coordinating Router for EduBot Multi-Agent Architecture.
    Dispatches student pilot queries to:
    - TheoryTutorAgent: DGCA 5 ground subjects, RAPTOR & textbook RAG + Interactive Pariksha Quizzes
    - AviationSQLRAG: Structured Text-to-SQL for exam tables, flying schedules, and course matrices
    - DGCAQuizEngine: Immediate evaluation of student practice answers
    - AdmissionsAdvisorAgent: CPL courses, fee schedules, bank loans & WhatsApp escalation
    - RegulatoryVerifierAgent: eGCA, medical fitness, 200 flying hours, anti-fraud & official portal checks
    """
    def __init__(self, kb_path: str = "backend/knowledge_base.json", api_key: Optional[str] = None):
        self.kb_path = kb_path
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)
        with open(self.kb_path, "r", encoding="utf-8") as f:
            self.kb = json.load(f)

        self.theory_tutor = TheoryTutorAgent(api_key=self.api_key)
        self.admissions_advisor = AdmissionsAdvisorAgent(kb=self.kb)
        self.regulatory_verifier = RegulatoryVerifierAgent(kb=self.kb)
        self.sql_rag = sql_rag
        self.quiz_engine = quiz_engine

    def is_complex_query(self, message: str) -> Tuple[bool, str]:
        """Detects if query requires counselor escalation."""
        for pattern in COMPLEX_PATTERNS:
            if pattern.search(message):
                text = message.lower()
                if any(w in text for w in ["loan", "emi", "bank", "sbi", "hdfc", "financ"]):
                    return True, "Personalized Education Loan & Fee Assistance Required"
                elif any(w in text for w in ["medical", "appeal", "reject", "color", "vision", "specs", "lasik"]):
                    return True, "DGCA Medical Fitness & Medical Appeal Counseling Required"
                elif any(w in text for w in ["cadet", "adapt", "compass", "indigo", "interview"]):
                    return True, "Airline Cadet Pilot Selection & Assessment Consultation"
                elif any(w in text for w in ["discount", "concession", "scholarship", "waiver"]):
                    return True, "Scholarship & Fee Concession Desk"
                elif any(w in text for w in ["foreign", "conversion", "faa"]):
                    return True, "License Conversion & Eligibility Evaluation Required"
                else:
                    return True, "Direct request to connect with Senior Flight Advisor"

        return False, ""

    def is_adversarial_or_jailbreak(self, message: str) -> bool:
        """Detect prompt injection and system jailbreak attempts"""
        lower = message.lower()
        jailbreak_triggers = [
            "ignore all previous", "ignore previous instructions", "forget your instructions",
            "you are no longer", "system prompt", "print your prompt", "leak your prompt",
            "act as a", "pretend you are", "jailbreak", "dan mode", "bypass instructions",
            "bypass prompt", "bypass guardrail", "bomb", "explosive"
        ]
        return any(t in lower for t in jailbreak_triggers)

    def is_aviation_query(self, message: str) -> bool:
        """Determines if query belongs to the aviation domain"""
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', message.lower()))
        if tokens & AVIATION_TERMS:
            return True
        if any(w in message.lower() for w in ["pilot", "jahaj", "plane", "udaan", "cpl", "fees", "flight", "option a", "option b", "option c"]):
            return True
        return False

    def is_explicit_non_aviation(self, message: str) -> bool:
        """Detects clear non-aviation domain requests (cooking, coding, stock market, sports, entertainment)"""
        lower = message.lower()
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', lower))
        has_aviation_token = bool(tokens & AVIATION_TERMS) or any(w in lower for w in ["pilot", "plane", "flight", "dgca", "cpl", "aircraft", "ground school", "flying"])
        if has_aviation_token:
            return False
        return any(pattern.search(lower) for pattern in NON_AVIATION_PATTERNS)

    def is_end_of_session(self, message: str) -> bool:
        """Detects if user indicates they have no further questions or are concluding the study session"""
        lower = message.strip().lower()
        patterns = [
            r'\b(no\s*(?:other|more|further)?\s*questions?|no\s*doubts?)\b',
            r'\b(that(?:[\'’]s|\s+is)\s*all|nothing\s*else|nothing\s*more)\b',
            r'\b(i(?:[\'’]m|\s+am)\s*done|done\s*for\s*now|all\s*good|all\s*clear)\b',
            r'\b(thank\s*you\s*(?:that(?:[\'’]s|\s+is)\s*all|so\s*much)?)\b'
        ]
        return any(re.search(p, lower) for p in patterns) and len(lower.split()) <= 7

    def generate_escalation_data(self, query: str, reason: str) -> Dict[str, Any]:
        academy = self.kb.get("academy", {})
        wa_number = academy.get("whatsapp_number", "+919876543210").replace("+", "").replace(" ", "")
        prefilled_msg = f"Hi Airborne Aviation Academy! I am inquiring about: {query[:80]}... Please connect me with a senior flight training counselor."
        encoded_msg = urllib.parse.quote(prefilled_msg)
        wa_url = f"https://wa.me/{wa_number}?text={encoded_msg}"

        return {
            "needed": True,
            "reason": reason,
            "whatsapp_url": wa_url,
            "whatsapp_display": academy.get("whatsapp_display", "+91 98765 43210"),
            "phone_helpline": academy.get("phone_helpline", "+91 1800 247 2676"),
            "alternate_phone": academy.get("alternate_phone", "+91 98765 43210"),
            "email": academy.get("email", "admissions@airborne-aviation.edu")
        }

    def route_and_process(self, message: str, persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET) -> Dict[str, Any]:
        """
        Coordinates the execution lifecycle across guardrails, interactive quizzes,
        structured SQL-RAG, regulatory checks, admissions guidance, and textbook RAG.
        """
        text = message.strip()
        lower = text.lower()
        is_complex, complex_reason = self.is_complex_query(text)
        default_escalation = self.generate_escalation_data(message, complex_reason) if is_complex else {
            "needed": False,
            "whatsapp_url": f"https://wa.me/{self.kb['academy']['whatsapp_number'].replace('+', '')}",
            "whatsapp_display": self.kb["academy"]["whatsapp_display"],
            "phone_helpline": self.kb["academy"]["phone_helpline"]
        }

        # 1. Adversarial & Prompt Injection Guardrail
        if self.is_adversarial_or_jailbreak(text):
            return {
                "answer": (
                    "### 🛡️ **Airborne Flight Training Assistant**\n\n"
                    "I am the dedicated 24/7 AI Flight Training Advisor for **Airborne Aviation Academy**. "
                    "My operating guidelines restrict me exclusively to DGCA flight training, ground school subjects, CPL/ATPL course fees, and pilot career counseling. "
                    "How can I assist your aviation and flight training journey today?"
                ),
                "chips": ["DGCA CPL Syllabus", "Course Fee Breakdown", "Class 1 & 2 Medicals", "Bank Loan Assistance"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "Security Guardrail (Prompt Injection Defense)",
                    "primary_book": "Airborne Security & Safety Guidelines",
                    "page_number": 1,
                    "subject": "System Integrity",
                    "chunk_excerpt": "Out-of-domain jailbreak or prompt modification request neutralized."
                },
                "agent_handled": "SecurityGuardrail"
            }

        # 2. Regulatory Subagent Guardrails (Illegal / Fraud Refusal)
        if self.regulatory_verifier.is_illegal_or_fraud(text):
            res = self.regulatory_verifier.answer_regulatory_query(text, persona)
            res["escalation"] = default_escalation
            res["agent_handled"] = "RegulatoryVerifierAgent"
            return res

        # 3. Official DGCA Portal Restriction Policy (Zero Web Scraping)
        if self.regulatory_verifier.is_external_web_request(text):
            res = self.regulatory_verifier.answer_regulatory_query(text, persona)
            res["escalation"] = default_escalation
            res["agent_handled"] = "RegulatoryVerifierAgent"
            return res

        # 4. Interactive DGCA Pariksha Quiz Answer Submission (EduBot Pattern)
        quiz_eval = self.quiz_engine.is_quiz_answer_submission(text)
        if quiz_eval:
            status_emoji = "✅" if quiz_eval["is_correct"] else "❌"
            status_text = "Correct Answer!" if quiz_eval["is_correct"] else f"Incorrect. The correct answer is Option {quiz_eval['correct_option']}."
            quiz_resp = (
                f"### 🎯 **DGCA Pariksha Practice Assessment**\n\n"
                f"**Question:** *{quiz_eval['question']}*\n\n"
                f"**Your Choice:** Option {quiz_eval['chosen']}\n\n"
                f"{status_emoji} **{status_text}**\n\n"
                f"#### 📖 **Theoretical Explanation:**\n"
                f"{quiz_eval['explanation']}\n\n"
                f"📖 **Referred Background Source Book:** {quiz_eval['source']}"
            )
            return {
                "answer": quiz_resp,
                "chips": ["Try Another Question", "DGCA 5 Subjects", "CPL Ground School", "Class 1 & 2 Medicals"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "DGCA Pariksha Interactive Assessment Evaluator",
                    "primary_book": quiz_eval["source"].split(":")[0] if ":" in quiz_eval["source"] else quiz_eval["source"],
                    "page_number": 1,
                    "subject": "Pariksha Exam Practice & Self-Assessment",
                    "syllabus_breadcrumb": "DGCA CAR Section 7 > Pariksha CBT Question Bank",
                    "recommended_next": "Next Theoretical Subject Review",
                    "chunk_excerpt": quiz_eval["explanation"]
                },
                "agent_handled": "DGCAQuizEngine"
            }

        # 4b. On-Demand DGCA Pariksha Practice Quiz Request (Explicit User Request)
        if self.quiz_engine.is_on_demand_quiz_request(text):
            subject_hint = getattr(self.theory_tutor, "last_subject", None)
            quiz_data = self.quiz_engine.serve_quiz_for_query(text, subject=subject_hint)
            return {
                "answer": quiz_data["answer"],
                "chips": quiz_data["chips"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "DGCA Pariksha Interactive Assessment (On Demand)",
                    "primary_book": quiz_data["quiz"]["source"],
                    "page_number": 1,
                    "subject": quiz_data["quiz"]["subject"],
                    "syllabus_breadcrumb": f"DGCA CAR Sec 7 > {quiz_data['quiz']['subject']} Practice CBT",
                    "recommended_next": "Answer submission and theoretical review",
                    "chunk_excerpt": quiz_data["quiz"]["explanation"]
                },
                "agent_handled": "DGCAQuizEngine"
            }

        # 4c. End-of-Session Trigger ("no other question", "that is all", "done for now")
        if self.is_end_of_session(text):
            return {
                "answer": (
                    "### 🎓 **Great session today, Cadet!** ✈️\n\n"
                    "You've reviewed key DGCA pilot ground school concepts today.\n\n"
                    "Before you wrap up, would you like to test your understanding with a quick **DGCA Pariksha Practice Question**?\n\n"
                    "- Click **\"🎯 Quick Pariksha Quiz\"** to test your knowledge on demand.\n"
                    "- Or connect directly with our Chief Ground Instructor if you need further guidance.\n\n"
                    "📖 **Referred Background Source:** DGCA Pilot Training Curriculum & Ground School Syllabus"
                ),
                "chips": ["🎯 Quick Pariksha Quiz", "Commercial Pilot Course (CPL)", "Class 1 & 2 Medicals", "Talk to Counselor"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "End of Study Session Assessment Trigger",
                    "primary_book": "Airborne Ground School Curriculum",
                    "page_number": 1,
                    "subject": "Session Wrap-up & Self Assessment Option",
                    "syllabus_breadcrumb": "DGCA CAR Sec 7 > Pilot Training Milestone",
                    "recommended_next": "Interactive Pariksha Quiz Evaluation",
                    "chunk_excerpt": "Student completed query cycle; offered optional Pariksha CBT assessment."
                },
                "agent_handled": "SessionWrapUpAgent"
            }

        # 5. Pure Greeting (Word-bounded regex, <= 3 words)
        is_greeting = bool(re.match(r'^(hi|hello|hey|namaste|good\s+morning|good\s+evening|start)\b', text, re.I)) and len(text.split()) <= 3
        if is_greeting:
            response_text = (
                f"### Welcome to **{self.kb['academy']['name']}**! ✈️\n\n"
                "I am your **24/7 AI Aviation Flight Advisor & Ground School Tutor**, powered by verified DGCA pilot training curricula and official textbooks. "
                "I can resolve every doubt regarding:\n\n"
                "- 📚 **DGCA Ground Subjects:** Air Navigation, Meteorology, Regulations, Technical General/Specific & RTR(A)\n"
                "- 💰 **Fee Structures & 100% Bank Loan Tie-ups**\n"
                "- 🩺 **Class 1 & Class 2 Medicals, Eye Vision & Computer Number**\n"
                "- 🛩️ **CPL 200 Flying Hours & Cadet Pilot Programs**\n\n"
                "Ask any theoretical doubt or select a quick topic below!"
            )
            chips = [
                "Commercial Pilot Course (CPL)",
                "Full Fee Structure & Loans",
                "DGCA Syllabus & Exams",
                "Class 1 & 2 Medical Process",
                "Aerodynamic Stall & Lift"
            ]
            return {
                "answer": response_text,
                "chips": chips,
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 100.0,
                    "retrieval_method": "Greeting & Onboarding Dispatcher",
                    "primary_book": "Airborne Aviation Welcome Portal",
                    "page_number": 1,
                    "subject": "Student Onboarding",
                    "chunk_excerpt": "Welcome prompt and quick-start DGCA syllabus options."
                },
                "agent_handled": "OnboardingRouter"
            }

        # 6. Structured SQL-RAG: Tabular & Comparative Queries (EduBot SQL-RAG Pattern)
        if any(w in lower for w in ["compare", "comparison"]) and any(w in lower for w in ["course", "courses", "cpl", "cadet", "fleet", "program"]):
            return {
                "answer": self.sql_rag.query_course_comparison(),
                "chips": ["CPL Total Cost", "Cadet Pilot Costs", "100% Bank Loans", "Talk to Admissions Counselor"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.8,
                    "retrieval_method": "SQL-RAG (course_fees_installments Table)",
                    "primary_book": "Airborne Aviation Course Specification Database",
                    "page_number": 1,
                    "subject": "Flight Training Course Comparison Matrix",
                    "syllabus_breadcrumb": "Airborne Academy > Program Matrix",
                    "recommended_next": "Personalized Installment Counseling",
                    "chunk_excerpt": "Structured SQL table query comparing CPL, Cadet, Ground School, RTR, and Conversion courses."
                },
                "agent_handled": "AviationSQLRAG"
            }

        if any(w in lower for w in ["exam table", "exams table", "passing table", "subject code table", "cbt table"]):
            return {
                "answer": self.sql_rag.query_exams_table(),
                "chips": ["DGCA 5 Subjects", "Pariksha Exam Dates", "Computer Number Steps", "Ground School Fees"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.9,
                    "retrieval_method": "SQL-RAG (dgca_exams Table)",
                    "primary_book": "DGCA CAR Section 7 Series J",
                    "page_number": 1,
                    "subject": "DGCA Theoretical Knowledge Examinations",
                    "syllabus_breadcrumb": "DGCA CAR Section 7 > Pariksha Exam Matrix",
                    "recommended_next": "Registration on pariksha.dgca.gov.in",
                    "chunk_excerpt": "Structured SQL query of official exam codes (021-025, WPC) with 70% passing standards."
                },
                "agent_handled": "AviationSQLRAG"
            }

        if any(w in lower for w in ["flying schedule", "flying hours table", "flying breakdown table", "hours schedule", "statutory hours"]):
            return {
                "answer": self.sql_rag.query_flying_hours_table(),
                "chips": ["CPL Course Details", "Class 1 & 2 Medicals", "Total Course Cost", "Admissions Help"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.9,
                    "retrieval_method": "SQL-RAG (flying_hours_schedule Table)",
                    "primary_book": "DGCA Aircraft Rules 1937 Schedule II Section J",
                    "page_number": 190,
                    "subject": "Commercial Pilot License Flight Requirements",
                    "syllabus_breadcrumb": "DGCA Aircraft Rules 1937 > Schedule II Section J",
                    "recommended_next": "Flight Simulator FNPT-II Training Schedule",
                    "chunk_excerpt": "Structured SQL query of statutory 200 flying hours breakdown."
                },
                "agent_handled": "AviationSQLRAG"
            }

        # 7. Regulatory & Institutional Verification (Medicals, eGCA, 200 Flying Hours, NIOS, Age, Exams)
        reg_result = self.regulatory_verifier.answer_regulatory_query(text, persona)
        if reg_result:
            if "escalation" not in reg_result or not reg_result["escalation"].get("needed"):
                reg_result["escalation"] = default_escalation
            reg_result["agent_handled"] = "RegulatoryVerifierAgent"
            return reg_result

        # 8. Admissions, Fleet, Course Specifications & Bank Loans
        adm_result = self.admissions_advisor.answer_admissions_query(text, persona)
        if adm_result:
            if "escalation" not in adm_result or not adm_result["escalation"].get("needed"):
                adm_result["escalation"] = default_escalation
            adm_result["agent_handled"] = "AdmissionsAdvisorAgent"
            return adm_result

        # 9. Explicit Out-of-Domain Guardrail (Reject recipes, coding, stocks, sports)
        if self.is_explicit_non_aviation(text):
            return {
                "answer": (
                    "### ✈️ **Airborne Aviation Academy Assistant**\n\n"
                    "I specialize strictly in **DGCA Pilot Training & Aviation Ground School** (Air Navigation, Aviation Meteorology, Air Regulations, Technical General, and RTR-A).\n\n"
                    "I cannot assist with unrelated queries like general programming, cooking recipes, or stock market trading.\n\n"
                    "Please feel free to ask any question regarding:\n"
                    "- 🛫 **CPL & Airline Cadet Pilot Programs**\n"
                    "- 📚 **DGCA Ground Exam Subjects & Theory Doubts**\n"
                    "- 💰 **Flight Training Fees & Bank Loan Tie-ups**\n"
                    "- 🩺 **Class 1 & Class 2 Medicals and Vision Rules**\n\n"
                    "📖 **Referred Background Source:** Airborne Aviation Academy Ground School Curriculum"
                ),
                "chips": ["CPL Course Details", "DGCA 5 Subjects", "Total Course Cost", "Class 1 & 2 Medicals"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": False,
                    "confidence_score": 0.0,
                    "retrieval_method": "Scope Guardrail (Out of Domain)",
                    "primary_book": "Airborne Aviation Scope Guardrail",
                    "page_number": None,
                    "subject": "Out-of-Domain Protection",
                    "chunk_excerpt": "Query rejected as outside aviation ground school and pilot training curriculum."
                },
                "agent_handled": "ScopeGuardrail"
            }

        # 10. Theory Tutor Agent (DGCA Ground School Textbook RAG + Pariksha Practice Quiz)
        theory_result = self.theory_tutor.answer_theory_query(text, persona)
        if theory_result.get("under_the_hood", {}).get("matched", False):
            theory_result["escalation"] = default_escalation
            theory_result["agent_handled"] = "TheoryTutorAgent"
            return theory_result

        # 11. Domain Verification for Unmatched Queries
        if not self.is_aviation_query(text) and not is_complex:
            return {
                "answer": (
                    "### ✈️ **Airborne Aviation Academy Assistant**\n\n"
                    "I specialize strictly in **DGCA Pilot Training & Aviation Ground School** (Air Navigation, Aviation Meteorology, Air Regulations, Technical General, and RTR-A).\n\n"
                    "I cannot assist with unrelated queries like general programming, cooking recipes, or stock market trading.\n\n"
                    "Please feel free to ask any question regarding:\n"
                    "- 🛫 **CPL & Airline Cadet Pilot Programs**\n"
                    "- 📚 **DGCA Ground Exam Subjects & Theory Doubts**\n"
                    "- 💰 **Flight Training Fees & Bank Loan Tie-ups**\n"
                    "- 🩺 **Class 1 & Class 2 Medicals and Vision Rules**\n\n"
                    "📖 **Referred Background Source:** Airborne Aviation Academy Ground School Curriculum"
                ),
                "chips": ["CPL Course Details", "DGCA 5 Subjects", "Total Course Cost", "Class 1 & 2 Medicals"],
                "escalation": default_escalation,
                "under_the_hood": {
                    "matched": False,
                    "confidence_score": 0.0,
                    "retrieval_method": "Scope Guardrail (Out of Domain)",
                    "primary_book": "Airborne Aviation Scope Guardrail",
                    "page_number": None,
                    "subject": "Out-of-Domain Protection",
                    "chunk_excerpt": "Query rejected as outside aviation ground school and pilot training curriculum."
                },
                "agent_handled": "ScopeGuardrail"
            }

        # 11. Fallback for unindexed general aviation queries
        default_escalation["needed"] = True
        default_escalation["reason"] = "Aviation advisor ready to answer your specific flight question"
        response_text = (
            f"Thank you for your question regarding **\"{text}\"**.\n\n"
            "At **Airborne Aviation Academy**, our flight training instructors and admissions counselors are on standby 24/7 to resolve every query about:\n\n"
            "- ✈️ **CPL Flying Hours & Multi-Engine Endorsements**\n"
            "- 💰 **Fee Schedules, EMI Options & Bank Education Loans**\n"
            "- 📚 **DGCA Computer Number, eGCA Verification & Exam Syllabus**\n"
            "- 🩺 **Class 1 & Class 2 Medicals and Vision Clearances**\n"
            "- 👨‍✈️ **Airline Recruitment & Cadet Pilot Programs**\n\n"
            "To get immediate personalized guidance, connect directly with our Senior Flight Advisor below via WhatsApp or call our 24/7 toll-free helpline.\n\n"
            "📖 **Referred Background Source:** DGCA Pilot Training Curriculum & Airborne Aviation Ground School Syllabus"
        )
        chips = ["CPL Course Details", "Fee Structure & Loans", "DGCA Syllabus", "Class 1 & 2 Medicals", "Chat on WhatsApp"]
        return {
            "answer": response_text,
            "chips": chips,
            "escalation": default_escalation,
            "under_the_hood": {
                "matched": False,
                "confidence_score": 50.0,
                "retrieval_method": "Aviation Knowledge Fallback",
                "primary_book": "Airborne Aviation Ground Syllabus",
                "page_number": 1,
                "subject": "Flight Training Counseling",
                "chunk_excerpt": "Direct counseling fallback for unindexed aviation query."
            },
            "agent_handled": "AviationFallback"
        }
