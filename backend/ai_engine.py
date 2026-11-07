import json
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, Any, List, Optional
from backend.rag_pipeline import rag_pipeline
from backend.models.student_profile import StudentPersona
from backend.agents.router import IntentRouter

DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Comprehensive regex patterns for high-intent complex escalations
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

# Core aviation terminology to guard against random false-positive RAG retrieval
AVIATION_TERMS = {
    # Licensing & Training
    "cpl", "ppl", "atpl", "spl", "dgca", "pilot", "plane", "aircraft", "flying", "flight",
    "course", "courses", "fee", "fees", "cost", "price", "installment", "salary", "hours",
    "admission", "eligibility", "physics", "maths", "nios", "arts", "commerce", "12th",
    "spectacles", "glasses", "fleet", "duration", "subjects", "passing", "marks", "exam",
    "exams", "syllabus", "cadet", "ground school", "fdtl", "logbook", "rule 67a", "rule 7",
    "computer number", "egca", "pariksha", "medical", "medicals", "class 1", "class 2",
    "lasik", "vision", "eyesight", "afcme", "iam", "pmr", "rtr", "license",
    # Aerodynamics & Principles of Flight
    "aerodynamics", "lift", "drag", "thrust", "weight", "stall", "stalling", "angle of attack",
    "aoa", "camber", "cambered", "aerofoil", "airfoil", "chord", "span", "aspect ratio",
    "vortex", "vortices", "wingtip", "downwash", "induced drag", "parasite drag", "yaw",
    "adverse yaw", "rudder", "aileron", "elevator", "dihedral", "roll", "pitch", "stability",
    "center of pressure", "center of gravity", "ground effect", "mach", "transonic", "supersonic",
    "shock", "shock stall", "buffet", "boundary layer", "flaps", "slats", "spoilers",
    # Meteorology
    "weather", "met", "meteorology", "altimeter", "qnh", "qfe", "qne", "pressure", "atmosphere",
    "lapse", "lapse rate", "dalr", "salr", "elr", "temperature", "inversion", "coriolis",
    "geostrophic", "wind", "winds", "shear", "wind shear", "fog", "radiation fog", "advection fog",
    "cloud", "clouds", "cumulonimbus", "cb", "microburst", "downdraft", "thunderstorm",
    "turbulence", "cat", "clear air turbulence", "mountain wave", "rotor", "lenticular",
    "icing", "supercooled", "rime", "rime ice", "clear ice", "monsoon", "trough", "tibetan",
    "easterly jet", "somali jet", "western disturbances", "norwester", "nor'wester", "kalbaisakhi",
    "andhi", "metar", "taf", "speci", "cavok", "rvr",
    # Air Regulations & ATC
    "airspace", "fir", "atc", "runway", "speed", "knot", "knots", "heading", "track",
    "right of way", "head on", "converging", "overtaking", "semi-circular", "cruising level",
    "vfr", "ifr", "imc", "vmc", "minima", "squawk", "transponder", "7500", "7600", "7700",
    # Navigation & Instruments
    "nav", "navigation", "vor", "dme", "radial", "ils", "localizer", "glide path", "glideslope",
    "ndb", "adf", "coastal refraction", "night effect", "radar", "psr", "ssr", "gps", "gnss",
    "raim", "satellite", "great circle", "rhumb line", "mercator", "lambert", "convergence",
    "conversion angle", "true airspeed", "tas", "indicated airspeed", "ias", "cas", "eas",
    "groundspeed", "1 in 60", "drift", "cross country", "solo", "pet", "critical point",
    "psr", "point of safe return", "endurance", "fuel flow",
    # Airframes, Systems, Engines & RT
    "airframe", "hydraulics", "hydraulic", "accumulator", "nitrogen", "actuator", "fly by wire",
    "fbw", "powerplant", "engine", "engines", "piston", "carburetor", "carb heat", "magneto",
    "magnetos", "spark plug", "ignition", "propeller", "turbofan", "turbojet", "turboprop",
    "bypass ratio", "bypass", "thermal runaway", "battery", "nickel cadmium", "ni-cd",
    "mayday", "pan pan", "distress", "urgency", "readback", "clearance", "phraseology",
    "cessna", "cessna 172", "multi-engine"
}

