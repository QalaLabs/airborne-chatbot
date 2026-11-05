import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.rag_pipeline import rag_pipeline

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_KB_PATH = BASE_DIR / "backend" / "knowledge_base.json"
DEFAULT_GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")

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
    "cpl", "ppl", "atpl", "dgca", "pilot", "plane", "aircraft", "flying", "flight",
    "nav", "navigation", "altimeter", "stall", "weather", "met", "meteorology",
    "qnh", "qfe", "engine", "airspace", "course", "fee", "fees", "medical", "class 1",
    "class 2", "rtr", "license", "cadet", "ground school", "speed", "knot", "runway",
    "atc", "cessna", "multi-engine", "instrument", "vor", "dme", "ils", "radar",
    "squawk", "fdtl", "cross country", "solo", "computer number", "egca", "pariksha",
    "aerodynamics", "lift", "drag", "thrust", "airframe", "hydraulics", "propeller",
    "monsoon", "turbulence", "icing", "cloud", "cumulonimbus", "metar", "taf",
    "cost", "price", "installment", "salary", "hours", "admission", "eligibility",
    "physics", "maths", "nios", "arts", "commerce", "12th", "spectacles", "glasses",
    "curriculum", "syllabus", "duration", "qualification", "exam", "exams", "paper",
    "passing", "pass", "marks", "marksheet", "documents", "training", "academy", "rules"
}

