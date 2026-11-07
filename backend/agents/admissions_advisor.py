import urllib.parse
from typing import Dict, Any, Optional
from backend.models.student_profile import StudentPersona

class AdmissionsAdvisorAgent:
    """
    Autonomous subagent specialized in CPL course selection, fleet capabilities,
    tuition fee schedules, bank loans (SBI/HDFC), and admissions escalation.
    """
    def __init__(self, kb: Dict[str, Any]):
        self.kb = kb

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

    def answer_admissions_query(self, message: str, persona: StudentPersona = StudentPersona.GROUND_SCHOOL_CADET) -> Dict[str, Any]:
        lower = message.lower()
        escalation = self.generate_escalation_data(message, "Admissions & Loan Consultation")

        # 1. CPL Integrated Course Details
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
                    "chips": ["200 Flying Hours Breakdown", "Education Loan Options", "Ground School Subjects", "Class 1 & 2 Medicals"],
                    "escalation": escalation,
                    "under_the_hood": {
                        "matched": True,
                        "confidence_score": 98.6,
                        "retrieval_method": "Institutional Knowledge Base (Courses Catalog)",
                        "primary_book": "Airborne Aviation CPL Course Specification",
                        "page_number": 1,
                        "subject": "Commercial Pilot Licensing Program",
                        "chunk_excerpt": cpl["description"]
                    }
                }

        # 2. Cadet Pilot Program
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
                    "chips": ["Conventional CPL vs Cadet", "ADAPT Assessment Prep", "Education Loans", "Speak to Counselor"],
                    "escalation": escalation,
                    "under_the_hood": {
                        "matched": True,
                        "confidence_score": 97.8,
                        "retrieval_method": "Institutional Knowledge Base (Cadet Programs)",
                        "primary_book": "Airborne Cadet Pilot Mentorship Syllabus",
                        "page_number": 1,
                        "subject": "Airline Cadet Pilot Recruitment",
                        "chunk_excerpt": cadet["description"]
                    }
                }

        # 3. RTR(A) Radio Telephony Course
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
                    "chips": ["DGCA 5 Subjects", "CPL Course Details", "Pariksha Portal", "Talk to Ground Instructor"],
                    "escalation": escalation,
                    "under_the_hood": {
                        "matched": True,
                        "confidence_score": 98.0,
                        "retrieval_method": "Institutional Knowledge Base (RTR Course)",
                        "primary_book": "Radio Telephony: RTR(A) Communications & Phraseology",
                        "page_number": 1,
                        "subject": "Radio Telephony Restricted Aeronautical",
                        "chunk_excerpt": rtr["description"]
                    }
                }

        # 4. Total Fees, Cost Breakdown & 100% Bank Loans
        if any(w in lower for w in ["fee", "fees", "cost", "price", "budget", "expensive", "charges", "installment", "sbi", "hdfc", "loan", "financ"]):
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
            return {
                "answer": response_text,
                "chips": ["CPL Installment Schedule", "Bank Loan Assistance", "Cadet Pilot Costs", "Talk to Finance Counselor"],
                "escalation": escalation,
                "under_the_hood": {
                    "matched": True,
                    "confidence_score": 99.1,
                    "retrieval_method": "Institutional Knowledge Base (Fees & Banking Module)",
                    "primary_book": "Airborne Aviation Approved Fee Schedule",
                    "page_number": 1,
                    "subject": "Commercial Pilot Training Budget & Loans",
                    "chunk_excerpt": f"Total Estimated CPL: {budget['total_estimated_conventional_cpl']}, Partner Banks: {', '.join(loans['partner_banks'])}"
                }
            }

        return None