class AviationAIEngine:
    def __init__(self, kb_path: str = "backend/knowledge_base.json"):
        self.kb_path = kb_path
        self.kb = self._load_kb()
        self.api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)
        self.router = IntentRouter(kb_path=self.kb_path, api_key=self.api_key)

    def _load_kb(self) -> Dict[str, Any]:
        with open(self.kb_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def is_complex_query(self, message: str) -> tuple[bool, str]:
        """
        Detects if query requires escalation to human counselor / WhatsApp / Phone using flexible regex.
        Returns (is_complex, reason)
        """
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

    def is_illegal_or_fraud(self, message: str) -> bool:
        """Detect illegal requests such as fake licenses, bribes, or cheating medicals"""
        lower = message.lower()
        illegal_triggers = [
            "fake license", "fake cpl", "fake dgca", "bribe", "cheat sheet",
            "cheat the test", "bypass medical", "illegal license", "buy license",
            "without logging 200", "forge license", "pass the ishihara plates test"
        ]
        return any(t in lower for t in illegal_triggers)

    def is_external_web_request(self, message: str) -> bool:
        """Detect requests to scrape the web, browse arbitrary websites, or look outside official portals"""
        lower = message.lower()
        triggers = [
            "scrape", "web scrape", "scraping", "crawl", "browse the web", "search google",
            "search the web", "check online", "check other website", "check other websites",
            "search internet", "search other sites", "from another website"
        ]
        return any(t in lower for t in triggers)

    def is_aviation_query(self, message: str) -> bool:
        """Determines if query belongs to the aviation domain"""
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', message.lower()))
        if tokens & AVIATION_TERMS:
            return True
        # Check partial stems for Hindi/Hinglish (e.g. pilot, udaan, jahaj, hawai)
        if any(w in message.lower() for w in ["pilot", "jahaj", "plane", "udaan", "cpl", "fees", "flight"]):
            return True
        return False

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

    def generate_with_gemini(self, question: str, context_chunks: List[Dict[str, Any]]) -> Optional[str]:
        """Calls Gemini Flash REST API with retrieved DGCA textbook excerpts"""
        api_key = os.environ.get("GEMINI_API_KEY", self.api_key)
        if not api_key:
            return None

        formatted_context = "\n\n".join([
            f"--- [Textbook: {c['book_title']}, Page {c['page_number']}, Subject: {c['subject']}] ---\n{c['text']}"
            for c in context_chunks
        ])

        system_instruction = (
            "You are the Senior Flight Ground Instructor at Airborne Aviation Academy (DGCA Approved Pilot Training Institute). "
            "A student pilot has asked a question. Explain it thoroughly, accurately, and professionally based on the provided verified DGCA textbook excerpts. "
            "You MUST prominently state at the very beginning of your answer which textbook was referred to from the background: "
            "'📖 **Referred Background Source Book:** [Book Title], Page [Page Number] ([Subject])'. "
            "Always cite the textbook title and page numbers in bold (e.g. **Oxford Aviation Academy: Meteorology, Page 135**). "
            "Use clear markdown headings, bullet points, and formulas where applicable. "
            "If the question is in Hindi or Hinglish, answer in polite, clear Hinglish."
        )

        user_prompt = f"{system_instruction}\n\nStudent Question: {question}\n\nVerified DGCA Textbook Excerpts:\n{formatted_context}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1000}
        }

        try:
            req = urllib.request.Request(
                GEMINI_API_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as e:
            print(f"[AI Engine] Gemini API error: {e}")

        return None

    def query_knowledge_base(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Resolves institutional and regulatory queries using structured verified sources
        from knowledge_base.json (Courses, DGCA rules, exams, medicals, flying hours, FAQs).
        """
        lower = text.lower()

        # 1. DGCA Computer Number & eGCA
        if any(w in lower for w in ["computer number", "egca", "computer no"]):
            cn = self.kb["dgca_syllabus_and_rules"]["computer_number"]
            reqs = "\n".join([f"- {r}" for r in cn["requirements"]])
            ans = (
                "### 📋 **DGCA Computer Number & eGCA Registration Guide**\n\n"
                f"**What is a Computer Number?**\n{cn['definition']}\n\n"
                f"**Official Portal:** [{cn['portal']}]({cn['portal']})\n"
                f"**Processing Time:** {cn['processing_time']}\n\n"
                f"#### 📑 Mandatory Documents Checklist:\n{reqs}\n\n"
                "> 💡 *Airborne Support: Our admissions office assists all enrolled students with document attestation and eGCA submission free of charge.*\n\n"
                "📖 **Referred Background Source:** DGCA Aircraft Rules 1937, Schedule II & eGCA Portal Specifications ([egca.dgca.gov.in](https://egca.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["DGCA 5 Subjects", "Class 2 Medicals", "CPL Course Details", "Talk to Admissions Counselor"]
            }

        # 2. DGCA Syllabus, 5 Subjects, and Exam Pattern / Passing Marks
        if any(w in lower for w in ["5 subject", "five subject", "dgca subject", "passing mark", "pass percentage", "pariksha", "exam pattern", "negative marking"]) or ("syllabus" in lower and "cpl" in lower):
            exams = self.kb["dgca_syllabus_and_rules"]["dgca_exams"]
            gs = next((c for c in self.kb["courses"] if c["id"] == "ground-school"), None)
            subjects_list = "\n".join([f"{i+1}. **{s}**" for i, s in enumerate(gs["subjects_covered"])]) if gs else ""
            ans = (
                "### 📚 **DGCA CPL Theoretical Exam Pattern & Syllabus**\n\n"
                "To obtain a Commercial Pilot License in India, candidate pilots must clear theoretical examinations conducted by the DGCA (Central Examination Organisation / Pariksha portal).\n\n"
                f"#### 📝 **The 5 Core DGCA Ground Subjects:**\n{subjects_list}\n\n"
                "#### 📊 **DGCA Examination Guidelines:**\n"
                f"- **Format:** {exams['format']}\n"
                f"- **Passing Percentage:** **{exams['pass_percentage']}**\n"
                f"- **Negative Marking:** **{exams['negative_marking']}**\n"
                f"- **Exam Schedule:** {exams['frequency']}\n"
                f"- **Score Validity:** {exams['validity']}\n\n"
                "> ✈️ *Airborne Ground School provides chapter-wise question banks and mock exams on Pariksha CBT software.*\n\n"
                "📖 **Referred Background Source:** DGCA CAR Section 7 & Pariksha CBT Examination Curriculum ([pariksha.dgca.gov.in](https://pariksha.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Ground School Fees", "Computer Number Steps", "Class 1 & 2 Medicals", "CPL Flying Hours"]
            }

        # 3. DGCA Class 1 & Class 2 Medicals, Eye Vision & Lasik
        if any(w in lower for w in ["medical", "medicals", "class 1", "class 2", "eye test", "vision", "lasik", "spectacle", "glasses"]):
            med = self.kb["dgca_syllabus_and_rules"]["medicals"]
            c2 = med["class_2"]
            c1 = med["class_1"]
            centers = "\n".join([f"- {c}" for c in c1["authorized_centers"]])
            ans = (
                "### 🩺 **DGCA Pilot Medical Fitness Guidelines (Class 1 & Class 2)**\n\n"
                "Every aspiring commercial pilot must undergo a two-tier medical examination mandated by DGCA:\n\n"
                "#### 1️⃣ **Class 2 Medical (Initial Entry Level):**\n"
                f"- **Purpose:** {c2['description']}\n"
                f"- **Key Tests:** {c2['tests_included']}\n"
                f"- **Validity:** {c2['validity']}\n"
                f"- **Outcome:** {c2['outcome']}\n\n"
                "#### 2️⃣ **Class 1 Medical (Commercial Pilot Level):**\n"
                f"- **Purpose:** {c1['description']}\n"
                f"- **Authorized Centers:**\n{centers}\n"
                f"- **Vision Standard:** {c1['vision_criteria']}\n\n"
                "> 💡 *Important: You must obtain your Class 2 Medical Assessment and DGCA PMR file number before booking an appointment for Class 1 Medical.*\n\n"
                "📖 **Referred Background Source:** DGCA Civil Aviation Requirements (CAR) Section 7, Series F Part I & Medical Cell Guidelines ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Computer Number Steps", "Vision & Lasik Query", "Ground School Details", "Talk to Medical Counselor"]
            }

        # 4. Flying Hours Breakdown (200 Hours)
        if any(w in lower for w in ["200 hour", "200 flying hour", "flying hour breakdown", "flying breakdown", "solo hour", "pic hour", "cross country hour", "night flying"]):
            fb = self.kb["dgca_syllabus_and_rules"]["flying_hour_breakdown"]
            breakdown_list = "\n".join([f"- **{b.split(':')[0]}**: {b.split(':')[1]}" for b in fb["breakdown"]])
            ans = (
                "### 🛩️ **DGCA CPL 200 Flying Hours Distribution**\n\n"
                "As per DGCA Aircraft Rules 1937 (Schedule II, Section J), a minimum of **200 logged flying hours** is mandatory for the issue of a Commercial Pilot License (Aeroplanes):\n\n"
                f"{breakdown_list}\n\n"
                "#### ✈️ Fleet Flown at Airborne Aviation Academy:\n"
                "- **Single-Engine Primary:** Cessna 172R / 172S Glass Cockpit (Garmin G1000)\n"
                "- **Multi-Engine Endorsement:** Piper Seneca V & Diamond DA42\n"
                "- **Flight Simulator:** DGCA Level-5 FAA-approved FNPT-II simulator for instrument rating drills\n\n"
                "📖 **Referred Background Source Book:** Air Regulations: RK Bali 15th Edition (DGCA Aircraft Rules 1937, Schedule II, Section J)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Total Cost", "Ground School Subjects", "Medical Eligibility", "Download Brochure"]
            }

        # 5. CPL Integrated Course Details
        if any(w in lower for w in ["cpl course", "commercial pilot course", "cpl details", "cpl duration", "fleet", "pilot training details", "cessna 172"]):
            cpl = next((c for c in self.kb["courses"] if c["id"] == "cpl-integrated"), None)
            if cpl:
                inst_list = "\n".join([f"- {i}" for i in cpl["installments"]])
                high_list = "\n".join([f"- {h}" for h in cpl["highlights"]])
                ans = (
                    f"### ✈️ **{cpl['title']}**\n\n"
                    f"{cpl['description']}\n\n"
                    f"- ⏱️ **Duration:** {cpl['duration']}\n"
                    f"- 🎓 **Eligibility:** {cpl['eligibility']}\n"
                    f"- 🛩️ **Fleet:** {cpl['aircraft_fleet']}\n"
                    f"- 💰 **Fee (India):** {cpl['total_fee_india']}\n"
                    f"- 🌍 **Fee (Abroad + Conversion):** {cpl['total_fee_abroad']}\n\n"
                    f"#### 🌟 Program Highlights:\n{high_list}\n\n"
                    f"#### 💳 Milestone-Based Installments:\n{inst_list}\n\n"
                    "📖 **Referred Background Source Book:** Technical General: Principles of Flight & DGCA Approved CPL Flight Training Manual"
                )
                return {
                    "answer": ans,
                    "chips": ["200 Flying Hours Breakdown", "Education Loan Options", "Ground School Subjects", "Class 1 & 2 Medicals"]
                }

        # 6. Cadet Pilot Program
        if "cadet" in lower:
            cadet = next((c for c in self.kb["courses"] if c["id"] == "cadet-pilot"), None)
            if cadet:
                high_list = "\n".join([f"- {h}" for h in cadet["highlights"]])
                ans = (
                    f"### 👨‍✈️ **{cadet['title']}**\n\n"
                    f"{cadet['description']}\n\n"
                    f"- ⏱️ **Duration:** {cadet['duration']}\n"
                    f"- 🎓 **Eligibility:** {cadet['eligibility']}\n"
                    f"- 💼 **Airline Program Cost:** {cadet['cadet_program_cost']}\n"
                    f"- 🎯 **Airborne Prep & Mentorship Fee:** {cadet['our_prep_fee']}\n\n"
                    f"#### 🌟 Key Benefits:\n{high_list}\n\n"
                    "> 💡 *Cadet programs include a conditional job offer from IndiGo, Air India, or SpiceJet before flying begins.*\n\n"
                    "📖 **Referred Background Source:** Airline Cadet Pilot Program Mentorship Curriculum & DGCA Type-Rating Standards"
                )
                return {
                    "answer": ans,
                    "chips": ["Conventional CPL vs Cadet", "ADAPT Assessment Prep", "Education Loans", "Speak to Counselor"]
                }

        # 7. RTR(A) Radio Telephony Course
        if any(w in lower for w in ["rtr", "radio telephony", "wpc exam", "rtr-a"]):
            rtr = next((c for c in self.kb["courses"] if c["id"] == "rtr-aero"), None)
            if rtr:
                comps = "\n".join([f"- {e}" for e in rtr["exam_components"]])
                ans = (
                    f"### 🎙️ **{rtr['title']}**\n\n"
                    f"{rtr['description']}\n\n"
                    f"- ⏱️ **Duration:** {rtr['duration']}\n"
                    f"- 💰 **Fee:** {rtr['total_fee_india']}\n"
                    f"- 🎓 **Eligibility:** {rtr['eligibility']}\n\n"
                    f"#### 📻 Exam Components Conducted by WPC:\n{comps}\n\n"
                    "📖 **Referred Background Source Book:** Radio Telephony: RTR(A) Communications & Phraseology & WPC COP Syllabus"
                )
                return {
                    "answer": ans,
                    "chips": ["DGCA 5 Subjects", "CPL Course Details", "Pariksha Portal", "Talk to Ground Instructor"]
                }

        # 8. Career FAQs: Arts / Commerce & NIOS (using word boundaries to avoid collision with 'charts')
        if re.search(r'\b(arts|commerce|nios|non-science)\b', lower) or "without maths" in lower or "without physics" in lower:
            faq = next((f for f in self.kb["career_faqs"] if "Arts or Commerce" in f["question"]), None)
            ans = (
                "### 🎓 **Pilot Eligibility for Arts & Commerce Students**\n\n"
                f"{faq['answer'] if faq else 'You can become a pilot even without Physics and Maths in 12th by taking NIOS exams.'}\n\n"
                "#### 📌 Steps to Qualify via NIOS:\n"
                "1. Register on the NIOS portal (National Institute of Open Schooling) for **On-Demand Examinations**.\n"
                "2. Appear for **Physics (Code 312)** and **Mathematics (Code 311)**.\n"
                "3. Secure passing grades (minimum 50% recommended).\n"
                "4. Submit the verified NIOS marksheet to DGCA for Computer Number issuance.\n\n"
                "> 💡 *Airborne Aviation Academy provides in-house coaching for NIOS Physics & Mathematics alongside your ground classes.*\n\n"
                "📖 **Referred Background Source:** DGCA Public Circular on NIOS Senior Secondary Equivalence ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["Computer Number Steps", "CPL Course Details", "Fee Structure & Loans", "Talk to Admissions Counselor"]
            }

        # 9. Career FAQs: Pilot Salary in India
        if any(w in lower for w in ["salary", "pilot salary", "how much does a pilot earn", "earnings", "pay"]):
            faq = next((f for f in self.kb["career_faqs"] if "starting salary" in f["question"].lower()), None)
            ans = (
                "### 💵 **Commercial Pilot Salary Breakdown in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "#### 📈 Career Progression & Typical Compensation:\n"
                "| Rank | Experience | Estimated Monthly Salary |\n"
                "| :--- | :--- | :--- |\n"
                "| **Junior First Officer (Second Officer)** | 0 - 500 Hours | ₹1,50,000 - ₹2,50,000 |\n"
                "| **First Officer** | 500 - 2,500 Hours | ₹3,50,000 - ₹5,00,000 |\n"
                "| **Senior First Officer** | 2,500 - 4,000 Hours | ₹4,50,000 - ₹6,50,000 |\n"
                "| **Captain (A320 / B737 Commander)** | 4,000+ Hours & ATPL | ₹6,50,000 - ₹10,50,000 |\n"
                "| **Line Training Captain (LTC / TRI / TRE)**| Senior Captain | ₹11,00,000 - ₹15,00,000+ |\n\n"
                "> ✈️ *Aviation is one of the highest-paying professions in India, with rapid return on initial training investment.*\n\n"
                "📖 **Referred Background Source:** Indian Airline First Officer & Commander Industry Survey (Airborne Careers)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Total Cost", "Cadet Pilot Programs", "100% Bank Loans", "Airline Hiring Demand"]
            }

        # 10. Career FAQs: Age Limits
        if any(w in lower for w in ["age limit", "minimum age", "maximum age", "upper age", "how old"]):
            faq = next((f for f in self.kb["career_faqs"] if "minimum age" in f["question"].lower()), None)
            ans = (
                "### 📅 **Age Criteria for Pilot Training in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "- 🪪 **Student Pilot License (SPL):** Minimum 16 years of age.\n"
                "- 🛫 **Commercial Pilot License (CPL):** Minimum 17 years to fly solo; 18 years for license issuance.\n"
                "- 👨‍✈️ **Airline Cadet Pilot Programs:** Typically 18 to 32 years at application.\n"
                "- 🛩️ **Maximum Commercial Flying Age:** Commercial pilots can fly with airlines up to **65 years of age** as per DGCA rules.\n\n"
                "> 💡 *It is never too late: Many professionals transition to commercial aviation in their late 20s and 30s successfully.*\n\n"
                "📖 **Referred Background Source Book:** Air Regulations: RK Bali 15th Edition (DGCA Aircraft Rules 1937, Rule 38A & Schedule II)"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Class 1 & 2 Medicals", "Total Course Fees", "Admissions Help"]
            }

        # 11. Career FAQs: Airline Hiring Demand & Industry Scope
        if any(w in lower for w in ["hiring demand", "airline demand", "scope", "market demand", "pilot shortage", "job opportunity"]):
            faq = next((f for f in self.kb["career_faqs"] if "hiring demand" in f["question"].lower()), None)
            ans = (
                "### 🚀 **Aviation Industry Growth & Pilot Hiring Boom in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "#### ✈️ Major Fleet Expansions in India:\n"
                "- **Air India:** 470 aircraft ordered (Airbus A320neo, A350 & Boeing 737 MAX, 777X, 787)\n"
                "- **IndiGo:** 500 aircraft order (Airbus A320neo family) + 30 A350 widebodies\n"
                "- **Akasa Air:** 200+ Boeing 737 MAX aircraft\n\n"
                "> 💡 *Each narrow-body airliner requires an average of 10 to 12 pilots (Captains & First Officers) to operate 24/7 schedules.*\n\n"
                "📖 **Referred Background Source:** DGCA Commercial Pilot Licensing Annual Statistics & Fleet Expansion Reports ([dgca.gov.in](https://www.dgca.gov.in))"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Cadet Pilot Programs", "Ground School Syllabus", "Talk to Flight Advisor"]
            }

        # 12. Academy Information & Campus Hubs
        if any(w in lower for w in ["about academy", "location", "locations", "where are you", "ground center", "flying base", "contact academy"]):
            acad = self.kb["academy"]
            locs = "\n".join([f"- {loc}" for loc in acad["locations"]])
            ans = (
                f"### ✈️ **About {acad['name']}**\n\n"
                f"*{acad['tagline']}*\n\n"
                f"#### 📍 Training Hubs & Flight Bases:\n{locs}\n\n"
                "#### 📞 Contact & Admissions Desk:\n"
                f"- **Helpline Toll-Free:** {acad['phone_helpline']}\n"
                f"- **WhatsApp Admissions:** {acad['whatsapp_display']}\n"
                f"- **Admissions Email:** {acad['email']}\n\n"
                "Visit our ground center or book a simulator cockpit trial with our senior flight instructors!\n\n"
                "📖 **Referred Background Source:** Airborne Aviation Academy Official Prospectus & DGCA Approved Flying Training Hubs"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "Fee Breakdown & Loans", "DGCA Syllabus", "Chat on WhatsApp"]
            }

        return None

    def answer_query(self, message: str, persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET) -> Dict[str, Any]:
        """Processes student query using modular EduBot IntentRouter with Persona context"""
        return self.router.route_and_process(message, persona=persona)

    def _legacy_answer_query(self, message: str) -> Dict[str, Any]:
        """Legacy direct procedural query processor"""
        text = message.strip()
        is_complex, complex_reason = self.is_complex_query(text)
        escalation = self.generate_escalation_data(message, complex_reason) if is_complex else {
            "needed": False,
            "whatsapp_url": f"https://wa.me/{self.kb['academy']['whatsapp_number'].replace('+', '')}",
            "whatsapp_display": self.kb["academy"]["whatsapp_display"],
            "phone_helpline": self.kb["academy"]["phone_helpline"]
        }

        # 1. Adversarial & Jailbreak Defense
        if self.is_adversarial_or_jailbreak(text):
            return {
                "answer": (
                    "### 🛡️ **Airborne Flight Training Assistant**\n\n"
                    "I am the dedicated 24/7 AI Flight Training Advisor for **Airborne Aviation Academy**. "
                    "My operating guidelines restrict me exclusively to DGCA flight training, ground school subjects, CPL/ATPL course fees, and pilot career counseling. "
                    "How can I assist your aviation and flight training journey today?"
                ),
                "chips": ["DGCA CPL Syllabus", "Course Fee Breakdown", "Class 1 & 2 Medicals", "Bank Loan Assistance"],
                "escalation": escalation
            }

        # 2. Illegal Requests & Fraud Defense
        if self.is_illegal_or_fraud(text):
            return {
                "answer": (
                    "### 🛡️ **Airborne Compliance & Regulatory Integrity**\n\n"
                    "Airborne Aviation Academy operates in strict compliance with the **Directorate General of Civil Aviation (DGCA)**, Aircraft Rules 1937, and international flight safety standards.\n\n"
                    "We **strictly prohibit** and refuse any assistance with:\n"
                    "- ❌ Fabricated flight logbooks or bypass of mandatory 200 flying hours\n"
                    "- ❌ Fake DGCA licenses, cheating, or bribery\n"
                    "- ❌ Bypassing Class 1 or Class 2 medical examinations\n\n"
                    "All pilot qualifications must be earned legitimately through verified flight training, genuine medical board clearances, and passing official DGCA examinations.\n\n"
                    "📖 **Referred Background Source:** DGCA Aircraft Rules 1937 & Regulatory Compliance Enforcement Guidelines"
                ),
                "chips": ["DGCA CPL Syllabus", "Class 1 & 2 Medical Process", "Course Fee Breakdown", "Bank Loan Assistance"],
                "escalation": escalation
            }

        # 3. External Web Scraping & Official Portal Verification Policy
        if self.is_external_web_request(text):
            response_text = (
                "### ⚠️ **Official DGCA Source Policy (Zero Third-Party Web Scraping)**\n\n"
                "I do not possess or use general web scraping capabilities on arbitrary third-party websites. "
                "To maintain 100% regulatory integrity and prevent unverified misinformation, I can answer queries **only if the information is officially published on official DGCA portals**:\n\n"
                "- 🌐 **Directorate General of Civil Aviation:** [dgca.gov.in](https://www.dgca.gov.in)\n"
                "- 🌐 **Central Examination Organisation (Pariksha):** [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in)\n\n"
                "**No other website will be checked.**\n\n"
                "Whenever official online information from these portals is referenced, the exact portal pages will be cited as the authoritative source.\n\n"
                "Would you like me to verify whether your query is covered on [dgca.gov.in](https://www.dgca.gov.in) or [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in)?\n\n"
                "📖 **Referred Background Source:** Official DGCA Regulatory Portal Policy ([dgca.gov.in](https://www.dgca.gov.in) & [pariksha.dgca.gov.in](https://pariksha.dgca.gov.in))"
            )
            return {
                "answer": response_text,
                "chips": ["DGCA Official Circulars", "Pariksha Exam Portal", "DGCA 5 Subjects", "Talk to Admissions Counselor"],
                "escalation": escalation
            }

        # 4. Pure Greetings (only if message is predominantly a greeting without substantive question)
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
            return {"answer": response_text, "chips": chips, "escalation": escalation}

        # 4. Institutional & Regulatory Knowledge Base Queries (Courses, Medicals, Computer Number, Exams, FAQs)
        kb_result = self.query_knowledge_base(text)
        if kb_result:
            return {
                "answer": kb_result["answer"],
                "chips": kb_result.get("chips", []),
                "escalation": escalation
            }

        # 5. Fee & Loan Queries
        if any(w in text.lower() for w in ["fee", "fees", "cost", "price", "budget", "expensive", "charges", "installment", "sbi", "hdfc", "loan", "financ"]):
            budget = self.kb["fees_and_loans"]["budget_summary"]
            loans = self.kb["fees_and_loans"]["bank_loans"]
            response_text = (
                "### 💰 **Comprehensive Pilot Training Fee Breakdown**\n\n"
                "Becoming a Commercial Pilot in India involves the following cost components:\n\n"
                "| Component | Estimated Cost | Notes |\n"
                "| :--- | :--- | :--- |\n"
                f"| **DGCA Ground School** | {budget['ground_school']} | 5 subjects + RTR(A) exam prep |\n"
                f"| **200 Flying Hours (India)** | {budget['flying_training_200hrs']} | Cessna 172 Glass Cockpit + Multi-Engine |\n"
                f"| **Medicals & DGCA Exam Fees** | {budget['dgca_exam_and_medical_fees']} | Class 2, Class 1 & 5 DGCA papers |\n"
                f"| **Books, Uniform & Headset** | {budget['uniform_books_navigation_logbook']} | Navigation computer, logbook, charts |\n"
                f"| **Total Conventional CPL** | **{budget['total_estimated_conventional_cpl']}** | Payable in 4-5 stage installments |\n\n"
                "#### 🏦 **Education Loans & Financing**:\n"
                f"- **Partner Banks**: {', '.join(loans['partner_banks'])}\n"
                f"- **Loan Coverage**: Up to ₹1.5 Cr with approved collateral; up to ₹7.5 Lakhs collateral-free under national education schemes.\n"
                f"- **Moratorium Period**: {loans['moratorium']}\n"
                f"- **Interest Rate**: Typically {loans['interest_rate_range']}.\n\n"
                "> 💡 *Tip: We provide bonafide fee structure certificates and quotation letters required by banks for instant loan sanctions.*\n\n"
                "📖 **Referred Background Source:** Airborne Aviation Academy Fee Schedule & SBI Scholar/Global Ed-Vantage Scheme Guidelines"
            )
            chips = ["CPL Installment Schedule", "Bank Loan Assistance", "Cadet Pilot Costs", "Talk to Finance Counselor"]
            escalation["needed"] = True
            escalation["reason"] = "Personalized Loan & Installment Consultation Available"
            return {"answer": response_text, "chips": chips, "escalation": escalation}

        # 6. Out-of-Domain Guardrail: Rejection of non-aviation requests (recipes, coding hacks, stocks)
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
                "escalation": escalation
            }

        # 7. Search RAG Database across DGCA Books for theoretical ground school queries
        rag_results = rag_pipeline.search(message, top_k=3)

        if rag_results:
            # Try Gemini synthesis
            gemini_ans = self.generate_with_gemini(message, rag_results)
            if gemini_ans:
                return {
                    "answer": gemini_ans,
                    "chips": ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"],
                    "escalation": escalation
                }

            # Local verified RAG presentation
            sources_md = []
            citations = []
            for r in rag_results:
                source_tag = f"**{r['book_title']}** (Page {r['page_number']}) — *{r['subject']}*"
                citations.append(source_tag)
                clean_snippet = r['text'].strip()
                if len(clean_snippet) > 450:
                    clean_snippet = clean_snippet[:450] + "..."
                sources_md.append(f"> 📖 **{r['book_title']} [p. {r['page_number']}]**:\n> \"{clean_snippet}\"")

            answer_body = (
                f"### ✈️ **DGCA Textbook Doubt Resolution**\n\n"
                f"📖 **Referred Background Source Book:** **{rag_results[0]['book_title']}** (Page {rag_results[0]['page_number']}) — *Subject: {rag_results[0]['subject']}*\n\n"
                f"Here is the verified theoretical explanation from the official **DGCA Aviation Syllabus & Curriculum**:\n\n"
                f"{rag_results[0]['text'].strip()}\n\n"
            )

            if len(rag_results) > 1:
                answer_body += f"#### 🔍 Additional Technical References:\n" + "\n\n".join(sources_md[1:]) + "\n\n"

            answer_body += f"📚 **Referenced DGCA Textbooks:**\n" + "\n".join([f"- {c}" for c in citations])

            chips = ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"]
            return {"answer": answer_body, "chips": chips, "escalation": escalation}

        # 8. Fallback for unindexed general aviation queries
        escalation["needed"] = True
        escalation["reason"] = "Aviation advisor ready to answer your specific flight question"
        response_text = (
            f"Thank you for your question regarding **\"{message}\"**.\n\n"
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
        return {"answer": response_text, "chips": chips, "escalation": escalation}

ai_engine = AviationAIEngine()