class AviationAIEngine:
    def __init__(self, kb_path: Optional[str] = None):
        self.kb_path = Path(kb_path) if kb_path else DEFAULT_KB_PATH
        self.kb = self._load_kb()
        self.api_key = os.environ.get("GEMINI_API_KEY", DEFAULT_GEMINI_KEY)
        self.model_name = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

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
            "act as a", "pretend you are", "jailbreak", "dan mode", "bypass"
        ]
        return any(t in lower for t in jailbreak_triggers)

    def is_aviation_query(self, message: str) -> bool:
        """Determines if query belongs to the aviation domain"""
        tokens = set(re.findall(r'\b[a-z0-9\-]+\b', message.lower()))
        if tokens & AVIATION_TERMS:
            return True
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
        """
        Token-optimized call to Google Gemini Flash REST API with retrieved DGCA textbook excerpts.
        Minimizes prompt tokens and caps output tokens to eliminate token waste.
        """
        api_key = os.environ.get("GEMINI_API_KEY", self.api_key)
        if not api_key:
            return None

        # Format concise context excerpts (up to 3 chunks, ~350 chars each) to optimize token usage
        compact_chunks = []
        for c in context_chunks[:3]:
            snippet = c.get("text", "").strip()
            if len(snippet) > 400:
                snippet = snippet[:400] + "..."
            compact_chunks.append(f"[{c['book_title']} - p.{c['page_number']} - {c['subject']}]:\n{snippet}")

        formatted_context = "\n\n".join(compact_chunks)

        system_instruction = (
            "You are the Senior Flight Ground Instructor at Airborne Aviation Academy (DGCA Approved). "
            "Explain the student pilot's query accurately, professionally, and concisely based on the verified DGCA textbook excerpts below. "
            "Cite textbook and page in bold (e.g. **Oxford Aviation Academy: Meteorology, p. 135**). "
            "Use clear bullet points and formulas where relevant. Keep response under 400 words."
        )

        user_prompt = f"{system_instruction}\n\nExcerpts:\n{formatted_context}\n\nStudent Doubt: {question}"

        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600
            }
        }

        model = os.environ.get("GEMINI_MODEL", self.model_name)
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        try:
            req = urllib.request.Request(
                api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-goog-api-key": api_key}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as e:
            # Fallback to gemini-1.5-flash if custom model endpoint fails
            if model != "gemini-1.5-flash":
                try:
                    fallback_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
                    req2 = urllib.request.Request(
                        fallback_url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json", "X-goog-api-key": api_key}
                    )
                    with urllib.request.urlopen(req2, timeout=10.0) as resp2:
                        data2 = json.loads(resp2.read().decode("utf-8"))
                        candidates2 = data2.get("candidates", [])
                        if candidates2:
                            parts2 = candidates2[0].get("content", {}).get("parts", [])
                            if parts2:
                                return parts2[0].get("text", "")
                except Exception:
                    pass
            print(f"[AI Engine] Gemini API error: {e}")

        return None

    def match_knowledge_base(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Directly matches student query against structured Knowledge Base data.
        Returns high-confidence, verified response without consuming LLM tokens.
        """
        lower = text.lower()

        # 1. Career FAQs: Arts / Commerce / NIOS / 10+2 non-science
        if re.search(r'\b(arts|commerce|non-science|without (maths|physics)|nios|open school)\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "arts" in f["question"].lower()), None)
            ans = (
                "### 🎓 **Becoming a Pilot from Arts or Commerce Background**\n\n"
                f"{faq['answer'] if faq else 'YES! You can become a commercial pilot in India even without 10+2 Science.'}\n\n"
                "#### 📋 **The NIOS Pathway Explained:**\n"
                "- **DGCA Requirement**: 10+2 passing certificate with Physics and Mathematics.\n"
                "- **The Solution**: Enroll for Physics & Mathematics via **NIOS (National Institute of Open Schooling)** On-Demand Examinations.\n"
                "- **100% DGCA Valid**: DGCA unconditionally accepts NIOS marksheet for your Computer Number and CPL issue.\n"
                "- **Concurrent Training**: At Airborne Aviation Academy, you can attend Ground Classes while preparing for NIOS papers simultaneously."
            )
            return {
                "answer": ans,
                "chips": ["DGCA Computer Number", "Ground School Syllabus", "CPL Fee Structure", "Talk to Admissions Counselor"]
            }

        # 2. Career FAQs: Starting Salary & Career Roadmap
        if re.search(r'\b(salary|salaries|earn|earning|pay scale|package|pilot income)\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "salary" in f["question"].lower()), None)
            ans = (
                "### 💼 **Commercial Pilot Salary Breakdown in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "| Rank / Role | Flying Experience | Approximate Monthly Salary |\n"
                "| :--- | :--- | :--- |\n"
                "| **Junior First Officer** | Fresh CPL + Type Rating | **₹1,50,000 – ₹2,50,000** |\n"
                "| **First Officer (FO)** | 500 – 1,500 Flying Hours | **₹3,50,000 – ₹5,00,000** |\n"
                "| **Senior First Officer** | 1,500 – 3,000 Flying Hours | **₹5,00,000 – ₹6,50,000** |\n"
                "| **Captain / Commander** | ATPL + 2,500+ Hours | **₹6,50,000 – ₹10,50,000** |\n"
                "| **Line Training Captain (LTC/TRI)** | Senior Airline Examiner | **₹10,50,000 – ₹14,00,000+** |\n\n"
                "> 💡 *Airlines also provide international layover allowances, comprehensive medical insurance, and free family flight tickets.*"
            )
            return {
                "answer": ans,
                "chips": ["Conventional CPL Course", "Cadet Pilot Programs", "DGCA Exams Guide", "Talk to Chief Counselor"]
            }

        # 3. Career FAQs: Spectacles / Glasses / Eyesight Criteria (Non-escalation informative queries)
        if re.search(r'\b(glasses|spectacles|specs|contact lenses|vision criteria|eyesight criteria|wear glasses|can i wear glasses)\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "glasses" in f["question"].lower()), None)
            ans = (
                "### 👓 **DGCA Eyesight & Spectacles Regulations**\n\n"
                f"{faq['answer'] if faq else 'Yes, wearing spectacles or contact lenses is completely permissible.'}\n\n"
                "#### 🔍 **DGCA Medical Vision Parameters:**\n"
                "- **Distance Vision**: Must correct to **6/6** in each eye with glasses or contact lenses.\n"
                "- **Near Vision**: Normal reading vision (N5) with or without correction.\n"
                "- **Permissible Refractive Error**: Up to ±6.00 Dioptres spherical/cylindrical for Class 1 Medicals.\n"
                "- **Lasik / Refractive Surgery**: Permitted by DGCA if done after 18 years of age and stable for >6 months.\n"
                "- **Color Vision**: Must be normal (tested via 38-plate Ishihara pseudoisochromatic plates)."
            )
            return {
                "answer": ans,
                "chips": ["Class 1 & 2 Medical Process", "Book Medical Appointment", "Ground School Details", "Talk to Doctor"]
            }

        # 4. Career FAQs: Conventional CPL vs Cadet Pilot Program
        if re.search(r'\b(conventional.*cadet|cadet.*conventional|difference between.*(cadet|conventional))\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "difference" in f["question"].lower()), None)
            ans = (
                "### ✈️ **Conventional CPL vs. Airline Cadet Pilot Program**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "| Comparison Metric | Conventional CPL Course | Airline Cadet Pilot Program |\n"
                "| :--- | :--- | :--- |\n"
                "| **Total Cost** | **₹42 Lakhs – ₹48 Lakhs** | **₹95 Lakhs – ₹1.15 Crores** |\n"
                "| **Job Security** | Open license; apply to all airlines upon graduation | Conditional Letter of Intent (LOI) before flying begins |\n"
                "| **Type Rating** | Self-sponsored post-CPL (~₹15-20L) | Included in program (A320/B737) |\n"
                "| **Airline Flexibility** | Freedom to join any airline (IndiGo, Air India, Akasa) | Bonded to specific partner airline for 5-7 years |\n"
                "| **Duration** | 14 to 18 Months | 18 to 24 Months |"
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Structure", "Cadet Prep Classes", "Bank Loan Assistance", "Book Counseling Call"]
            }

        # 5. Career FAQs: Minimum & Upper Age Limit
        if re.search(r'\b(age limit|minimum age|upper age|maximum age|how old can i be)\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "age" in f["question"].lower()), None)
            ans = (
                "### ⏳ **DGCA Pilot Age Criteria & Career Span**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "- **Student Pilot License (SPL)**: Minimum **16 years** of age.\n"
                "- **Commercial Pilot License (CPL)**: Minimum **17 years** to fly; CPL issued at **18 years**.\n"
                "- **Airline First Officer Hiring**: Generally **18 to 35 years** of age.\n"
                "- **Commercial Flying Privileges**: DGCA permits airline flying privileges up to **65 years of age** in two-pilot cockpit operations."
            )
            return {
                "answer": ans,
                "chips": ["CPL Course Details", "10+2 Eligibility", "Class 2 Medicals", "Talk to Counselor"]
            }

        # 6. Career FAQs: Hiring Demand & Industry Growth
        if re.search(r'\b(hiring demand|job market|pilot demand|scope of pilot|airline orders|pilot shortage)\b', lower):
            faq = next((f for f in self.kb.get("career_faqs", []) if "hiring" in f["question"].lower()), None)
            ans = (
                "### 📈 **Aviation Hiring Demand & Pilot Scope in India**\n\n"
                f"{faq['answer'] if faq else ''}\n\n"
                "- **Historic Aircraft Fleet Expansion**: Indian airlines (Air India, IndiGo, Akasa) have ordered **1,500+ new commercial aircraft** scheduled for delivery through 2035.\n"
                "- **Pilot Requirements**: Narrow-body aircraft require ~12 pilots (6 flight crews); wide-body requires ~20-24 pilots. Over **12,000 new commercial pilots** are required across India over the next 10 years.\n"
                "- **Airport Infrastructure**: Expansion of 100+ airports under UDAN scheme drives regional flight frequency."
            )
            return {
                "answer": ans,
                "chips": ["Commercial Pilot Course (CPL)", "Cadet Pilot Programs", "Fee Breakdown & Loans", "Talk to Senior Advisor"]
            }

        # 7. DGCA Rules: Computer Number Requirements & Process
        if re.search(r'\b(computer number|egca|documents? for computer number|apply for computer number|verification letter)\b', lower):
            cn = self.kb.get("dgca_syllabus_and_rules", {}).get("computer_number", {})
            reqs = "\n".join([f"- {r}" for r in cn.get("requirements", [])])
            ans = (
                "### 🆔 **DGCA Computer Number — Complete Checklist & Process**\n\n"
                f"{cn.get('definition', 'A unique permanent identification number issued by the DGCA via the eGCA portal.')}\n\n"
                f"#### 📋 **Mandatory Documents Required:**\n{reqs}\n\n"
                f"- **Application Portal**: eGCA Official Portal ({cn.get('portal', 'https://egca.dgca.gov.in')})\n"
                f"- **Processing Time**: {cn.get('processing_time', '15 to 30 working days')}\n\n"
                "> 💡 *Airborne Aviation Academy assists every enrolled cadet with end-to-end document verification and eGCA application filing.*"
            )
            return {
                "answer": ans,
                "chips": ["Class 2 Medical Assistance", "Ground School Syllabus", "CPL Flying Hours", "Contact Admissions Desk"]
            }

        # 8. DGCA Rules: Exam Pattern, Passing Marks & Pariksha
        if re.search(r'\b(passing mark|passing percentage|pass mark|pass percentage|negative marking|pariksha|exam pattern|exam format|dgca exams?|5 subjects)\b', lower):
            exams = self.kb.get("dgca_syllabus_and_rules", {}).get("dgca_exams", {})
            ans = (
                "### 📝 **DGCA Pilot Theoretical Examination Scheme**\n\n"
                "Every Commercial Pilot License (CPL) aspirant must pass 5 DGCA theory papers plus WPC RTR(A):\n\n"
                "| # | DGCA Subject | Format | Pass Percentage | Result Validity |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
                "| 1 | **Air Navigation** | Online CBT (MCQs) | **70%** | **5 Years** |\n"
                "| 2 | **Aviation Meteorology** | Online CBT (MCQs) | **70%** | **5 Years** |\n"
                "| 3 | **Air Regulations** | Online CBT (MCQs) | **70%** | **5 Years** |\n"
                "| 4 | **Technical General** | Online CBT (MCQs) | **70%** | **5 Years** |\n"
                "| 5 | **Technical Specific** | Online CBT (MCQs) | **70%** | **5 Years** |\n\n"
                f"- **Exam Mode**: {exams.get('format', 'Online Computer-Based Testing (CBT), Multiple Choice Questions')}\n"
                f"- **Negative Marking**: **{exams.get('negative_marking', 'No negative marking in DGCA CPL exams')}**\n"
                f"- **Frequency**: {exams.get('frequency', 'Quarterly / On-Demand through Pariksha portal')}\n"
                f"- **Validity**: {exams.get('validity', 'Results are valid for 5 years to complete flight training.')}"
            )
            return {
                "answer": ans,
                "chips": ["Air Navigation Theory", "Aviation Meteorology", "Air Regulations RK Bali", "Ground School Admissions"]
            }

        # 9. DGCA Rules: Class 1 & Class 2 Medicals
        if re.search(r'\b(class [12]|class 1 medical|class 2 medical|medical process|medical test|iam bangalore|afcme|medical centers?)\b', lower):
            medicals = self.kb.get("dgca_syllabus_and_rules", {}).get("medicals", {})
            c2 = medicals.get("class_2", {})
            c1 = medicals.get("class_1", {})
            centers = "\n".join([f"- {c}" for c in c1.get("authorized_centers", [])])
            ans = (
                "### 🩺 **DGCA Pilot Medical Examination Stages**\n\n"
                "Pilot medical certification in India involves two stages:\n\n"
                "#### 1. **Class 2 Medical (Initial Entry Stage)**\n"
                f"- **Description**: {c2.get('description', 'Initial medical by DGCA empanelled civil doctors.')}\n"
                f"- **Tests Included**: {c2.get('tests_included', 'Blood routine, Lipid profile, Urine RE/ME, Audiometry, ECG, Chest X-ray, Eye test.')}\n"
                f"- **Validity**: {c2.get('validity', '2 years for pilots under 40 years.')}\n\n"
                "#### 2. **Class 1 Medical (Commercial Pilot Issue Stage)**\n"
                f"- **Description**: {c1.get('description', 'Advanced medical required for final CPL issuance.')}\n"
                f"- **Prerequisite**: {c1.get('prerequisite', 'Valid DGCA Class 2 Medical Assessment.')}\n"
                f"- **Vision Standard**: {c1.get('vision_criteria', '6/6 corrected with glasses or contact lenses.')}\n"
                f"- **Authorized IAF / Civil Centers**:\n{centers}"
            )
            return {
                "answer": ans,
                "chips": ["Book Class 2 Doctor", "Computer Number Application", "CPL Course Structure", "Talk to Flight Surgeon"]
            }

        # 10. DGCA Rules: 200 Flying Hours Breakdown
        if re.search(r'\b(200 flying hours?|hour breakdown|flying hour breakdown|breakdown of.*hours?|solo hours?|cross country hours?|instrument hours?|night hours?)\b', lower):
            fh = self.kb.get("dgca_syllabus_and_rules", {}).get("flying_hour_breakdown", {})
            breakdown_list = "\n".join([f"- {b}" for b in fh.get("breakdown", [])])
            ans = (
                "### 🛩️ **DGCA Mandatory 200 Flying Hours Breakdown**\n\n"
                f"Per DGCA Civil Aviation Requirements (CAR) Section 7, a minimum of **{fh.get('total_required', 200)} Flight Hours** are mandatory for CPL issue:\n\n"
                f"{breakdown_list}\n\n"
                "> 💡 *At Airborne Aviation Academy, cadets log these 200 hours on Garmin G1000 Glass Cockpit Cessna 172s and multi-engine aircraft (Piper Seneca V / Diamond DA42).*"
            )
            return {
                "answer": ans,
                "chips": ["CPL Integrated Course", "Fleet & Cockpit Specs", "Course Fee Breakdown", "Talk to Chief Flight Instructor"]
            }

        # 11. Courses: Ground School
        if re.search(r'\b(ground school|ground classes|dgca ground)\b', lower):
            gs = next((c for c in self.kb.get("courses", []) if c["id"] == "ground-school"), None)
            if gs:
                subjects = "\n".join([f"- {s}" for s in gs.get("subjects_covered", [])])
                ans = (
                    f"### 📚 **{gs['title']}**\n\n"
                    f"{gs['description']}\n\n"
                    f"- **Duration**: {gs['duration']}\n"
                    f"- **Eligibility**: {gs['eligibility']}\n"
                    f"- **Total Fee**: **{gs['total_fee_india']}**\n\n"
                    f"#### 📖 **Subjects Covered (All 5 DGCA Papers + RTR):**\n{subjects}\n\n"
                    f"#### 💳 **Installment Schedule:**\n" + "\n".join([f"- {i}" for i in gs.get("installments", [])])
                )
                return {
                    "answer": ans,
                    "chips": ["Enroll in Ground School", "DGCA Syllabus & Exams", "CPL 200 Flying Hours", "Talk to Chief Instructor"]
                }

        # 12. Courses: Cadet Pilot Program
        if re.search(r'\b(cadet program|cadet pilot program|cadet course|indigo cadet|air india cadet)\b', lower):
            cp = next((c for c in self.kb.get("courses", []) if c["id"] == "cadet-pilot"), None)
            if cp:
                ans = (
                    f"### 👨‍✈️ **{cp['title']}**\n\n"
                    f"{cp['description']}\n\n"
                    f"- **Duration**: {cp['duration']}\n"
                    f"- **Eligibility**: {cp['eligibility']}\n"
                    f"- **Airline Cadet Fee**: {cp['cadet_program_cost']}\n"
                    f"- **Airborne Academy Prep Fee**: {cp['our_prep_fee']}\n\n"
                    f"#### 🌟 **Program Highlights:**\n" + "\n".join([f"- {h}" for h in cp.get("highlights", [])])
                )
                return {
                    "answer": ans,
                    "chips": ["Cadet Assessment Prep", "ADAPT & COMPASS Drills", "Bank Loan Assistance", "Talk to Cadet Mentor"]
                }

        # 13. Courses: RTR(A) Radio Telephony
        if re.search(r'\b(rtr|rtr\(a\)|radio telephony restricted|wpc exam)\b', lower):
            rt = next((c for c in self.kb.get("courses", []) if c["id"] == "rtr-aero"), None)
            if rt:
                ans = (
                    f"### 📻 **{rt['title']}**\n\n"
                    f"{rt['description']}\n\n"
                    f"- **Duration**: {rt['duration']}\n"
                    f"- **Eligibility**: {rt['eligibility']}\n"
                    f"- **Total Fee**: **{rt['total_fee_india']}**\n\n"
                    f"#### 🎯 **Exam Components (WPC Ministry of Communications):**\n" + "\n".join([f"- {e}" for e in rt.get("exam_components", [])])
                )
                return {
                    "answer": ans,
                    "chips": ["Enroll in RTR(A)", "DGCA Computer Number", "Full Course Fees", "Talk to RT Instructor"]
                }

        # 14. Courses: Commercial Pilot License (CPL) Integrated or Course Overview
        if re.search(r'\b(cpl course|cpl details|commercial pilot license course|integrated cpl|what courses|which course|all courses|courses? offered)\b', lower):
            cpl = next((c for c in self.kb.get("courses", []) if c["id"] == "cpl-integrated"), None)
            if cpl:
                ans = (
                    f"### ✈️ **{cpl['title']}**\n\n"
                    f"{cpl['description']}\n\n"
                    f"- **Course Duration**: {cpl['duration']}\n"
                    f"- **Educational Eligibility**: {cpl['eligibility']}\n"
                    f"- **Total Course Investment (India)**: **{cpl['total_fee_india']}**\n"
                    f"- **Abroad Pathway (USA/South Africa + Conversion)**: {cpl['total_fee_abroad']}\n"
                    f"- **Modern Training Fleet**: {cpl['aircraft_fleet']}\n\n"
                    f"#### 💳 **Stage-wise Installment Schedule:**\n" + "\n".join([f"- {i}" for i in cpl.get("installments", [])]) + "\n\n"
                    f"#### ⭐ **Key Highlights:**\n" + "\n".join([f"- {h}" for h in cpl.get("highlights", [])])
                )
                return {
                    "answer": ans,
                    "chips": ["100% Bank Loan Support", "Ground School Only", "Class 1 & 2 Medicals", "Talk to Flight Advisor"]
                }

        # 15. Academy Contact / Helpline / Campus Locations
        if re.search(r'\b(contact|helpline|phone number|call|whatsapp|email|address|location|campus|centers?|where are you located)\b', lower):
            acad = self.kb.get("academy", {})
            locs = "\n".join([f"- {l}" for l in acad.get("locations", [])])
            ans = (
                f"### 🏢 **{acad.get('name', 'Airborne Aviation Academy')}**\n\n"
                f"*{acad.get('tagline', 'DGCA Approved Premier Pilot Training & Ground School')}*\n\n"
                f"- **Toll-Free Helpline**: {acad.get('phone_helpline', '+91 1800 247 2676')}\n"
                f"- **WhatsApp Flight Desk**: {acad.get('whatsapp_display', '+91 98765 43210')}\n"
                f"- **Admissions Email**: {acad.get('email', 'admissions@airborne-aviation.edu')}\n\n"
                f"#### 📍 **Campus & Flying Base Locations:**\n{locs}"
            )
            return {
                "answer": ans,
                "chips": ["Connect on WhatsApp", "Call Helpline Now", "Schedule Campus Visit", "Request Call Back"]
            }

        return None

    def answer_query(self, message: str) -> Dict[str, Any]:
        """Processes student query with scope guardrails, structured knowledge base, RAG, and escalation"""
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

        # 2. Strict Greeting Matcher (Word boundaries only, avoid false positives on 'which', 'this', 'approaching')
        is_pure_greeting = bool(
            re.search(r'\b(hello|hi|hey|good morning|good evening|namaste)\b', text.lower()) and
            len(text.split()) <= 4
        ) or text.lower() in ["start", "get started", "restart"]

        if is_pure_greeting:
            response_text = (
                f"### Welcome to **{self.kb['academy']['name']}**! ✈️\n\n"
                "I am your **24/7 AI Aviation Flight Advisor & Ground School Tutor**, powered by **Gemini Flash & 13 DGCA Pilot Training Textbooks (9,200+ knowledge chunks)**. "
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

        # 3. High-Intent Complex Escalation (Loan sanctions, medical rejections, human agent requests)
        # Note: If is_complex and asking for personalized sanction or human counselor, trigger immediate escalation contract
        if is_complex and not re.search(r'\b(definition|explain|what is|formula)\b', text.lower()):
            if "loan" in complex_reason.lower() or "medical" in complex_reason.lower() or "human" in complex_reason.lower() or "discount" in complex_reason.lower():
                budget = self.kb["fees_and_loans"]["budget_summary"]
                loans = self.kb["fees_and_loans"]["bank_loans"]
                escalation_resp = (
                    f"### 🤝 **Senior Flight Counselor Assistance Required**\n\n"
                    f"Your inquiry regarding **\"{text}\"** involves **{complex_reason}**.\n\n"
                    f"At **Airborne Aviation Academy**, our Senior Admissions Directorate and Chief Flight Instructors handle these directly:\n\n"
                    f"- 🏦 **Education Loans**: Direct tie-ups with {', '.join(loans['partner_banks'])} for up to ₹1.5 Cr with collateral or ₹7.5 Lakhs collateral-free.\n"
                    f"- 🩺 **DGCA Medical Appeals**: Expert guidance for Class 1 appeal boards at IAM Bangalore / AFCME Delhi.\n"
                    f"- 📞 **Instant Priority Hotline**: Call **{self.kb['academy']['phone_helpline']}** or chat instantly via WhatsApp below."
                )
                return {
                    "answer": escalation_resp,
                    "chips": ["Connect on WhatsApp", "Call Admissions Desk", "Request Call Back", "CPL Fee Details"],
                    "escalation": escalation
                }

        # 4. Structured Knowledge Base Matching (Zero LLM token consumption, 100% precision)
        kb_match = self.match_knowledge_base(text)
        if kb_match:
            kb_match["escalation"] = escalation
            return kb_match

        # 5. Fee & Loan Queries (Word boundary check)
        if re.search(r'\b(fee|fees|cost|costs|price|pricing|budget|installment|installments|loan|loans|sbi|hdfc)\b', text.lower()):
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
                "> 💡 *Tip: We provide bonafide fee structure certificates and quotation letters required by banks for instant loan sanctions.*"
            )
            chips = ["CPL Installment Schedule", "Bank Loan Assistance", "Cadet Pilot Costs", "Talk to Finance Counselor"]
            escalation["needed"] = True
            escalation["reason"] = "Personalized Loan & Installment Consultation Available"
            return {"answer": response_text, "chips": chips, "escalation": escalation}

        # 6. Out-of-Domain Guardrail: Rejection of non-aviation requests
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
                    "- 🩺 **Class 1 & Class 2 Medicals and Vision Rules**"
                ),
                "chips": ["CPL Course Details", "DGCA 5 Subjects", "Total Course Cost", "Class 1 & 2 Medicals"],
                "escalation": escalation
            }

        # 7. Search RAG Database across all 13 DGCA Books
        rag_results = rag_pipeline.search(message, top_k=3)

        if rag_results:
            # 7A. Try Gemini synthesis if API key configured
            gemini_ans = self.generate_with_gemini(message, rag_results)
            if gemini_ans:
                return {
                    "answer": gemini_ans,
                    "chips": ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"],
                    "escalation": escalation
                }

            # 7B. Local RAG fallback (verified textbook citations)
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
                f"Here is the verified theoretical explanation from the official **DGCA Aviation Syllabus & Curriculum**:\n\n"
                f"{rag_results[0]['text'].strip()}\n\n"
            )

            if len(rag_results) > 1:
                answer_body += f"#### 🔍 Additional Technical References:\n" + "\n\n".join(sources_md[1:]) + "\n\n"

            answer_body += f"📚 **Referenced DGCA Textbooks:**\n" + "\n".join([f"- {c}" for c in citations])

            chips = ["Explain Further", "Related DGCA Question", "Connect with Ground Instructor", "CPL Course Details"]
            return {"answer": answer_body, "chips": chips, "escalation": escalation}

        # 8. Default fallback for general aviation queries
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
            "To get immediate personalized guidance, connect directly with our Senior Flight Advisor below via WhatsApp or call our 24/7 toll-free helpline."
        )
        chips = ["CPL Course Details", "Fee Structure & Loans", "DGCA Syllabus", "Class 1 & 2 Medicals", "Chat on WhatsApp"]
        return {"answer": response_text, "chips": chips, "escalation": escalation}

ai_engine = AviationAIEngine()
